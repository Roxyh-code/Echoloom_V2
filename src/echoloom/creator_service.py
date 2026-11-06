"""Server-owned creator records; no fake provider is installed in live mode."""

import json
from contextlib import ExitStack
from copy import deepcopy
from uuid import UUID

from fastapi import HTTPException, Request
from fastapi.responses import Response
from pydantic import ValidationError
from sqlalchemy import select

from .creator_domain import (
    apply_action,
    demo_output,
    generate_context,
    new_document,
    path,
    sample_cast,
)
from .creator_schemas import (
    CreatorAction,
    CreatorCharacterInput,
    CreatorCreate,
    CreatorDocument,
    CreatorImageInput,
    CreatorImport,
    CreatorOutput,
)
from .db import (
    Character,
    Conversation,
    CreatorRequest,
    CreatorWork,
    Portrait,
    ProfileRevision,
    now,
    uid,
)
from .providers import ProviderError
from .schemas import ImageInput, Profile


def references(factory, value):
    """Protect portraits/characters pinned by any active, archived or saved draft."""
    with factory() as db:
        return any(
            value in json.dumps(w.document) for w in db.scalars(select(CreatorWork))
        )


def register_creator(app, factory, locks, settings, image_render, serialize_character):
    def owner(request):
        return request.state.user_id

    def character(db, cid, user):
        c = db.get(Character, str(cid))
        if not c or c.owner_id != user:
            raise HTTPException(404, "Character not found.")
        return c

    def snapshot(db, c):
        r = db.scalar(
            select(ProfileRevision).where(
                ProfileRevision.character_id == c.id,
                ProfileRevision.version == c.current_profile_version,
            )
        )
        pending = next(
            (
                j
                for j in db.scalars(
                    select(CreatorRequest).where(
                        CreatorRequest.scope == "character",
                        CreatorRequest.owner_id == c.owner_id,
                        CreatorRequest.status == "pending",
                    )
                )
                if (j.result or {}).get("character_id") == c.id
            ),
            None,
        )
        return {
            "id": c.id,
            "character_id": c.id,
            "creation_job_id": pending.id if pending else None,
            "profile": Profile.model_validate(r.profile_json).model_dump(),
            "version": c.current_profile_version,
            "portrait_id": c.current_image_id,
            "portrait_url": f"/api/characters/{c.id}/images/{c.current_image_id}/file"
            if c.current_image_id
            else None,
        }

    def work(db, wid, user):
        w = db.get(CreatorWork, str(wid))
        if not w or w.owner_id != user:
            raise HTTPException(404, "Story not found.")
        return w

    def pack(w):
        return {
            "id": w.id,
            "revision": w.revision,
            "document": w.document,
            "updated_at": w.updated_at,
        }

    def record(db, rid, user, scope, payload):
        row = db.get(CreatorRequest, str(rid))
        if row and (
            row.owner_id != user or row.scope != scope or row.payload != payload
        ):
            raise HTTPException(
                409,
                "This request ID belongs to another operation. Reload before retrying.",
            )
        if not row:
            row = CreatorRequest(
                id=str(rid),
                owner_id=user,
                scope=scope,
                payload=payload,
                status="pending",
            )
            db.add(row)
            db.commit()
        return row

    def fail(db, rid, detail):
        db.rollback()
        r = db.get(CreatorRequest, str(rid))
        r.status = "failed"
        r.result = {"detail": detail}
        db.commit()

    def generate(doc, line, event):
        if doc["demo"]:
            return demo_output(doc, event["instruction"], event["operation"])
        context = generate_context(doc, line, event, settings)
        out = CreatorOutput.model_validate(app.state.text.creator(context))
        return out

    def save_doc(w, doc):
        validated = CreatorDocument.model_validate(doc).model_dump()
        if len(json.dumps(validated).encode()) > 4 * 1024 * 1024:
            raise HTTPException(
                413, "Story is too large. Export a backup and start a new story."
            )
        w.document = validated
        w.revision += 1
        w.updated_at = now()

    @app.get("/api/creator/characters")
    def characters(request: Request, archived: bool = False):
        with factory() as db:
            return [
                serialize_character(db, c) | {"archived": c.archived}
                for c in db.scalars(
                    select(Character)
                    .where(
                        Character.owner_id == owner(request),
                        Character.archived == archived,
                    )
                    .order_by(Character.updated_at.desc())
                )
            ]

    @app.post("/api/creator/characters", status_code=201)
    def create_character(body: CreatorCharacterInput, request: Request):
        if len(body.description) > settings.max_profile_input_chars:
            raise HTTPException(
                422, "The character description exceeds the configured limit."
            )
        user = owner(request)
        rid = str(body.request_id)
        payload = body.model_dump(mode="json")
        with locks.hold("creator-request:" + rid), factory() as db:
            row = record(db, rid, user, "character", payload)
            if row.status == "succeeded":
                return row.result
            cid = (row.result or {}).get("character_id")
            if not cid:
                try:
                    profile = Profile.model_validate(
                        app.state.text.generate(body.description)
                    )
                except ProviderError as exc:
                    fail(db, rid, str(exc))
                    raise
                with locks.hold("account-bootstrap"):
                    from .companion_models import Account

                    if user is None and db.scalar(select(Account.id).limit(1)):
                        raise HTTPException(
                            401, "Please sign in before saving your character."
                        )
                    c = Character(owner_id=user, original_description=body.description)
                    db.add(c)
                    db.flush()
                    db.add(
                        ProfileRevision(
                            character_id=c.id,
                            version=1,
                            profile_json=profile.model_dump(),
                            change_summary="Create character and portrait",
                        )
                    )
                    db.add(Conversation(character_id=c.id))
                    row.result = {"character_id": c.id, "phase": "portrait_pending"}
                    db.commit()
                    cid = c.id
            c = character(db, cid, user)
            # A restart can recover a portrait already saved before its response was recorded.
            image = db.scalar(
                select(Portrait)
                .where(Portrait.character_id == cid)
                .order_by(Portrait.version)
            )
            image_error = None
            try:
                if not image:
                    result = image_render(
                        UUID(cid),
                        ImageInput(expected_image_id=c.current_image_id),
                        False,
                        db,
                    )
                    image = db.get(Portrait, result["id"])
                with locks.hold(cid):
                    db.refresh(c)
                    if c.current_image_id is None and c.current_profile_version == 1:
                        c.current_image_id = image.id
                        db.commit()
            except (ProviderError, HTTPException) as exc:
                db.rollback()
                image_error = exc.detail if isinstance(exc, HTTPException) else str(exc)
            if image and not image_error:
                # Resolve only the original pending portrait, never a later edit.
                pinned_ids = list(
                    db.scalars(
                        select(CreatorWork.id).where(CreatorWork.owner_id == user)
                    )
                )
                db.rollback()
                for pinned_id in pinned_ids:
                    with locks.hold("creator-work:" + pinned_id):
                        pinned = db.get(CreatorWork, pinned_id, populate_existing=True)
                        if not pinned:
                            continue
                        doc = deepcopy(pinned.document)
                        changed = False
                        for members in doc["casts"].values():
                            for member in members:
                                if (
                                    member.get("creation_job_id") == rid
                                    and member["character_id"] == cid
                                    and member["version"] == 1
                                    and not member["portrait_id"]
                                ):
                                    member["portrait_id"] = image.id
                                    member["portrait_url"] = (
                                        f"/api/characters/{cid}/images/{image.id}/file"
                                    )
                                    changed = True
                        if changed:
                            pinned.document = CreatorDocument.model_validate(
                                doc
                            ).model_dump()
                            pinned.revision += 1
                            pinned.updated_at = now()
                            db.commit()

            db.refresh(c)
            row = db.get(CreatorRequest, rid)
            row.status = "succeeded"
            row.result = {
                "character_id": cid,
                "phase": "portrait_failed" if image_error else "ready",
                "image_error": image_error,
            }
            db.commit()
            return row.result

    @app.get("/api/creator/jobs/{rid}")
    def job(rid: UUID, request: Request):
        with factory() as db:
            r = db.get(CreatorRequest, str(rid))
            if not r or r.owner_id != owner(request):
                raise HTTPException(404, "Job not found.")
            return {"status": r.status, "result": r.result}

    @app.post("/api/creator/characters/{cid}/portrait")
    def portrait(cid: UUID, body: CreatorImageInput, request: Request):
        user = owner(request)
        rid = str(body.request_id)
        with locks.hold("creator-request:" + rid), factory() as db:
            character(db, cid, user)
            row = record(
                db, rid, user, "portrait:" + str(cid), body.model_dump(mode="json")
            )
            if row.status == "succeeded":
                return row.result
            if row.status == "pending" and row.result and row.result.get("started"):
                raise HTTPException(
                    409,
                    "This image request was interrupted. Check portrait history before starting another request.",
                )
            row.result = {"started": True}
            db.commit()
            try:
                result = image_render(
                    cid,
                    ImageInput(
                        instruction=body.instruction,
                        expected_image_id=body.expected_image_id,
                    ),
                    body.editing,
                    db,
                )
            except (ProviderError, HTTPException) as exc:
                fail(
                    db, rid, exc.detail if isinstance(exc, HTTPException) else str(exc)
                )
                raise
            row = db.get(CreatorRequest, rid)
            row.status = "succeeded"
            row.result = result
            db.commit()
            return result

    @app.post("/api/creator/characters/{cid}/duplicate", status_code=201)
    def duplicate_character(cid: UUID, body: CreatorImageInput, request: Request):
        user = owner(request)
        with (
            locks.hold("creator-request:" + str(body.request_id)),
            locks.hold(str(cid)),
            factory() as db,
        ):
            c = character(db, cid, user)
            job = record(
                db,
                body.request_id,
                user,
                "duplicate:" + str(cid),
                body.model_dump(mode="json"),
            )
            if job.status == "succeeded":
                return serialize_character(
                    db, character(db, job.result["character_id"], user)
                )
            original = snapshot(db, c)
            profile = deepcopy(original["profile"])
            profile["name"] = profile["name"][:50] + " · copy"
            clone = Character(
                owner_id=user, original_description=c.original_description
            )
            db.add(clone)
            db.flush()
            db.add(
                ProfileRevision(
                    character_id=clone.id,
                    version=1,
                    profile_json=profile,
                    change_summary="Duplicate character",
                )
            )
            db.add(Conversation(character_id=clone.id))
            target = None
            if c.current_image_id:
                image = db.get(Portrait, c.current_image_id)
                image_id = uid()
                source = settings.image_directory / image.file_path
                if source.is_file():
                    target = settings.image_directory / (image_id + ".png")
                    target.write_bytes(source.read_bytes())
                    db.add(
                        Portrait(
                            id=image_id,
                            character_id=clone.id,
                            parent_image_id=None,
                            provider=image.provider,
                            model=image.model,
                            prompt=image.prompt,
                            file_path=image_id + ".png",
                            version=1,
                        )
                    )
                    clone.current_image_id = image_id
            job.status = "succeeded"
            job.result = {"character_id": clone.id}
            try:
                db.commit()
            except Exception:
                if target:
                    target.unlink(missing_ok=True)
                raise
            return serialize_character(db, clone)

    @app.patch("/api/creator/characters/{cid}/archive")
    def archive_character(cid: UUID, request: Request):
        with locks.hold(str(cid)), factory() as db:
            c = character(db, cid, owner(request))
            c.archived = not c.archived
            db.commit()
            return {"archived": c.archived}

    @app.get("/api/creator/works")
    def works(request: Request):
        with factory() as db:
            return [
                pack(w)
                for w in db.scalars(
                    select(CreatorWork)
                    .where(CreatorWork.owner_id == owner(request))
                    .order_by(CreatorWork.updated_at.desc())
                )
            ]

    @app.post("/api/creator/works", status_code=201)
    def create(body: CreatorCreate, request: Request):
        user = owner(request)
        rid = str(body.request_id)
        with (
            locks.hold("creator-request:" + rid),
            locks.hold("account-bootstrap"),
            ExitStack() as stack,
            factory() as db,
        ):
            from .companion_models import Account

            if user is None and db.scalar(select(Account.id).limit(1)):
                raise HTTPException(401, "Please sign in before saving a story.")
            row = record(db, rid, user, "work", body.model_dump(mode="json"))
            if row.status == "succeeded":
                return pack(work(db, row.result["work_id"], user))
            for cid in sorted({str(c) for c in body.character_ids}):
                stack.enter_context(locks.hold(cid))
            if body.demo:
                cast = sample_cast()
            else:
                if len(set(body.character_ids)) != len(body.character_ids):
                    raise HTTPException(422, "Choose different characters.")
                expected = 1 if body.mode == "play" else 2
                if len(body.character_ids) != expected:
                    raise HTTPException(422, f"Choose {expected} character(s).")
                cast = [
                    snapshot(db, character(db, c, user)) for c in body.character_ids
                ]
                if body.mode == "play":
                    cast.append(
                        {
                            "id": "player",
                            "character_id": None,
                            "profile": Profile(
                                name=body.player_name,
                                short_description=body.player_description
                                or "Played by the author",
                            ).model_dump(),
                            "version": 1,
                            "portrait_id": None,
                            "portrait_url": None,
                        }
                    )
            d = new_document(body, cast)
            w = CreatorWork(owner_id=user, document=d)
            db.add(w)
            db.flush()
            row.status = "succeeded"
            row.result = {"work_id": w.id}
            db.commit()
            return pack(w)

    @app.get("/api/creator/works/{wid}")
    def read(wid: UUID, request: Request):
        with factory() as db:
            return pack(work(db, wid, owner(request)))

    @app.post("/api/creator/works/{wid}/actions")
    def action(wid: UUID, body: CreatorAction, request: Request):
        user = owner(request)
        rid = str(body.request_id)
        with locks.hold("creator-work:" + str(wid)), factory() as db:
            w = work(db, wid, user)
            row = record(
                db, rid, user, "work:" + str(wid), body.model_dump(mode="json")
            )
            if row.status == "succeeded":
                return pack(w)
            if w.revision != body.expected_revision:
                raise HTTPException(
                    409,
                    "This story changed in another window. Reload before retrying; your input is kept.",
                )

            def refresh_cast(cast):
                result = []
                for member in cast:
                    if member["character_id"]:
                        c = character(db, member["character_id"], user)
                        fresh = snapshot(db, c)
                        fresh["id"] = member["id"]
                        result.append(fresh)
                    else:
                        result.append(member)
                return result

            try:
                d = apply_action(w.document, body, generate, refresh_cast)
                save_doc(w, d)
                row.status = "succeeded"
                row.result = {"work_id": w.id}
                db.commit()
            except (ProviderError, HTTPException, ValueError, ValidationError) as exc:
                detail = (
                    exc.detail
                    if isinstance(exc, HTTPException)
                    else str(exc)
                    if isinstance(exc, ProviderError)
                    else "The generated story could not be validated. Your previous draft is safe."
                )
                fail(db, rid, detail)
                if isinstance(exc, (ProviderError, HTTPException)):
                    raise
                raise HTTPException(422, detail) from None
            return pack(w)

    @app.delete("/api/creator/works/{wid}", status_code=204)
    def delete(wid: UUID, request: Request):
        with locks.hold("creator-work:" + str(wid)), factory() as db:
            w = work(db, wid, owner(request))
            for previous in db.scalars(
                select(CreatorRequest).where(CreatorRequest.owner_id == owner(request))
            ):
                if (
                    previous.scope == "work:" + w.id
                    or (previous.result or {}).get("work_id") == w.id
                ):
                    previous.payload = {}
                    previous.status = "deleted"
                    previous.result = {"work_id": w.id, "deleted": True}
            db.delete(w)
            db.commit()

    @app.post("/api/creator/import", status_code=201)
    def import_work(body: CreatorImport, request: Request):
        user = owner(request)
        rid = str(body.request_id)
        if len(body.model_dump_json().encode()) > 5 * 1024 * 1024:
            raise HTTPException(413, "Backups must be smaller than 5 MiB.")
        with locks.hold("creator-request:" + rid), factory() as db:
            row = record(db, rid, user, "import", body.model_dump(mode="json"))
            if row.status == "succeeded":
                return pack(work(db, row.result["work_id"], user))
            d = body.document.model_dump()
            all_ids = (
                set(d["nodes"])
                | set(d["lines"])
                | set(d["casts"])
                | set(d["scenes"])
                | {c["id"] for c in d["checkpoints"]}
                | {f["id"] for f in d["facts"]}
            )
            ids = {key: uid() for key in all_ids}

            def map_values(value):
                if isinstance(value, dict):
                    return {
                        ids.get(k, k): map_values(v)
                        if k
                        not in (
                            "text",
                            "instruction",
                            "name",
                            "title",
                            "premise",
                            "portrait_url",
                            "character_id",
                            "portrait_id",
                            "profile",
                        )
                        else v
                        for k, v in value.items()
                    }
                if isinstance(value, list):
                    return [map_values(v) for v in value]
                return ids.get(value, value) if isinstance(value, str) else value

            d = map_values(d)
            d["title"] = d["title"][:85] + " · imported"
            for members in d["casts"].values():
                for m in members:
                    if m["character_id"]:
                        c = db.get(Character, m["character_id"])
                        image = (
                            db.get(Portrait, m["portrait_id"])
                            if m["portrait_id"]
                            else None
                        )
                        if (
                            not c
                            or c.owner_id != user
                            or (
                                m["portrait_id"]
                                and (not image or image.character_id != c.id)
                            )
                        ):
                            m.update(
                                character_id=None, portrait_id=None, portrait_url=None
                            )
            d = CreatorDocument.model_validate(d).model_dump()
            w = CreatorWork(owner_id=user, document=d)
            db.add(w)
            db.flush()
            row.status = "succeeded"
            row.result = {"work_id": w.id}
            db.commit()
            return pack(w)

    @app.get("/api/creator/works/{wid}/export")
    def export(
        wid: UUID,
        request: Request,
        format: str = "script",
        line_id: str = "",
        scene_id: str = "",
        checkpoint_id: str = "",
    ):
        if format not in ("script", "prose", "json"):
            raise HTTPException(422, "Choose script, prose or json.")
        with factory() as db:
            w = work(db, wid, owner(request))
            d = w.document
            if format == "json":
                text = json.dumps(d, ensure_ascii=False, indent=2)
                ext = "json"
                media = "application/json"
            else:
                line = d["lines"].get(line_id or d["active_line"])
                if checkpoint_id:
                    c = next(
                        (c for c in d["checkpoints"] if c["id"] == checkpoint_id), None
                    )
                    if not c:
                        raise HTTPException(404, "Saved version not found.")
                    line = c["line"]
                if not line:
                    raise HTTPException(404, "Storyline not found.")
                sections = [f"# {d['title']}", f"*{line['name']} · Draft*"]
                previous = None
                for n in path(d, line["head"]):
                    if scene_id and n["scene_id"] != scene_id:
                        continue
                    if previous != n["scene_id"]:
                        sections.append("## " + d["scenes"][n["scene_id"]]["title"])
                        previous = n["scene_id"]
                    names = {
                        m["id"]: m["profile"]["name"] for m in d["casts"][n["cast_id"]]
                    }
                    for b in n["blocks"]:
                        if b["type"] == "dialogue":
                            sections.append(
                                f"**{names[b['speaker']]}**\n\n{b['text']}"
                                if format == "script"
                                else f"{names[b['speaker']]}: “{b['text']}”"
                            )
                        elif b["type"] == "action":
                            sections.append(f"*{b['text']}*")
                        else:
                            sections.append(b["text"])
                text = "\n\n".join(sections)
                ext = "md"
                media = "text/markdown"
            return Response(
                text,
                media_type=media,
                headers={
                    "Content-Disposition": f'attachment; filename="echoloom-story.{ext}"'
                },
            )
