"""Story state machine, immutable branch checkpoints and transactional API integration."""

from contextlib import asynccontextmanager
from copy import deepcopy

from fastapi import Depends, HTTPException
from sqlalchemy import inspect, select, update

from .db import (
    Character,
    ChatEvent,
    Conversation,
    Message,
    ProfileRevision,
    Story,
    StoryRequest,
    StorySegment,
    allocate_timeline,
    now,
    uid,
)
from .providers import ProviderError
from .story_context import story_context, validate_story_output
from .story_schemas import ReadingProgress, StoryAction, StoryCreate, StoryOutput


def active_chain(db, story):
    result, current, visited = [], story.active_segment_id, set()
    while current:
        seg = db.get(StorySegment, current)
        if not seg or seg.story_id != story.id or current in visited:
            raise HTTPException(500, "The saved story branch is inconsistent.")
        visited.add(current)
        result.append(seg)
        current = seg.parent_segment_id
    return list(reversed(result))


def segment_json(seg, decisions):
    ending = deepcopy(seg.ending)
    if ending.get("id") in decisions:
        ending.update(decisions[ending["id"]])
    return {
        "id": seg.id,
        "parent_segment_id": seg.parent_segment_id,
        "revision": seg.revision,
        "input_event": seg.input_event,
        "blocks": seg.blocks,
        "ending": ending,
        "summary": seg.summary,
        "confirmed_facts": seg.confirmed_facts,
    }


def story_json(db, story):
    chain = active_chain(db, story)
    decisions = {}
    for seg in chain:
        ev = seg.input_event
        if ev.get("decision_id"):
            decisions[ev["decision_id"]] = {
                "selected_option_id": ev.get("option_id"),
                "custom_input": ev.get("content"),
                "resolved_at": seg.created_at,
            }
    event = db.scalar(select(ChatEvent).where(ChatEvent.story_id == story.id))
    retry = (
        db.scalar(
            select(StoryRequest)
            .where(
                StoryRequest.story_id == story.id,
                StoryRequest.expected_revision == story.revision,
                StoryRequest.status.in_(["failed", "interrupted"]),
            )
            .order_by(StoryRequest.created_at.desc())
        )
        if story.last_error
        else None
    )
    return {
        "id": story.id,
        "character_id": story.character_id,
        "origin_conversation_id": story.origin_conversation_id,
        "creation_request_id": story.creation_request_id,
        "event_id": event.id if event else None,
        "title": story.title,
        "character_snapshot": story.snapshot_profile_json,
        "profile_version": story.profile_version,
        "portrait_id": story.portrait_id,
        "player_name": story.player_name,
        "setup": story.setup,
        "language": story.language,
        "status": story.status,
        "last_error": story.last_error,
        "retry_action": retry.payload
        if retry and retry.payload.get("request_id")
        else None,
        "revision": story.revision,
        "active_segment_id": story.active_segment_id,
        "progress": {
            "segment_id": story.reading_segment_id,
            "last_revealed_block_id": story.last_revealed_block_id,
        },
        "segments": [segment_json(s, decisions) for s in chain],
        "can_undo": any(s.input_event.get("kind") == "decide" for s in chain),
        "created_at": story.created_at,
        "updated_at": story.updated_at,
    }


def card_json(db, event):
    story = db.get(Story, event.story_id) if event.story_id else None
    return {
        "kind": "story_card",
        "id": event.id,
        "story_id": event.story_id,
        "conversation_id": event.conversation_id,
        "timeline_order": event.timeline_order,
        "title": story.title if story else event.fallback_title,
        "preview": event.preview,
        "character_id": story.character_id if story else None,
        "character_name": story.snapshot_profile_json["name"] if story else "",
        "status": story.status if story else "deleted",
        "last_error": story.last_error if story else None,
        "created_at": event.created_at,
    }


def register_story_routes(app, factory, locks, settings):
    def db_dependency():
        with factory() as db:
            yield db

    # Depends objects are shared constants, not per-definition mutable defaults.
    dep = Depends(db_dependency)

    def get_story(db, sid):
        story = db.get(Story, str(sid))
        if not story:
            raise HTTPException(404, "Story not found.")
        return story

    def get_conversation(db, cid):
        conv = db.get(Conversation, str(cid))
        if not conv:
            raise HTTPException(404, "Conversation not found.")
        return conv

    old_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(app):
        # Single-worker startup: recover requests abandoned by the prior process.
        if inspect(factory.kw["bind"]).has_table("stories"):
            with factory() as db:
                for story in db.scalars(
                    select(Story).where(Story.status == "generating")
                ):
                    story.status = story.stable_status
                    story.last_error = "Generation was interrupted by a server restart. Retry explicitly."
                for req in db.scalars(
                    select(StoryRequest).where(StoryRequest.status == "running")
                ):
                    req.status = "interrupted"
                db.commit()
        async with old_lifespan(app):
            yield

    app.router.lifespan_context = lifespan

    from uuid import UUID

    from sqlalchemy.orm import Session

    @app.get("/api/conversations/{conv_id}/timeline")
    def timeline(conv_id: UUID, db: Session = dep):
        get_conversation(db, conv_id)
        items = [
            {
                "kind": "text",
                "id": m.id,
                "role": m.role,
                "source_type": m.source_type,
                "content": m.content,
                "request_id": m.request_id,
                "profile_version": m.profile_version,
                "timeline_order": m.timeline_order,
                "created_at": m.created_at,
            }
            for m in db.scalars(
                select(Message).where(Message.conversation_id == str(conv_id))
            )
        ]
        items += [
            card_json(db, e)
            for e in db.scalars(
                select(ChatEvent).where(ChatEvent.conversation_id == str(conv_id))
            )
        ]
        return sorted(items, key=lambda item: item["timeline_order"])

    @app.post("/api/characters/{cid}/stories", status_code=201)
    def create(cid: UUID, body: StoryCreate, db: Session = dep):
        with locks.hold(str(cid)):
            c = db.get(Character, str(cid))
            conv = get_conversation(db, body.conversation_id)
            if not c or conv.character_id != str(cid):
                raise HTTPException(
                    404, "The conversation does not belong to this character."
                )
            payload = body.model_dump(mode="json")
            event = db.scalar(
                select(ChatEvent).where(
                    ChatEvent.conversation_id == conv.id,
                    ChatEvent.creation_request_id == str(body.request_id),
                )
            )
            if event:
                if event.creation_payload != payload:
                    raise HTTPException(
                        409,
                        "This invitation request ID was used with different content.",
                    )
                return {
                    "story": story_json(db, db.get(Story, event.story_id))
                    if event.story_id
                    else None,
                    "card": card_json(db, event),
                }
            profile = db.scalar(
                select(ProfileRevision).where(
                    ProfileRevision.character_id == c.id,
                    ProfileRevision.version == c.current_profile_version,
                )
            ).profile_json
            setup = {
                k: payload[k]
                for k in ("description", "relationship", "atmosphere", "constraints")
            }
            if not setup["relationship"]:
                setup["relationship"] = profile.get("interaction_preferences", {}).get(
                    "relationship_context", ""
                )
            title = " ".join(body.description.split())
            title = title[:40] + ("…" if len(title) > 40 else "")
            story = Story(
                character_id=c.id,
                origin_conversation_id=conv.id,
                creation_request_id=str(body.request_id),
                title=title,
                snapshot_profile_json=deepcopy(profile),
                profile_version=c.current_profile_version,
                portrait_id=c.current_image_id,
                player_name=body.player_name,
                setup=setup,
            )
            db.add(story)
            db.flush()
            event = ChatEvent(
                conversation_id=conv.id,
                story_id=story.id,
                creation_request_id=str(body.request_id),
                creation_payload=payload,
                fallback_title=title,
                preview=body.description[:120],
                timeline_order=allocate_timeline(db, conv.id)[0],
            )
            conv.updated_at = now()
            db.add(event)
            db.commit()
            return {"story": story_json(db, story), "card": card_json(db, event)}

    @app.get("/api/characters/{cid}/stories")
    def list_stories(cid: UUID, conversation_id: UUID | None = None, db: Session = dep):
        if not db.get(Character, str(cid)):
            raise HTTPException(404, "Character not found.")
        query = select(Story).where(Story.character_id == str(cid))
        if conversation_id:
            conv = get_conversation(db, conversation_id)
            if conv.character_id != str(cid):
                raise HTTPException(404, "Conversation not found for this character.")
            query = query.where(Story.origin_conversation_id == str(conversation_id))
        return [
            {
                "id": s.id,
                "title": s.title,
                "status": s.status,
                "revision": s.revision,
                "origin_conversation_id": s.origin_conversation_id,
                "updated_at": s.updated_at,
            }
            for s in db.scalars(query.order_by(Story.updated_at.desc()))
        ]

    @app.get("/api/stories/{sid}")
    def detail(sid: UUID, db: Session = dep):
        return story_json(db, get_story(db, sid))

    @app.patch("/api/stories/{sid}/progress")
    def progress(sid: UUID, body: ReadingProgress, db: Session = dep):
        story = get_story(db, sid)
        key = story.character_id
        db.rollback()
        with locks.hold(key):
            story = get_story(db, sid)
            if story.revision != body.expected_revision:
                raise HTTPException(
                    409,
                    "The story changed in another page. Reload before saving progress.",
                )
            segment = next(
                (s for s in active_chain(db, story) if s.id == str(body.segment_id)),
                None,
            )
            block_id = (
                str(body.last_revealed_block_id)
                if body.last_revealed_block_id
                else None
            )
            if not segment or (
                block_id and not any(b["id"] == block_id for b in segment.blocks)
            ):
                raise HTTPException(
                    422, "Reading progress must refer to an active story block."
                )
            story.reading_segment_id = segment.id
            story.last_revealed_block_id = block_id
            db.commit()
            return {
                "segment_id": segment.id,
                "last_revealed_block_id": block_id,
                "revision": story.revision,
            }

    @app.delete("/api/stories/{sid}", status_code=204)
    def remove(sid: UUID, db: Session = dep):
        story = get_story(db, sid)
        key = story.character_id
        db.rollback()
        with locks.hold(key):
            db.delete(get_story(db, sid))
            db.commit()

    @app.post("/api/stories/{sid}/actions")
    def action(sid: UUID, body: StoryAction, db: Session = dep):
        story = get_story(db, sid)
        key = story.character_id
        db.rollback()
        with locks.hold(key):
            story = get_story(db, sid)
            payload = body.model_dump(mode="json")
            req = db.scalar(
                select(StoryRequest).where(
                    StoryRequest.story_id == story.id,
                    StoryRequest.request_id == str(body.request_id),
                )
            )
            if req and req.payload != payload:
                raise HTTPException(
                    409, "This story request ID was used with different content."
                )
            if req and req.status == "succeeded":
                return {
                    "story": story_json(db, story),
                    "result": req.result_json,
                    "current_revision": story.revision,
                    "replayed": True,
                }
            if story.revision != body.expected_revision:
                raise HTTPException(
                    409, "The story changed in another page. Reload the latest version."
                )
            if story.status == "completed":
                raise HTTPException(
                    409,
                    "Completed stories are read-only. Send a new invitation to start again.",
                )
            chain = active_chain(db, story)
            head = chain[-1] if chain else None
            operation = body.operation
            event = {
                "kind": operation,
                "content": body.content,
                "input_type": body.input_type,
            }
            parent_id = head.id if head else None
            prefix = None
            if operation == "start" and head:
                raise HTTPException(
                    409, "This story has already started. Read the saved scene instead."
                )
            if operation not in {"start", "end"} and not head:
                raise HTTPException(422, "Begin the story first.")
            if operation == "continue" and head.ending["type"] != "continue":
                raise HTTPException(
                    422, "Resolve the current decision before continuing."
                )
            if operation == "decide":
                if head.ending["type"] != "decision" or head.ending["id"] != str(
                    body.decision_id
                ):
                    raise HTTPException(
                        409, "This decision is not the active unresolved decision."
                    )
                selected = next(
                    (
                        o
                        for o in head.ending["options"]
                        if o["id"] == str(body.option_id)
                    ),
                    None,
                )
                if body.option_id and not selected:
                    raise HTTPException(
                        422, "The selected option does not belong to this decision."
                    )
                event.update(
                    decision_id=head.ending["id"],
                    option_id=str(body.option_id) if selected else None,
                    content=selected["intent"] if selected else body.content,
                )
            if operation == "rewrite":
                parent_id = head.parent_segment_id
                chain = chain[:-1]
                event = deepcopy(head.input_event)
                event["rewrite_instruction"] = body.content
            if operation == "interject":
                block_id = (
                    str(body.revealed_block_id) if body.revealed_block_id else None
                )
                indices = [i for i, b in enumerate(head.blocks) if b["id"] == block_id]
                if block_id and not indices:
                    raise HTTPException(
                        422,
                        "The revealed block must belong to the latest active segment.",
                    )
                count = indices[0] + 1 if indices else 0
                # A fully read decision must be resolved as a decision, not bypassed.
                if count == len(head.blocks) and head.ending["type"] == "decision":
                    raise HTTPException(
                        422,
                        "Respond to the pending decision using a choice or free response.",
                    )
                chain = chain[:-1]
                parent_id = head.parent_segment_id
                if count or head.input_event.get("kind") == "decide":
                    # The user already made this choice even if none of its AI
                    # consequences has been revealed. Preserve that authorization.
                    prefix = StorySegment(
                        id=uid(),
                        story_id=story.id,
                        parent_segment_id=parent_id,
                        revision=story.revision + 1,
                        input_event=deepcopy(head.input_event),
                        blocks=deepcopy(head.blocks[:count]),
                        ending={"type": "continue"},
                        summary="",
                        confirmed_facts=[],
                    )
                    chain = [*chain, prefix]
                    parent_id = prefix.id
            if operation == "undo":
                target = next(
                    (
                        s
                        for s in reversed(chain)
                        if s.input_event.get("kind") == "decide"
                    ),
                    None,
                )
                if not target:
                    raise HTTPException(422, "There is no decision to undo.")
                parent_id = target.parent_segment_id
                chain = chain[
                    : next(i for i, s in enumerate(chain) if s.id == target.id)
                ]
            if not req:
                req = StoryRequest(
                    story_id=story.id,
                    request_id=str(body.request_id),
                    expected_revision=story.revision,
                    operation=operation,
                    payload=payload,
                    status="running",
                )
                db.add(req)
            req.status = "running"
            story.stable_status = story.status
            story.status = "generating"
            story.last_error = None
            db.commit()  # Observable in other windows, with no read transaction held during the remote call.
            try:
                output = None
                if operation != "undo" and not (
                    operation == "end" and body.skip_generation
                ):
                    context = story_context(story, chain, event, settings)
                    try:
                        output = StoryOutput.model_validate(
                            app.state.text.story(context)
                        )
                        validate_story_output(output, context)
                    except ValueError:
                        raise ProviderError(
                            "The story output failed validation. Saved content was kept. Retry explicitly."
                        ) from None
                # A conditional update protects the same aggregate even if concurrency assumptions change.
                result = db.execute(
                    update(Story)
                    .where(
                        Story.id == story.id, Story.revision == body.expected_revision
                    )
                    .values(revision=body.expected_revision + 1)
                )
                if result.rowcount != 1:
                    raise HTTPException(
                        409,
                        "The story changed while generating. Reload the current version.",
                    )
                if prefix:
                    db.add(prefix)
                    db.flush()
                if output:
                    # User-authored text is not regenerated when rewriting its AI response.
                    blocks = (
                        deepcopy([b for b in head.blocks if b["source"] == "user"])
                        if operation == "rewrite"
                        else []
                    )
                    if (
                        body.input_type in {"dialogue", "action"}
                        and body.content
                        and operation in {"decide", "interject"}
                    ):
                        blocks.append(
                            {
                                "id": uid(),
                                "type": body.input_type,
                                "speaker": "player",
                                "source": "user",
                                "text": body.content,
                            }
                        )
                    blocks += [
                        {
                            "id": uid(),
                            "type": b.type,
                            "speaker": b.speaker,
                            "source": "ai",
                            "text": b.text,
                        }
                        for b in output.blocks
                    ]
                    ending = output.ending.model_dump()
                    if ending["type"] == "decision":
                        ending["id"] = uid()
                        ending["options"] = [
                            {"id": uid(), "intent": o.intent}
                            for o in output.ending.options
                        ]
                    seg = StorySegment(
                        id=uid(),
                        story_id=story.id,
                        parent_segment_id=parent_id,
                        revision=body.expected_revision + 1,
                        input_event=event,
                        blocks=blocks,
                        ending=ending,
                        summary=output.summary,
                        confirmed_facts=output.confirmed_facts,
                    )
                    db.add(seg)
                    story.active_segment_id = seg.id
                    story.status = {
                        "continue": "active",
                        "decision": "awaiting_choice",
                        "ending": "completed",
                    }[ending["type"]]
                    if operation == "start" and output.title:
                        story.title = output.title
                    # Rewrites and interjections replay their replacement from the start.
                    story.reading_segment_id = seg.id
                    story.last_revealed_block_id = None
                elif operation == "undo":
                    story.active_segment_id = parent_id
                    story.status = "awaiting_choice"
                    story.reading_segment_id = parent_id
                    story.last_revealed_block_id = (
                        chain[-1].blocks[-1]["id"] if chain else None
                    )
                else:
                    story.status = "completed"
                story.stable_status = story.status
                story.last_error = None
                story.updated_at = now()
                req.status = "succeeded"
                req.result_segment_id = story.active_segment_id
                db.flush()
                req.result_json = {
                    "operation": operation,
                    "segment_id": story.active_segment_id,
                    "revision": story.revision,
                    "segment": segment_json(
                        db.get(StorySegment, story.active_segment_id), {}
                    )
                    if story.active_segment_id
                    else None,
                }
                db.commit()
                return {
                    "story": story_json(db, story),
                    "result": req.result_json,
                    "current_revision": story.revision,
                    "replayed": False,
                }
            except Exception as exc:
                db.rollback()
                # The failed replacement never replaces the effective branch or its state.
                story = get_story(db, sid)
                story.status = story.stable_status
                story.last_error = (
                    str(exc.detail)
                    if isinstance(exc, HTTPException)
                    else str(exc)
                    if isinstance(exc, ProviderError)
                    else "The story could not be generated or saved. Retry the same request."
                )
                req = db.scalar(
                    select(StoryRequest).where(
                        StoryRequest.story_id == story.id,
                        StoryRequest.request_id == str(body.request_id),
                    )
                )
                req.status = "failed"
                db.commit()
                if isinstance(exc, (HTTPException, ProviderError)):
                    raise
                if isinstance(exc, ValueError):
                    raise HTTPException(422, str(exc)) from None
                raise ProviderError(story.last_error) from None
