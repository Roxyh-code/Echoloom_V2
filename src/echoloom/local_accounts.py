"""Password-backed identity for this local prototype, not a hosted identity service."""

import hashlib
import hmac
import secrets
import threading
import time
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, Request, Response
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select, update

from .companion_models import Account, LoginSession
from .db import (
    Character,
    Conversation,
    CreatorRequest,
    CreatorWork,
    Portrait,
    RehearsalOperation,
    RehearsalScene,
    Story,
)

COOKIE = "echoloom_session"


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def password_hash(password, salt=None):
    salt = salt or secrets.token_hex(16)
    hashed = hashlib.scrypt(
        password.encode(), salt=bytes.fromhex(salt), n=16384, r=8, p=1
    ).hex()
    return salt + ":" + hashed


class Credentials(BaseModel):
    username: str = Field(min_length=3, max_length=80, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=10, max_length=128)


def register_accounts(app, factory, locks, settings):
    attempts = {}
    guard = threading.Lock()

    def user(db, request):
        key = request.cookies.get(COOKIE, "")
        row = db.get(LoginSession, digest(key)) if key else None
        return (
            row.user_id
            if row and row.expires_at > datetime.now(UTC).isoformat()
            else None
        )

    app.state.account_user = user

    @app.middleware("http")
    async def identity(request: Request, call_next):
        path = request.url.path
        if not path.startswith("/api/") or path == "/api/health":
            return await call_next(request)
        with factory() as db:
            owner = user(db, request)
            request.state.user_id = owner
            has_accounts = db.scalar(select(Account.id).limit(1)) is not None
            # Do not trust a browser-supplied owner or character ID.
            if request.method not in ("GET", "HEAD", "OPTIONS"):
                origin = request.headers.get("origin")
                if origin and origin.rstrip("/") != settings.app_origin.rstrip("/"):
                    return JSONResponse(
                        {"detail": "Untrusted request origin."}, status_code=403
                    )
                if request.headers.get("sec-fetch-site") == "cross-site":
                    return JSONResponse(
                        {"detail": "Cross-site request rejected."}, status_code=403
                    )
            exempt = (
                path.startswith("/api/account/")
                or path == "/api/health"
                or path.endswith("/google-calendar/callback")
            )
            if has_accounts and not exempt:
                if not owner:
                    return JSONResponse(
                        {"detail": "Please sign in to your local account."},
                        status_code=401,
                    )
                parts = path.split("/")
                resource = parts[2] if len(parts) > 2 else ""
                key = parts[3] if len(parts) > 3 else ""
                cid = None
                if resource == "characters" and key and key != "generate":
                    cid = key
                elif resource == "conversations" and key:
                    row = db.get(Conversation, key)
                    cid = row.character_id if row else "missing"
                elif resource == "stories" and key:
                    row = db.get(Story, key)
                    cid = row.character_id if row else "missing"
                elif resource == "images" and key:
                    row = db.get(Portrait, key)
                    cid = row.character_id if row else "missing"
                if cid:
                    char = db.get(Character, cid)
                    if not char or char.owner_id != owner:
                        return JSONResponse(
                            {"detail": "Resource not found."}, status_code=404
                        )
        return await call_next(request)

    @app.get("/api/account/session")
    def session_status(request: Request):
        with factory() as db:
            owner = user(db, request)
            row = db.get(Account, owner) if owner else None
            return {
                "authenticated": bool(row),
                "username": row.username if row else None,
                "setup_required": db.scalar(select(Account.id).limit(1)) is None,
                "local_only": True,
            }

    def establish(db, row, response):
        token = secrets.token_urlsafe(32)
        db.add(
            LoginSession(
                id=digest(token),
                user_id=row.id,
                expires_at=(datetime.now(UTC) + timedelta(days=7)).isoformat(),
            )
        )
        db.commit()
        response.set_cookie(
            COOKIE,
            token,
            httponly=True,
            samesite="lax",
            secure=settings.app_origin.startswith("https://"),
            max_age=604800,
            path="/",
        )
        return {"authenticated": True, "username": row.username}

    @app.post("/api/account/register")
    def register(body: Credentials, response: Response):
        with locks.hold("account-bootstrap"), factory() as db:
            first = db.scalar(select(Account.id).limit(1)) is None
            if not first and not settings.allow_additional_accounts:
                raise HTTPException(
                    403,
                    "This local installation already has an account. Please sign in.",
                )
            if db.scalar(
                select(Account.id).where(Account.username == body.username.lower())
            ):
                raise HTTPException(409, "That account cannot be created.")
            row = Account(
                username=body.username.lower(),
                password_hash=password_hash(body.password),
            )
            db.add(row)
            db.flush()
            if first:
                db.execute(
                    update(Character)
                    .where(Character.owner_id.is_(None))
                    .values(owner_id=row.id)
                )
                for model in (
                    CreatorWork,
                    CreatorRequest,
                    RehearsalScene,
                    RehearsalOperation,
                ):
                    db.execute(
                        update(model)
                        .where(model.owner_id.is_(None))
                        .values(owner_id=row.id)
                    )
            return establish(db, row, response)

    @app.post("/api/account/login")
    def login(body: Credentials, request: Request, response: Response):
        address = request.client.host if request.client else "local"
        with guard:
            recent = [
                t for t in attempts.get(address, []) if t > time.monotonic() - 300
            ]
            if len(recent) >= 12:
                raise HTTPException(429, "Too many attempts. Please wait five minutes.")
            attempts[address] = [*recent, time.monotonic()]
        with factory() as db:
            row = db.scalar(
                select(Account).where(Account.username == body.username.lower())
            )
            stored = row.password_hash if row else password_hash("unavailable-account")
            salt = stored.split(":")[0]
            if (
                not hmac.compare_digest(password_hash(body.password, salt), stored)
                or not row
            ):
                raise HTTPException(401, "Incorrect username or password.")
            return establish(db, row, response)

    @app.post("/api/account/logout")
    def logout(request: Request, response: Response):
        with factory() as db:
            row = db.get(LoginSession, digest(request.cookies.get(COOKIE, "")))
            if row:
                db.delete(row)
                db.commit()
        response.delete_cookie(COOKIE, path="/")
        return {"authenticated": False}
