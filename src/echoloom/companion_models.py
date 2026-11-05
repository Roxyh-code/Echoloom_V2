"""Private calendar storage. Credentials are encrypted before reaching this layer."""

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base, now, uid


class Account(Base):
    __tablename__ = "user_accounts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    username: Mapped[str] = mapped_column(String(80), unique=True)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)


class LoginSession(Base):
    __tablename__ = "login_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="CASCADE")
    )
    expires_at: Mapped[str]


class CalendarConnection(Base):
    __tablename__ = "calendar_connections"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="CASCADE"), unique=True
    )
    credentials: Mapped[str] = mapped_column(Text)
    email: Mapped[str] = mapped_column(String(254), default="")
    status: Mapped[str] = mapped_column(default="syncing")
    calendar_timezone: Mapped[str] = mapped_column(default="UTC")
    sync_token: Mapped[str | None] = mapped_column(Text, default=None)
    last_sync: Mapped[str | None] = mapped_column(default=None)
    next_sync: Mapped[str] = mapped_column(default=now)
    full_sync_at: Mapped[str | None] = mapped_column(default=None)
    created_at: Mapped[str] = mapped_column(default=now)


class OAuthAttempt(Base):
    __tablename__ = "calendar_oauth_attempts"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="CASCADE")
    )
    verifier: Mapped[str] = mapped_column(Text)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE")
    )
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    timezone: Mapped[str]
    expires_at: Mapped[str]


class CompanionSettings(Base):
    __tablename__ = "companion_settings"
    user_id: Mapped[str] = mapped_column(
        ForeignKey("user_accounts.id", ondelete="CASCADE"), primary_key=True
    )
    character_id: Mapped[str | None] = mapped_column(
        ForeignKey("characters.id", ondelete="SET NULL"), default=None
    )
    conversation_id: Mapped[str | None] = mapped_column(
        ForeignKey("conversations.id", ondelete="SET NULL"), default=None
    )
    enabled: Mapped[bool] = mapped_column(default=False)
    timezone: Mapped[str] = mapped_column(default="UTC")
    quiet_start: Mapped[str] = mapped_column(default="22:00")
    quiet_end: Mapped[str] = mapped_column(default="08:00")
    snoozed_until: Mapped[str | None] = mapped_column(default=None)


class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    __table_args__ = (UniqueConstraint("connection_id", "provider_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("calendar_connections.id", ondelete="CASCADE"), index=True
    )
    provider_id: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    starts_at: Mapped[str]
    ends_at: Mapped[str]
    all_day: Mapped[bool]
    private: Mapped[bool]
    category: Mapped[str]
    status: Mapped[str]
    fingerprint: Mapped[str]
    recurring_id: Mapped[str | None] = mapped_column(Text, default=None)


class CompanionTask(Base):
    __tablename__ = "companion_tasks"
    __table_args__ = (UniqueConstraint("connection_id", "event_key", "kind"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("calendar_connections.id", ondelete="CASCADE"), index=True
    )
    event_id: Mapped[str | None] = mapped_column(
        ForeignKey("calendar_events.id", ondelete="SET NULL"), default=None
    )
    event_key: Mapped[str] = mapped_column(Text)
    kind: Mapped[str]
    fingerprint: Mapped[str]
    due_at: Mapped[str]
    expires_at: Mapped[str]
    status: Mapped[str] = mapped_column(default="pending")
    attempts: Mapped[int] = mapped_column(default=0)
    delivered_at: Mapped[str | None] = mapped_column(default=None)


class EventMemory(Base):
    __tablename__ = "companion_event_memory"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    connection_id: Mapped[str] = mapped_column(
        ForeignKey("calendar_connections.id", ondelete="CASCADE")
    )
    event_id: Mapped[str] = mapped_column(
        ForeignKey("calendar_events.id", ondelete="CASCADE")
    )
    user_quote: Mapped[str] = mapped_column(Text)
    expires_at: Mapped[str]
