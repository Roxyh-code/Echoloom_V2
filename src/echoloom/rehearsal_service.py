"""Durable two-actor rehearsal jobs. Polling transports complete semantic blocks."""

import json
import re
from contextlib import asynccontextmanager
from copy import deepcopy
from pathlib import Path
from threading import Thread, Timer
from uuid import UUID

from fastapi import HTTPException, Request
from fastapi.responses import Response
from langgraph.checkpoint.sqlite import SqliteSaver
from sqlalchemy import select

from .db import (
    Character,
    Conversation,
    ProfileRevision,
    RehearsalOperation,
    RehearsalScene,
    now,
    uid,
)
from .providers import ProviderError
from .rehearsal_domain import (
    add_node,
    author_block,
    context,
    demo_performance,
    fork,
    history,
    line_count,
    new_document,
    reading_base,
    reading_view,
    render,
    state_at,
    state_change,
    unlocked_result,
    validate_performance,
    version,
)
from .rehearsal_graph import build_rehearsal_graph
from .rehearsal_schema import (
    Block,
    Command,
    CreateScene,
    Directions,
    QueryOperation,
    QuickCharacter,
    Review,
    StateChange,
)
from .schemas import Profile

ACTIVE = ("queued", "running", "stopping")
TERMINAL = ("completed", "cancelled", "failed")


def register_rehearsal(app, factory, locks, settings, serialize):
    running = set()
    app.state.rehearsal_running = running
    memory = None
    if settings.memory_enabled:
        from .rehearsal_memory import RehearsalMemory

        memory = RehearsalMemory(settings)
        previous_lifespan = app.router.lifespan_context

        @asynccontextmanager
        async def lifespan(application):
            async with previous_lifespan(application):
                try:
                    yield
                finally:
                    memory.close()

        app.router.lifespan_context = lifespan
    app.state.rehearsal_memory = memory

    def own(db, sid, owner):
        row = db.get(RehearsalScene, str(sid))
        if not row or row.owner_id != owner:
            raise HTTPException(404, "Scene not found.")
        return row

    def op_owned(db, oid, owner):
        row = db.get(RehearsalOperation, str(oid))
        if not row or row.owner_id != owner:
            raise HTTPException(404, "Operation not found.")
        return row

    def save(row, doc):
        if (
            len(json.dumps(doc).encode()) > 4 * 1024 * 1024
            or len(doc["nodes"]) > 1000
            or len(doc["versions"]) > 100
        ):
            raise HTTPException(
                413, "Scene is too large. Save this result and rehearse the next scene."
            )
        row.document = deepcopy(doc)
        row.revision += 1
        row.updated_at = now()

    def pack(row):
        return {
            "id": row.id,
            "revision": row.revision,
            "document": row.document,
            "updated_at": row.updated_at,
        }

    def event(job, kind, **data):
        r = deepcopy(job.result)
        seq = len(r.get("events", [])) + 1
        r.setdefault("events", []).append(
            {
                "job_id": job.id,
                "version_id": r.get("version_id"),
                "sequence": seq,
                "type": kind,
                **data,
            }
        )
        job.result = r

    def recover(db, sid):
        jobs = list(
            db.scalars(
                select(RehearsalOperation).where(
                    RehearsalOperation.scene_id == sid,
                    RehearsalOperation.status.in_(ACTIVE),
                )
            )
        )
        for j in jobs:
            if j.id not in running:
                j.status = "failed"
                event(
                    j,
                    "failed",
                    error="The server restarted. Completed paragraphs are safe; retry the remaining response.",
                )
        if jobs:
            db.commit()
        return [j for j in jobs if j.status in ACTIVE]

    def view(db, row):
        jobs = recover(db, row.id)
        return pack(row) | {"active_job": jobs[0].id if jobs else None}

    def record(db, oid, owner, kind, payload, sid=None):
        previous = db.get(RehearsalOperation, str(oid))
        if previous:
            if (
                previous.owner_id != owner
                or previous.kind != kind
                or previous.payload != payload
                or previous.scene_id != sid
            ):
                raise HTTPException(
                    409, "This operation ID belongs to another request."
                )
            return previous, True
        row = RehearsalOperation(
            id=str(oid),
            owner_id=owner,
            scene_id=sid,
            kind=kind,
            payload=payload,
            result={},
        )
        db.add(row)
        return row, False

    def no_job(db, sid):
        if recover(db, sid):
            raise HTTPException(
                409, "Pause the current performance before changing this scene."
            )

    def require_owner(db, owner):
        from .companion_models import Account

        if owner is None and db.scalar(select(Account.id).limit(1)):
            raise HTTPException(401, "Please sign in before saving.")

    def snapshot(db, cid, owner):
        c = db.get(Character, str(cid))
        if not c or c.owner_id != owner:
            raise HTTPException(404, "Character not found. Choose another actor.")
        p = db.scalar(
            select(ProfileRevision).where(
                ProfileRevision.character_id == c.id,
                ProfileRevision.version == c.current_profile_version,
            )
        )
        profile = Profile.model_validate(p.profile_json)
        return {
            "id": c.id,
            "source_character_id": c.id,
            "name": profile.name,
            "profile": profile.model_dump(),
            "description": c.original_description,
            "snapshot_revision": c.current_profile_version,
            "avatar": f"/api/characters/{c.id}/images/{c.current_image_id}/file"
            if c.current_image_id
            else None,
        }

    def perform(jid):
        timer = None
        try:
            with factory() as db:
                job = db.get(RehearsalOperation, jid)
                sid = job.scene_id

            def timeout():
                with locks.hold("rehearsal:" + sid), factory() as db:
                    j = db.get(RehearsalOperation, jid)
                    if j and j.status in ACTIVE:
                        j.status = "failed"
                        event(
                            j,
                            "failed",
                            error="This segment timed out. Completed paragraphs are safe. Retry the response.",
                        )
                        db.commit()

            timeout_seconds = (
                settings.rehearsal_quality_timeout_seconds
                if settings.rehearsal_consistency_enabled
                else 60
            )
            if memory is not None:
                timeout_seconds += settings.memory_timeout_seconds
            timer = Timer(timeout_seconds, timeout)
            timer.daemon = True
            timer.start()
            with locks.hold("rehearsal:" + sid), factory() as db:
                job = db.get(RehearsalOperation, jid)
                if job.status not in ACTIVE:
                    return
                job.status = "running"
                event(job, "running")
                row = db.get(RehearsalScene, sid)
                doc = deepcopy(row.document)
                v = version(doc, job.result["version_id"])
                request_event = job.result["generation"]
                checkpoint_thread = job.result.get("checkpoint_thread_id", str(jid))
                owner = job.owner_id
                db.commit()
            # No scene lock during the provider call: pause and historical reading remain available.
            if doc["demo"]:
                output = demo_performance(doc, v, request_event)
            else:
                checkpoint_dir = Path(__file__).resolve().parents[2] / "work"
                checkpoint_dir.mkdir(parents=True, exist_ok=True)

                checkpoint_path = checkpoint_dir / "rehearsal-checkpoints.sqlite"

                # Keep the connection open for the entire graph execution.
                # It closes when this with block exits.
                with SqliteSaver.from_conn_string(str(checkpoint_path)) as checkpointer:
                    graph = build_rehearsal_graph(
                        text_provider=app.state.text,
                        settings=settings,
                        checkpointer=checkpointer,
                        memory=memory,
                    )

                    initial_state = {
                        "document": doc,
                        "scene_version": v,
                        "request_event": request_event,
                    }
                    if memory is not None:
                        initial_state["memory_experiment"] = {
                            "owner": owner,
                            "scene": sid,
                            "llm": settings.memory_llm_model,
                            "embedding": settings.memory_embedding_model,
                            "top_k": settings.memory_top_k,
                            "context_bytes": settings.memory_context_bytes,
                            "directory": str(settings.memory_directory.resolve()),
                        }

                    # A retry gets a new operation ID, but may resume the original
                    # graph thread. Reuse only an identical, uncommitted input.
                    config = {"configurable": {"thread_id": checkpoint_thread}}
                    snapshot = graph.get_state(config)
                    reusable = bool(snapshot.values) and all(
                        snapshot.values.get(key) == value
                        for key, value in initial_state.items()
                    )
                    if memory is None and snapshot.values.get("memory_experiment"):
                        reusable = False
                    if not reusable:
                        checkpoint_thread = str(jid)
                        config = {"configurable": {"thread_id": checkpoint_thread}}
                        # Never overwrite an existing incompatible attempt.
                        current = graph.get_state(config)
                        if current.values:
                            raise ProviderError(
                                "This task's checkpoint no longer matches the scene. "
                                "Retry as a new operation."
                            )

                    # Persist the selected thread BEFORE executing the graph so
                    # another retry can find it even after a process crash.
                    with locks.hold("rehearsal:" + sid), factory() as db:
                        current_job = db.get(RehearsalOperation, jid)
                        if not current_job or current_job.status not in ACTIVE:
                            return
                        current_job.result = deepcopy(current_job.result) | {
                            "checkpoint_thread_id": checkpoint_thread,
                            "checkpoint_mode": "resumed" if reusable else "new",
                        }
                        db.commit()

                    if reusable and not snapshot.next:
                        # The graph completed; only the application commit failed.
                        if "performance" not in snapshot.values:
                            raise ProviderError(
                                "The saved generation has no complete result."
                            )
                        result = snapshot.values
                    else:
                        # None resumes pending work. Passing initial_state again
                        # would start another execution instead of resuming it.
                        result = graph.invoke(
                            None if reusable else initial_state,
                            config=config,
                            durability="sync",
                        )

                    output = result["performance"]
                    with locks.hold("rehearsal:" + sid), factory() as db:
                        current_job = db.get(RehearsalOperation, jid)
                        if current_job:
                            current_job.result = deepcopy(current_job.result) | {
                                "memory": result.get(
                                    "memory_context",
                                    {"status": "disabled", "items": []},
                                )
                            }
                            db.commit()

            output = validate_performance(output, doc, v)

            if output.conflicts:
                raise ProviderError(
                    "This direction conflicts with a locked rule: "
                    + " · ".join(output.conflicts)
                )
            if request_event["kind"] == "event":
                for change in output.changes:
                    change.after_block += 1
                output.blocks.insert(
                    0,
                    Block(
                        type="narration", character_id=None, text=request_event["text"]
                    ),
                )
                output.changes.insert(
                    0, StateChange(text=request_event["text"][:500], after_block=0)
                )
            node_id = uid()
            state = state_at(doc, v)
            for index, block in enumerate(output.blocks):
                with locks.hold("rehearsal:" + sid), factory() as db:
                    job = db.get(RehearsalOperation, jid)
                    if not job or job.status not in ACTIVE:
                        return
                    row = db.get(RehearsalScene, sid)
                    d = deepcopy(row.document)
                    target = version(d, job.result["version_id"])
                    b = block.model_dump() | {
                        "id": uid(),
                        "locked": request_event["kind"] == "event" and index == 0,
                        "user_edited": request_event["kind"] == "event" and index == 0,
                        "operation_id": jid,
                    }
                    for change in output.changes:
                        if change.after_block == index:
                            state_change(state, change, node_id, b["id"])
                    if index == 0:
                        target["revealed"] = line_count(d, target["head"]) + 1
                        if request_event.get("persistent"):
                            target["instructions"].append(
                                {
                                    "id": jid,
                                    "text": request_event["text"],
                                    "active": True,
                                }
                            )
                        add_node(
                            d,
                            target,
                            [b],
                            state,
                            jid,
                            request_event.get("text", ""),
                            "demo" if d["demo"] else "ai",
                            node_id,
                        )
                    else:
                        d["nodes"][node_id]["blocks"].append(b)
                        d["nodes"][node_id]["state"] = deepcopy(state)
                    save(row, d)
                    event(job, "block", block_id=b["id"], node_id=node_id, block=b)
                    db.commit()
                if memory is not None and not doc["demo"]:
                    memory.schedule(d, target, owner, sid)
            with locks.hold("rehearsal:" + sid), factory() as db:
                job = db.get(RehearsalOperation, jid)
                if job and job.status in ACTIVE:
                    job.status = "completed"
                    event(job, "completed", ending=output.ending)
                    db.commit()
        except Exception as exc:  # noqa: BLE001 - durable worker boundary must record terminal failure
            # Never expose raw SDK errors, prompts, or generated invalid text.
            detail = (
                str(exc)
                if isinstance(exc, ProviderError)
                else exc.detail
                if isinstance(exc, HTTPException)
                else "This segment could not be completed. Your saved paragraphs are safe."
            )
            with factory() as db:
                j = db.get(RehearsalOperation, jid)
                sid = j.scene_id if j else None
            if sid:
                with locks.hold("rehearsal:" + sid), factory() as db:
                    j = db.get(RehearsalOperation, jid)
                    if j and j.status in ACTIVE:
                        j.status = "failed"
                        event(j, "failed", error=detail)
                        db.commit()
        finally:
            if timer:
                timer.cancel()
            running.discard(jid)

    def launch(job):
        running.add(job.id)
        Thread(
            target=perform, args=(job.id,), daemon=True, name="rehearsal-generation"
        ).start()

    @app.get("/api/rehearsal/metrics")
    def metrics(request: Request):
        mapping = {
            "create": "scene_create_started",
            "cast": "cast_completed",
            "setup": "setup_submitted",
            "continue": "continue_clicked",
            "direction": "intervention_applied",
            "event": "intervention_applied",
            "takeover": "role_takeover_started",
            "branch": "branch_created",
            "switch": "version_switched",
            "result": "scene_result_saved",
            "export": "export_completed",
        }
        seen = {}
        with factory() as db:
            owned = list(
                db.scalars(
                    select(RehearsalScene).where(
                        RehearsalScene.owner_id == request.state.user_id
                    )
                )
            )
            for row in owned:
                if row.document["nodes"]:
                    seen.setdefault("first_segment_completed", set()).add(row.id)
                if row.document.get("source"):
                    seen.setdefault("next_scene_created", set()).add(row.id)
            for op in db.scalars(
                select(RehearsalOperation).where(
                    RehearsalOperation.owner_id == request.state.user_id
                )
            ):
                if op.status == "deleted":
                    continue
                name = (
                    "generation_failed"
                    if op.status == "failed"
                    else mapping.get(op.kind)
                )
                if name:
                    if (
                        op.kind == "cast"
                        and len([x for x in op.payload.get("character_ids", []) if x])
                        != 2
                    ):
                        continue
                    seen.setdefault(name, set()).add(
                        op.scene_id or op.result.get("scene_id") or op.id
                    )
        return {
            "deduplicated_by": "scene",
            "events": {key: len(ids) for key, ids in seen.items()},
        }

    @app.get("/api/rehearsal/characters")
    def characters(request: Request):
        with factory() as db:
            return [
                serialize(db, c)
                for c in db.scalars(
                    select(Character)
                    .where(
                        Character.owner_id == request.state.user_id,
                        Character.archived == False,
                    )
                    .order_by(Character.updated_at.desc())
                )
            ]

    @app.post("/api/rehearsal/characters", status_code=201)
    def quick(body: QuickCharacter, request: Request):
        owner = request.state.user_id
        with locks.hold("account-bootstrap"), factory() as db:
            require_owner(db, owner)
            op, exists = record(
                db,
                body.operation_id,
                owner,
                "quick_character",
                body.model_dump(mode="json"),
            )
            if exists:
                return op.result
            c = Character(owner_id=owner, original_description=body.description)
            db.add(c)
            db.flush()
            profile = Profile(
                name=body.name,
                short_description=body.description[:200],
                backstory=body.description,
            )
            db.add(
                ProfileRevision(
                    character_id=c.id,
                    version=1,
                    profile_json=profile.model_dump(),
                    change_summary="Author-created rehearsal character",
                )
            )
            db.add(Conversation(character_id=c.id))
            op.result = {"character_id": c.id}
            db.commit()
            return op.result

    @app.get("/api/rehearsal/scenes")
    def scenes(request: Request):
        with factory() as db:
            return [
                view(db, row)
                for row in db.scalars(
                    select(RehearsalScene)
                    .where(RehearsalScene.owner_id == request.state.user_id)
                    .order_by(RehearsalScene.updated_at.desc())
                )
            ]

    @app.post("/api/rehearsal/scenes", status_code=201)
    def create(body: CreateScene, request: Request):
        owner = request.state.user_id
        with locks.hold("account-bootstrap"), factory() as db:
            require_owner(db, owner)
            op, exists = record(
                db, body.operation_id, owner, "create", body.model_dump(mode="json")
            )
            if exists:
                return view(db, own(db, op.result["scene_id"], owner))
            source = None
            state = None
            if body.source_scene_id:
                parent = own(db, body.source_scene_id, owner)
                result = parent.document.get("result")
                if not result:
                    raise HTTPException(409, "Save the previous scene's result first.")
                cast = deepcopy(parent.document["cast"])
                source = {
                    "scene_id": parent.id,
                    "version_id": result["version_id"],
                    "head": result["head"],
                    "title": parent.document["title"],
                    "stamp": result["stamp"],
                    "excerpt": render(
                        parent.document,
                        {
                            **version(parent.document, result["version_id"]),
                            "head": result["head"],
                        },
                    )[-4000:],
                }
                state = deepcopy(result["state"])
            elif body.demo:
                cast = [
                    {
                        "id": "lin",
                        "source_character_id": None,
                        "name": "Lin",
                        "profile": {
                            "wants": "An honest answer without revealing how much she knows."
                        },
                        "description": "A quiet, observant restorer. She knows Xu betrayed her.",
                        "avatar": "/creator/mira.svg",
                        "snapshot_revision": 1,
                    },
                    {
                        "id": "xu",
                        "source_character_id": None,
                        "name": "Xu",
                        "profile": {
                            "wants": "Keep Lin from leaving; he believes she does not know."
                        },
                        "description": "An old friend, warm but evasive. He does not know Lin has discovered his betrayal.",
                        "avatar": "/creator/leo.svg",
                        "snapshot_revision": 1,
                    },
                ]
            else:
                if len(set(body.character_ids)) != len(body.character_ids):
                    raise HTTPException(422, "Choose two different characters.")
                cast = [snapshot(db, cid, owner) for cid in body.character_ids]
            setup = body.setup.model_dump()
            doc = new_document(
                setup,
                cast,
                body.demo or bool(body.source_scene_id and parent.document["demo"]),
                source,
            )
            if state:
                doc["initial_state"] = state
                for i, key in enumerate(("knowledge_a", "knowledge_b")):
                    if setup[key]:
                        state["knowledge"][cast[i]["id"]] = setup[key]
            row = RehearsalScene(owner_id=owner, document=doc)
            db.add(row)
            db.flush()
            op.result = {"scene_id": row.id}
            db.commit()
            return view(db, row)

    @app.get("/api/rehearsal/scenes/{sid}")
    def read(sid: UUID, request: Request):
        with locks.hold("rehearsal:" + str(sid)), factory() as db:
            row = own(db, sid, request.state.user_id)
            result = view(db, row)
            if row.document.get("source"):
                parent = db.get(RehearsalScene, row.document["source"]["scene_id"])
                result["source_updated"] = (
                    not parent
                    or (parent.document.get("result") or {}).get("stamp")
                    != row.document["source"]["stamp"]
                )
            return result

    @app.post("/api/rehearsal/scenes/{sid}/commands")
    def command(sid: UUID, body: Command, request: Request):
        owner = request.state.user_id
        with locks.hold("rehearsal:" + str(sid)), factory() as db:
            row = own(db, sid, owner)
            op, exists = record(
                db,
                body.operation_id,
                owner,
                body.kind,
                body.model_dump(mode="json"),
                row.id,
            )
            if exists:
                return view(db, row) | {
                    "job_id": op.id if "generation" in op.result else None,
                    "operation_status": op.status,
                }
            if row.revision != body.expected_revision:
                raise HTTPException(
                    409, "A newer revision exists. Reload it; your local input is kept."
                )
            if body.kind not in ("switch", "progress", "read"):
                no_job(db, row.id)
            d = deepcopy(row.document)
            v = version(d, body.version_id)
            kind = body.kind
            generate = kind in (
                "continue",
                "direction",
                "event",
                "speak",
                "branch",
                "replay",
            )
            node_id = body.node_id
            if kind in (
                "continue",
                "direction",
                "event",
                "speak",
                "branch",
                "edit",
                "replay",
                "takeover",
                "setup",
                "settle",
                "result",
            ):
                v, mapped = reading_base(
                    d, v, op.id, explicit_fork=kind in ("branch", "edit", "replay")
                )
                node_id = mapped.get(node_id, node_id)
            if kind == "settle":
                pass
            elif kind == "read":
                if body.revealed > line_count(d, v["head"]):
                    raise HTTPException(422, "This line has not been generated yet.")
                v["revealed"] = body.revealed
            elif kind == "cast":
                if v["head"] or d.get("source"):
                    raise HTTPException(
                        409, "This cast has already been snapshotted for a performance."
                    )
                ids = [cid for cid in body.character_ids if cid]
                if len(set(ids)) != len(ids):
                    raise HTTPException(422, "Choose different actors.")
                d["cast"] = [
                    snapshot(db, cid, owner) | {"slot": i}
                    for i, cid in enumerate(body.character_ids)
                    if cid
                ]
                from .rehearsal_domain import initial_state

                d["initial_state"] = initial_state(v["setup"], d["cast"])
            elif kind == "setup":
                if not body.setup:
                    raise HTTPException(422, "Enter scene settings.")
                if v["head"]:
                    v = fork(d, v, v["head"], "Scene settings changed")
                previous_setup = v["setup"]
                for i, actor in enumerate(d["cast"]):
                    field = "knowledge_a" if i == 0 else "knowledge_b"
                    if (
                        v["head"]
                        and body.setup.model_dump()[field] != previous_setup[field]
                    ):
                        v.setdefault("knowledge_overrides", {})[actor["id"]] = (
                            body.setup.model_dump()[field]
                        )
                v["setup"] = body.setup.model_dump()
                d["setup"] = v["setup"]
                if not v["head"]:
                    for i, m in enumerate(d["cast"]):
                        key = "knowledge_a" if m.get("slot", i) == 0 else "knowledge_b"
                        value = v["setup"][key]
                        if value or not d.get("source"):
                            d["initial_state"]["knowledge"][m["id"]] = value
                d["title"] = (
                    d["title"]
                    if d["title"] not in ("未命名场景", "Untitled scene")
                    else v["setup"]["premise"][:28]
                )
            elif kind == "switch":
                d["active_version"] = v["id"]
            elif kind == "progress":
                v["position"] = body.position
            elif kind == "rename":
                if not body.name.strip():
                    raise HTTPException(422, "Enter a name.")
                if body.target_id == "scene":
                    d["title"] = body.name
                else:
                    v["label"] = body.name
            elif kind == "takeover":
                if body.target_id not in {c["id"] for c in d["cast"]}:
                    raise HTTPException(422, "Choose one actor.")
                v = unlocked_result(d, v)
                v["takeover"] = body.target_id
            elif kind == "release":
                v["takeover"] = None
            elif kind == "stop_instruction":
                for i in v["instructions"]:
                    if i["id"] == body.target_id:
                        i["active"] = False
            elif kind == "delete_version":
                if (
                    len(d["versions"]) == 1
                    or v["id"] == d["active_version"]
                    or (d.get("result") and v["id"] == d["result"]["version_id"])
                ):
                    raise HTTPException(
                        409,
                        "Keep the current or confirmed version. Switch or change the result first.",
                    )
                deps = [
                    s.id
                    for s in db.scalars(
                        select(RehearsalScene).where(RehearsalScene.owner_id == owner)
                    )
                    if (s.document.get("source") or {}).get("version_id") == v["id"]
                ]
                if deps:
                    raise HTTPException(409, "A following scene uses this version.")
                del d["versions"][v["id"]]
            elif kind == "result":
                if not v["head"]:
                    raise HTTPException(409, "Rehearse a complete paragraph first.")
                previous = d.get("result")
                stamp = (
                    previous["stamp"]
                    if previous
                    and previous["version_id"] == v["id"]
                    and previous["head"] == v["head"]
                    else uid()
                )
                d["result"] = {
                    "version_id": v["id"],
                    "head": v["head"],
                    "state": state_at(d, v),
                    "setup": deepcopy(v["setup"]),
                    "stamp": stamp,
                }
                d["status"] = "saved"
            elif kind == "feedback":
                selected = d["nodes"].get(node_id)
                if not selected or selected["id"] not in {
                    n["id"] for n in history(d, v["head"])
                }:
                    raise HTTPException(404, "Paragraph not found.")
                d["feedback"].append(
                    {
                        "node_id": selected["id"],
                        "correction": body.text,
                        "created_at": now(),
                    }
                )
            elif kind in ("branch", "replay", "edit"):
                nodes = history(d, v["head"])
                selected = d["nodes"].get(node_id or v["head"])
                if node_id and not selected:
                    raise HTTPException(404, "Paragraph not found.")
                if selected and selected["id"] not in {n["id"] for n in nodes}:
                    raise HTTPException(404, "Paragraph is not on this version.")
                if kind == "branch":
                    v = fork(
                        d, v, selected["id"] if selected else None, body.text, body.name
                    )
                else:
                    if not selected:
                        raise HTTPException(404, "Choose a paragraph first.")
                    if body.block_id and not any(
                        b["id"] == body.block_id for b in selected["blocks"]
                    ):
                        raise HTTPException(404, "Paragraph block not found.")
                    selected_index = next(
                        (
                            i
                            for i, b in enumerate(selected["blocks"])
                            if b["id"] == body.block_id
                        ),
                        0,
                    )
                    old = v
                    v = fork(
                        d,
                        v,
                        selected["parent"],
                        body.text or "Replay from this paragraph",
                        body.name,
                    )
                    if kind == "edit":
                        changed = deepcopy(selected["blocks"])
                        changed[selected_index].update(
                            id=uid(),
                            text=body.text,
                            locked=True,
                            user_edited=True,
                            operation_id=op.id,
                        )
                        before = (
                            state_at(d, old, selected["parent"])
                            if selected["parent"]
                            else deepcopy(d["initial_state"])
                        )
                        if body.edit_type == "wording":
                            add_node(
                                d,
                                v,
                                changed,
                                selected["state"],
                                op.id,
                                "Wording edit · state needs review",
                                "author",
                            )
                            d["nodes"][v["head"]]["state_review"] = True
                            for following in nodes[nodes.index(selected) + 1 :]:
                                add_node(
                                    d,
                                    v,
                                    deepcopy(following["blocks"]),
                                    following["state"],
                                    op.id,
                                    "Preserved after wording edit",
                                    following["source"],
                                )
                        else:
                            add_node(
                                d,
                                v,
                                changed[: selected_index + 1],
                                before,
                                op.id,
                                "Locked plot edit",
                                "author",
                            )
                            generate = True
                    elif selected_index:
                        before = (
                            state_at(d, old, selected["parent"])
                            if selected["parent"]
                            else deepcopy(d["initial_state"])
                        )
                        add_node(
                            d,
                            v,
                            deepcopy(selected["blocks"][:selected_index]),
                            before,
                            op.id,
                            "Preserved prefix",
                            "author",
                        )
            if kind == "edit":
                v["revealed"] = line_count(d, v["head"])
            if generate:
                if len(d["cast"]) != 2:
                    raise HTTPException(422, "Choose two actors before starting.")
                v = unlocked_result(d, v)
                if len(v["setup"]["premise"].strip()) < 10:
                    raise HTTPException(
                        422, "Describe the situation in at least 10 characters."
                    )
                if kind == "speak":
                    if not v["takeover"]:
                        raise HTTPException(409, "Choose an actor to take over first.")
                    block = author_block(
                        body.input_type, v["takeover"], body.text, op.id
                    )
                    add_node(
                        d,
                        v,
                        [block],
                        state_at(d, v),
                        op.id,
                        "Author performance",
                        "author",
                    )
                if kind == "speak":
                    v["revealed"] = line_count(d, v["head"])
                d["status"] = "saved" if d.get("result") else "rehearsing"
                op.status = "queued"
                op.result = {
                    "version_id": v["id"],
                    "base_node_id": v["head"],
                    "events": [],
                    "generation": {
                        "kind": kind,
                        "text": body.text,
                        "persistent": body.persistent,
                    },
                    "author_head": v["head"] if kind == "speak" else None,
                }
            save(row, d)
            if not generate:
                op.result = {"version_id": v["id"]}
            if generate:
                running.add(op.id)
            try:
                db.commit()
            except Exception:
                running.discard(op.id)
                raise
            if generate:
                launch(op)
            return pack(row) | {
                "job_id": op.id if generate else None,
                "active_job": op.id if generate else None,
            }

    @app.get("/api/rehearsal/jobs/{oid}")
    def job(oid: UUID, request: Request, after: int = 0):
        with factory() as db:
            initial = op_owned(db, oid, request.state.user_id)
            sid = initial.scene_id
        if not sid:
            raise HTTPException(404, "Generation job not found.")
        with locks.hold("rehearsal:" + sid), factory() as db:
            row = own(db, sid, request.state.user_id)
            recover(db, sid)
            j = op_owned(db, oid, request.state.user_id)
            return {
                "id": j.id,
                "status": j.status,
                "version_id": j.result.get("version_id"),
                "events": [
                    e for e in j.result.get("events", []) if e["sequence"] > after
                ],
                "scene": pack(row),
                "memory": j.result.get("memory", {"status": "disabled", "items": []}),
            }

    @app.post("/api/rehearsal/jobs/{oid}/pause")
    def pause(oid: UUID, request: Request):
        with factory() as db:
            initial = op_owned(db, oid, request.state.user_id)
            sid = initial.scene_id
        if not sid:
            raise HTTPException(404, "Generation job not found.")
        with locks.hold("rehearsal:" + sid), factory() as db:
            own(db, sid, request.state.user_id)
            j = op_owned(db, oid, request.state.user_id)
            if j.status in ACTIVE:
                j.status = "cancelled"
                event(j, "cancelled", message="Stopped at the last complete paragraph.")
                db.commit()
            return {"status": j.status}

    @app.post("/api/rehearsal/jobs/{oid}/retry")
    def retry(oid: UUID, request: Request):
        with factory() as db:
            initial = op_owned(db, oid, request.state.user_id)
            sid = initial.scene_id
        if not sid:
            raise HTTPException(404, "Generation job not found.")
        with locks.hold("rehearsal:" + sid), factory() as db:
            row = own(db, sid, request.state.user_id)
            j = op_owned(db, oid, request.state.user_id)
            linked = j.result.get("retry_job_id")
            if linked:
                retry_job = op_owned(db, linked, request.state.user_id)
                return {"job_id": retry_job.id, "status": retry_job.status}
            no_job(db, sid)
            if j.status != "failed":
                return {"job_id": j.id, "status": j.status}
            # A timed-out provider call may still be executing in this process.
            # Wait for it to exit before a retry touches its checkpoint thread.
            if j.id in running:
                raise HTTPException(
                    409,
                    "The previous generation is still stopping. Retry shortly.",
                )
            d = deepcopy(row.document)
            v = version(d, j.result["version_id"])
            v, _ = reading_base(d, v, str(oid))
            if d != row.document:
                save(row, d)
            result = deepcopy(j.result)
            result["version_id"] = v["id"]
            result["events"] = []
            committed_blocks = any(
                e.get("type") == "block" for e in j.result.get("events", [])
            ) or any(
                n.get("operation_id") == j.id and n.get("source") in ("ai", "demo")
                for n in d["nodes"].values()
            )
            if (
                not committed_blocks
                and v["head"] == result["base_node_id"]
                and not d["demo"]
            ):
                result["checkpoint_thread_id"] = j.result.get(
                    "checkpoint_thread_id", j.id
                )
            else:
                # Existing continuation logic handles partially committed text.
                # Do not append the original complete performance a second time.
                result.pop("checkpoint_thread_id", None)
            result.pop("checkpoint_mode", None)
            if v["head"] != result["base_node_id"]:
                result["generation"] = {
                    "kind": "continue",
                    "text": "Continue after the last committed block; do not repeat it.",
                }
            retry_job = RehearsalOperation(
                id=uid(),
                owner_id=j.owner_id,
                scene_id=sid,
                kind=j.kind,
                payload={"retry_of": j.id},
                status="queued",
                result=result,
            )
            db.add(retry_job)
            # A distinct attempt prevents a timed-out worker from committing into a retry.
            j.result = deepcopy(j.result) | {"retry_job_id": retry_job.id}
            running.add(retry_job.id)
            try:
                db.commit()
            except Exception:
                running.discard(retry_job.id)
                raise
            launch(retry_job)
            return {"job_id": retry_job.id, "status": retry_job.status}

    @app.post("/api/rehearsal/scenes/{sid}/directions")
    def directions(sid: UUID, body: QueryOperation, request: Request):
        return generated_metadata(sid, body, request.state.user_id, "directions")

    @app.post("/api/rehearsal/scenes/{sid}/review")
    def review(sid: UUID, body: QueryOperation, request: Request):
        return generated_metadata(sid, body, request.state.user_id, "review")

    def generated_metadata(sid, body, owner, kind):
        with (
            locks.hold("rehearsal-metadata:" + str(body.operation_id)),
            factory() as db,
        ):
            row = own(db, sid, owner)
            op, exists = record(
                db, body.operation_id, owner, kind, body.model_dump(mode="json"), row.id
            )
            if exists:
                return op.result
            doc = deepcopy(row.document)
            v = version(doc, body.version_id)
            doc, v = reading_view(doc, v)
            if body.node_id:
                if body.node_id not in {n["id"] for n in history(doc, v["head"])}:
                    raise HTTPException(404, "Paragraph not found.")
                v = deepcopy(v)
                v["head"] = body.node_id
            ctx = context(doc, v, {"kind": kind}, settings)
            if kind == "directions":
                if doc["demo"]:
                    en = v["setup"]["language"] == "en"
                    data = {
                        "options": [
                            {
                                "id": "confess",
                                "title": "A partial confession"
                                if en
                                else "先坦白一部分",
                                "choice": "Let Xu admit the betrayal."
                                if en
                                else "让许先承认一部分事实。",
                                "consequence": "A secret becomes shared knowledge; trust may fracture."
                                if en
                                else "秘密成为共同知识，关系可能出现裂痕。",
                            },
                            {
                                "id": "leave",
                                "title": "Leave it unsaid" if en else "把话留在这里",
                                "choice": "Let Lin leave quietly."
                                if en
                                else "让林安静地离开。",
                                "consequence": "Distance grows while the secret stays unspoken."
                                if en
                                else "秘密仍未说破，两人的距离却更远了。",
                            },
                        ]
                    }
                else:
                    data = app.state.text.rehearsal_directions(ctx).model_dump()
                data = Directions.model_validate(data).model_dump()
            else:
                if not v["head"]:
                    raise HTTPException(409, "Rehearse a paragraph first.")
                # Recaps receive only completed text, never hidden setup or private profiles.
                ctx = [
                    {
                        "role": "system",
                        "content": "Summarize only completed scene text. Do not invent events.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "language": v["setup"]["language"],
                                "cast": [
                                    {"id": c["id"], "name": c["name"]}
                                    for c in doc["cast"]
                                ],
                                "text": render(doc, v, include_title=False),
                            },
                            ensure_ascii=False,
                        ),
                    },
                ]
                if doc["demo"]:
                    state = state_at(doc, v)
                    data = {
                        "summary": render(doc, v, include_title=False)[-700:],
                        "changes": [
                            f["text"]
                            for f in state["world_facts"]
                            if f["source_node"]
                            in {n["id"] for n in history(doc, v["head"])}
                        ],
                        "threads": [
                            f["text"]
                            for f in state["threads"]
                            if f["source_node"]
                            in {n["id"] for n in history(doc, v["head"])}
                        ],
                    }
                else:
                    data = app.state.text.rehearsal_review(ctx).model_dump()
                data = Review.model_validate(data).model_dump()
            op.result = data
            db.commit()
            return data

    @app.get("/api/rehearsal/scenes/{sid}/export")
    def export(
        sid: UUID,
        request: Request,
        version_id: str = "",
        format: str = "txt",
        include_title: bool = True,
        include_names: bool = True,
        visible_only: bool = False,
    ):
        if format not in ("txt", "md"):
            raise HTTPException(422, "Choose TXT or Markdown.")
        with factory() as db:
            row = own(db, sid, request.state.user_id)
            v = version(row.document, version_id)
            export_doc = row.document
            if visible_only:
                export_doc, v = reading_view(export_doc, v)
            text = render(export_doc, v, format, include_title, include_names)
            db.add(
                RehearsalOperation(
                    id=uid(),
                    owner_id=request.state.user_id,
                    scene_id=row.id,
                    kind="export",
                    payload={"format": format, "version_id": v["id"]},
                    status="completed",
                    result={"event": "export_completed", "version_id": v["id"]},
                )
            )
            db.commit()
            # RFC 5987 filename encoding; no OS-reserved characters.
            from urllib.parse import quote

            name = (
                re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", row.document["title"]).strip(
                    " ."
                )[:60]
                or "scene"
            )
            return Response(
                text.encode("utf-8-sig"),
                media_type="text/plain; charset=utf-8"
                if format == "txt"
                else "text/markdown; charset=utf-8",
                headers={
                    "Content-Disposition": f"attachment; filename=scene.{format}; filename*=UTF-8''{quote(name)}.{format}"
                },
            )

    @app.delete("/api/rehearsal/scenes/{sid}", status_code=204)
    def delete(sid: UUID, request: Request):
        with (
            locks.hold("account-bootstrap"),
            locks.hold("rehearsal:" + str(sid)),
            factory() as db,
        ):
            row = own(db, sid, request.state.user_id)
            no_job(db, row.id)
            deps = [
                {"id": s.id, "title": s.document["title"]}
                for s in db.scalars(
                    select(RehearsalScene).where(
                        RehearsalScene.owner_id == request.state.user_id
                    )
                )
                if (s.document.get("source") or {}).get("scene_id") == row.id
            ]
            if deps:
                raise HTTPException(
                    409,
                    {
                        "message": "Delete the following scenes first; their source must stay available.",
                        "dependencies": deps,
                    },
                )
            for op in db.scalars(
                select(RehearsalOperation).where(
                    RehearsalOperation.owner_id == request.state.user_id
                )
            ):
                if op.scene_id == row.id or op.result.get("scene_id") == row.id:
                    op.payload = {}
                    op.result = {"deleted": True}
                    op.status = "deleted"
            db.delete(row)
            db.commit()
