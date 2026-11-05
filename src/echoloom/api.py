import threading
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from PIL import Image, UnidentifiedImageError
from sqlalchemy import func, inspect, select, update
from sqlalchemy.orm import Session

from .config import Settings
from .db import (
    Character,
    Conversation,
    ImageRequest,
    Message,
    Portrait,
    ProfileRevision,
    Proposal,
    Story,
    allocate_timeline,
    make_engine,
    now,
    sessions,
    uid,
)
from .providers import (
    OpenAIImages,
    OpenAIText,
    ProviderError,
    ProviderUnavailable,
    chat_context,
)
from .schemas import (
    ChatInput,
    ConfirmInput,
    GenerateInput,
    ImageInput,
    Profile,
    ProfileUpdate,
    RefineInput,
    RestoreInput,
    apply_changes,
)


class Locks:
    """Serialize each character's mutations in the single-worker local server."""

    def __init__(self):
        self.guard = threading.Lock()
        self.active = {}

    @contextmanager
    def hold(self, key):
        with self.guard:
            lock, refs = self.active.get(key, (threading.Lock(), 0))
            self.active[key] = (lock, refs + 1)
        try:
            with lock:
                yield
        finally:
            with self.guard:
                _, refs = self.active[key]
                if refs == 1:
                    del self.active[key]
                else:
                    self.active[key] = (lock, refs - 1)


def create_app(
    settings: Settings | None = None,
    text_provider=None,
    image_provider=None,
    engine=None,
    calendar_provider=None,
    clock=None,
):
    settings = settings or Settings()
    if settings.database_url.startswith("sqlite:///./"):
        Path(settings.database_url.removeprefix("sqlite:///./")).parent.mkdir(
            parents=True, exist_ok=True
        )
    engine = engine or make_engine(settings.database_url)
    factory = sessions(engine)
    locks = Locks()
    app = FastAPI(title="EchoLoom", version="0.1.0")
    app.state.text = text_provider or OpenAIText(settings)
    app.state.images = image_provider or OpenAIImages(settings)
    app.state.settings = settings

    def get_db():
        with factory() as session:
            yield session

    DbSession = Annotated[Session, Depends(get_db)]

    @app.exception_handler(ProviderUnavailable)
    def unavailable(_, exc):
        return JSONResponse(status_code=503, content={"detail": str(exc)})

    @app.exception_handler(ProviderError)
    def provider_error(_, exc):
        return JSONResponse(status_code=502, content={"detail": str(exc)})

    def character(db, cid):
        value = db.get(Character, str(cid))
        if not value:
            raise HTTPException(404, "Character not found.")
        return value

    def revision(db, c, version=None):
        value = db.scalar(
            select(ProfileRevision).where(
                ProfileRevision.character_id == c.id,
                ProfileRevision.version == (version or c.current_profile_version),
            )
        )
        if not value:
            raise HTTPException(404, "Profile version not found.")
        return value

    def serialize(db, c):
        conv = db.scalar(
            select(Conversation)
            .where(Conversation.character_id == c.id)
            .order_by(Conversation.created_at)
        )
        return {
            "id": c.id,
            "profile": revision(db, c).profile_json,
            "profile_version": c.current_profile_version,
            "current_image_id": c.current_image_id,
            "conversation_id": conv.id if conv else None,
            "original_description": c.original_description,
            "created_at": c.created_at,
            "updated_at": c.updated_at,
        }

    def check_version(c, expected):
        if c.current_profile_version != expected:
            raise HTTPException(
                409, "The character was updated in another page. Reload before editing."
            )

    def save_profile(db, c, profile, expected, summary):
        check_version(c, expected)
        changed = db.execute(
            update(Character)
            .where(Character.id == c.id, Character.current_profile_version == expected)
            .values(current_profile_version=expected + 1, updated_at=now())
        )
        if changed.rowcount != 1:
            raise HTTPException(409, "Version conflict. Please reload.")
        db.add(
            ProfileRevision(
                character_id=c.id,
                version=expected + 1,
                profile_json=profile.model_dump(),
                change_summary=summary,
            )
        )
        db.flush()
        db.refresh(c)

    @app.get("/api/health")
    def health():
        ready = inspect(engine).has_table("characters")
        return JSONResponse(
            status_code=200 if ready else 503,
            content={
                "database_ready": ready,
                "story_database_ready": inspect(engine).has_table("stories"),
                "companion_database_ready": inspect(engine).has_table(
                    "calendar_connections"
                ),
                "text_configured": bool(
                    settings.llm_api_key.get_secret_value()
                    and settings.llm_model
                    and settings.llm_provider == "openai"
                ),
                "image_configured": bool(
                    (
                        settings.image_api_key.get_secret_value()
                        or settings.llm_api_key.get_secret_value()
                    )
                    and settings.image_model
                    and settings.image_provider == "openai"
                ),
                "max_profile_input_chars": settings.max_profile_input_chars,
                "mode": "local-single-user",
            },
        )

    @app.get("/api/characters")
    def list_characters(request: Request, db: DbSession):
        return [
            serialize(db, c)
            for c in db.scalars(
                select(Character)
                .where(Character.owner_id == request.state.user_id)
                .order_by(Character.updated_at.desc())
            )
        ]

    @app.post("/api/characters/generate", status_code=201)
    def generate(body: GenerateInput, request: Request, db: DbSession):
        if len(body.description) > settings.max_profile_input_chars:
            raise HTTPException(
                422,
                f"The description must not exceed {settings.max_profile_input_chars} characters.",
            )
        profile = Profile.model_validate(app.state.text.generate(body.description))
        from .companion_models import Account

        with locks.hold("account-bootstrap"):
            if request.state.user_id is None and db.scalar(select(Account.id).limit(1)):
                raise HTTPException(
                    401,
                    "A local account was created. Please sign in before saving a character.",
                )
            c = Character(
                original_description=body.description, owner_id=request.state.user_id
            )
            db.add(c)
            db.flush()
            db.add(
                ProfileRevision(
                    character_id=c.id,
                    version=1,
                    profile_json=profile.model_dump(),
                    change_summary="Create Character",
                )
            )
            db.add(Conversation(character_id=c.id))
            db.commit()
            return serialize(db, c)

    @app.get("/api/characters/{cid}")
    def get_character(cid: UUID, db: DbSession):
        return serialize(db, character(db, cid))

    @app.patch("/api/characters/{cid}")
    def edit(cid: UUID, body: ProfileUpdate, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            check_version(c, body.expected_version)
            if body.profile.model_dump() != revision(db, c).profile_json:
                save_profile(db, c, body.profile, body.expected_version, "Manual edit")
                db.commit()
            return serialize(db, c)

    @app.delete("/api/characters/{cid}", status_code=204)
    def remove(cid: UUID, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            files = list(
                db.scalars(
                    select(Portrait.file_path).where(Portrait.character_id == c.id)
                )
            )
            db.delete(c)
            db.commit()
            for file in files:
                (settings.image_directory / file).unlink(missing_ok=True)

    @app.post("/api/characters/{cid}/refine")
    def refine(cid: UUID, body: RefineInput, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            check_version(c, body.expected_version)
            profile = Profile.model_validate(revision(db, c).profile_json)
            proposal = app.state.text.refine(profile, body.instruction)
            try:
                proposed, diff = apply_changes(profile, proposal)
            except ValueError:
                raise ProviderError(
                    "The model proposed invalid field changes. Please retry."
                ) from None
            if not diff:
                raise HTTPException(
                    422,
                    "The model did not propose any changes. Try a different instruction.",
                )
            item = Proposal(
                character_id=c.id,
                base_version=c.current_profile_version,
                profile_json=proposed.model_dump(),
                diff=diff,
                explanation=proposal.explanation,
            )
            db.add(item)
            db.commit()
            return {
                "proposal_id": item.id,
                "base_version": item.base_version,
                "changes": item.diff,
                "explanation": item.explanation,
            }

    @app.post("/api/characters/{cid}/refine/confirm")
    def confirm(cid: UUID, body: ConfirmInput, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            item = db.get(Proposal, str(body.proposal_id))
            if not item or item.character_id != c.id:
                raise HTTPException(404, "Refinement proposal not found.")
            if item.accepted_version is not None:
                return serialize(db, c)
            save_profile(
                db,
                c,
                Profile.model_validate(item.profile_json),
                item.base_version,
                item.explanation,
            )
            item.accepted_version = c.current_profile_version
            db.commit()
            return serialize(db, c)

    def display_summary(summary):
        # Translate legacy system labels for display without modifying stored revisions.
        if summary == "\u521b\u5efa\u89d2\u8272":
            return "Create Character"
        if summary == "\u624b\u52a8\u7f16\u8f91":
            return "Manual edit"
        prefix = "\u6062\u590d\u81ea\u7248\u672c "
        if summary.startswith(prefix) and summary[len(prefix) :].isdigit():
            return "Restored from version " + summary[len(prefix) :]
        return summary

    @app.get("/api/characters/{cid}/versions")
    def versions(cid: UUID, db: DbSession):
        c = character(db, cid)
        return [
            {
                "version": r.version,
                "profile": r.profile_json,
                "change_summary": display_summary(r.change_summary),
                "created_at": r.created_at,
            }
            for r in db.scalars(
                select(ProfileRevision)
                .where(ProfileRevision.character_id == c.id)
                .order_by(ProfileRevision.version.desc())
            )
        ]

    @app.post("/api/characters/{cid}/restore")
    def restore(cid: UUID, body: RestoreInput, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            profile = Profile.model_validate(revision(db, c, body.version).profile_json)
            save_profile(
                db,
                c,
                profile,
                body.expected_version,
                f"Restored from version {body.version}",
            )
            db.commit()
            return serialize(db, c)

    @app.post("/api/characters/{cid}/conversations", status_code=201)
    def new_conversation(cid: UUID, db: DbSession):
        c = character(db, cid)
        conv = Conversation(character_id=c.id)
        db.add(conv)
        db.commit()
        return {"id": conv.id, "created_at": conv.created_at}

    @app.get("/api/characters/{cid}/conversations")
    def list_conversations(cid: UUID, db: DbSession):
        c = character(db, cid)
        return [
            {"id": r.id, "created_at": r.created_at}
            for r in db.scalars(
                select(Conversation)
                .where(Conversation.character_id == c.id)
                .order_by(Conversation.created_at)
            )
        ]

    def conversation(db, conv_id):
        conv = db.get(Conversation, str(conv_id))
        if not conv:
            raise HTTPException(404, "Conversation not found.")
        return conv

    def messages(db, conv_id):
        return [
            {
                "id": m.id,
                "role": m.role,
                "source_type": m.source_type,
                "content": m.content,
                "profile_version": m.profile_version,
                "request_id": m.request_id,
                "created_at": m.created_at,
            }
            for m in db.scalars(
                select(Message)
                .where(Message.conversation_id == str(conv_id))
                .order_by(Message.timeline_order)
            )
        ]

    @app.get("/api/conversations/{conv_id}/messages")
    def get_messages(conv_id: UUID, db: DbSession):
        conversation(db, conv_id)
        return messages(db, conv_id)

    @app.post("/api/conversations/{conv_id}/messages")
    def send(conv_id: UUID, body: ChatInput, db: DbSession):
        conv = conversation(db, conv_id)
        key = conv.character_id
        # Release the read transaction while waiting on another local request.
        db.rollback()
        with locks.hold(key):
            conv = conversation(db, conv_id)
            c = character(db, conv.character_id)
            existing = db.scalar(
                select(Message).where(
                    Message.conversation_id == conv.id,
                    Message.request_id == str(body.request_id),
                    Message.role == "user",
                )
            )
            if existing:
                if existing.content != body.content:
                    raise HTTPException(
                        409, "This request ID was already used for a different message."
                    )
                return messages(db, conv.id)
            # Bound rows read from DB too; old messages remain on disk.
            recent = list(
                db.scalars(
                    select(Message)
                    .where(Message.conversation_id == conv.id)
                    .order_by(Message.timeline_order.desc())
                    .limit(100)
                )
            )
            history = [
                {"role": m.role, "content": m.content, "source_type": m.source_type}
                for m in reversed(recent)
            ]
            frame = app.state.companion.chat_frame(db, c, body.content)
            try:
                context = chat_context(
                    Profile.model_validate(revision(db, c).profile_json),
                    history,
                    body.content,
                    settings,
                    calendar_frame=frame,
                )
            except ValueError as exc:
                raise HTTPException(422, str(exc)) from None
            response = app.state.text.chat(context)
            if not isinstance(response, str) or not response.strip():
                raise ProviderError("The model did not return a valid reply.")
            # Both messages commit together. Failed remote calls leave neither a false reply nor a duplicate user turn.
            orders = allocate_timeline(db, conv.id, 2)
            for order, (role, content) in zip(
                orders, (("user", body.content), ("assistant", response)), strict=True
            ):
                db.add(
                    Message(
                        conversation_id=conv.id,
                        timeline_order=order,
                        request_id=str(body.request_id),
                        role=role,
                        content=content,
                        profile_version=c.current_profile_version,
                        created_at=now(),
                    )
                )
            app.state.companion.remember(db, c, body.content, frame)
            conv.updated_at = c.updated_at = now()
            db.commit()
            return messages(db, conv.id)

    def portrait(db, cid, image_id):
        item = db.get(Portrait, str(image_id))
        if not item or item.character_id != str(cid):
            raise HTTPException(404, "Image not found.")
        return item

    def image_json(item):
        return {
            "id": item.id,
            "parent_image_id": item.parent_image_id,
            "provider": item.provider,
            "model": item.model,
            "prompt": item.prompt,
            "version": item.version,
            "created_at": item.created_at,
            "url": f"/api/characters/{item.character_id}/images/{item.id}/file",
        }

    def render(cid, body, editing, db):
        with locks.hold(str(cid)):
            c = character(db, cid)
            if c.current_image_id != (
                str(body.expected_image_id) if body.expected_image_id else None
            ):
                raise HTTPException(
                    409, "The current portrait has changed. Refresh before retrying."
                )
            source = None
            parent_id = None
            if editing:
                if not c.current_image_id or not body.instruction.strip():
                    raise HTTPException(
                        422, "Select a portrait and enter an edit instruction first."
                    )
                parent = portrait(db, c.id, c.current_image_id)
                source = (settings.image_directory / parent.file_path).read_bytes()
                parent_id = parent.id
            since = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
            count = db.scalar(
                select(func.count())
                .select_from(ImageRequest)
                .where(
                    ImageRequest.character_id == c.id, ImageRequest.created_at >= since
                )
            )
            if count >= settings.image_requests_per_hour:
                raise HTTPException(
                    429,
                    "This character has reached its hourly image request limit. Please try again later.",
                )
            profile = Profile.model_validate(revision(db, c).profile_json)
            prompt = (
                "Edit this existing fictional character portrait. Preserve identity and all details except "
                "the following requested changes: " + body.instruction
                if editing
                else "Create one fictional character portrait. No text or watermark. Style: "
                + profile.visual_style
                + ". Character appearance: "
                + profile.appearance.model_dump_json()
                + ". Description: "
                + profile.short_description
            )
            db.add(ImageRequest(character_id=c.id))
            db.commit()  # Failed requests also count toward the paid-call budget.
            data = app.state.images.render(prompt, source)
            if len(data) > settings.max_image_bytes:
                raise ProviderError("The image exceeds the size limit.")
            try:
                with Image.open(BytesIO(data)) as image:
                    if image.width * image.height > 16_000_000:
                        raise ProviderError("The image resolution exceeds the limit.")
                    normalized = BytesIO()
                    image.convert("RGB").save(normalized, format="PNG")
                data = normalized.getvalue()
                if len(data) > settings.max_image_bytes:
                    raise ProviderError("The image exceeds the size limit.")
            except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
                raise ProviderError(
                    "The image service did not return a valid image."
                ) from None
            image_id = uid()
            version = (
                db.scalar(
                    select(func.max(Portrait.version)).where(
                        Portrait.character_id == c.id
                    )
                )
                or 0
            ) + 1
            item = Portrait(
                id=image_id,
                character_id=c.id,
                parent_image_id=parent_id,
                provider=settings.image_provider,
                model=settings.image_model,
                prompt=prompt,
                file_path=image_id + ".png",
                version=version,
            )
            settings.image_directory.mkdir(parents=True, exist_ok=True)
            target = settings.image_directory / item.file_path
            target.write_bytes(data)
            try:
                db.add(item)
                db.commit()
            except Exception:
                target.unlink(missing_ok=True)
                raise
            return image_json(item)

    @app.post("/api/characters/{cid}/images/generate", status_code=201)
    def generate_image(cid: UUID, body: ImageInput, db: DbSession):
        return render(cid, body, False, db)

    @app.post("/api/characters/{cid}/images/edit", status_code=201)
    def edit_image(cid: UUID, body: ImageInput, db: DbSession):
        return render(cid, body, True, db)

    @app.get("/api/characters/{cid}/images")
    def images(cid: UUID, db: DbSession):
        character(db, cid)
        return [
            image_json(item)
            for item in db.scalars(
                select(Portrait)
                .where(Portrait.character_id == str(cid))
                .order_by(Portrait.version.desc())
            )
        ]

    @app.get("/api/characters/{cid}/images/{image_id}/file")
    def image_file(cid: UUID, image_id: UUID, db: DbSession):
        item = portrait(db, cid, image_id)
        return FileResponse(
            settings.image_directory / item.file_path, media_type="image/png"
        )

    @app.post("/api/characters/{cid}/images/{image_id}/select")
    def select_image(cid: UUID, image_id: UUID, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            item = portrait(db, cid, image_id)
            c.current_image_id = item.id
            c.updated_at = now()
            db.commit()
            return serialize(db, c)

    @app.delete("/api/characters/{cid}/images/{image_id}", status_code=204)
    def discard_image(cid: UUID, image_id: UUID, db: DbSession):
        with locks.hold(str(cid)):
            c = character(db, cid)
            item = portrait(db, cid, image_id)
            if db.scalar(select(Story.id).where(Story.portrait_id == item.id)):
                raise HTTPException(
                    409, "This portrait is used by a saved story and must be preserved."
                )
            if c.current_image_id == item.id:
                raise HTTPException(
                    409, "Select another portrait before deleting this image."
                )
            if db.scalar(
                select(Portrait.id).where(Portrait.parent_image_id == item.id)
            ):
                raise HTTPException(
                    409,
                    "This image is the source of another revision. Keep it to preserve the revision history.",
                )
            db.delete(item)
            db.commit()
            (settings.image_directory / item.file_path).unlink(missing_ok=True)

    from .story_service import register_story_routes

    register_story_routes(app, factory, locks, settings)
    from .companion_service import register_companion
    from .local_accounts import register_accounts

    register_accounts(app, factory, locks, settings)
    register_companion(app, factory, locks, settings, calendar_provider, clock)
    return app


app = create_app()
