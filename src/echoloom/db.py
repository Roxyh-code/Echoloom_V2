from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker


def uid() -> str:
    return str(uuid4())


def now() -> str:
    return datetime.now(UTC).isoformat()


class Base(DeclarativeBase):
    pass


class Character(Base):
    __tablename__ = "characters"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    original_description: Mapped[str] = mapped_column(Text)
    current_profile_version: Mapped[int] = mapped_column(default=1)
    current_image_id: Mapped[str | None] = mapped_column(String(36), default=None)
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class ProfileRevision(Base):
    __tablename__ = "character_profiles"
    __table_args__ = (UniqueConstraint("character_id", "version"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    version: Mapped[int]
    profile_json: Mapped[dict] = mapped_column(JSON)
    change_summary: Mapped[str] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(default=now)


class Proposal(Base):
    __tablename__ = "profile_proposals"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    base_version: Mapped[int]
    profile_json: Mapped[dict] = mapped_column(JSON)
    diff: Mapped[list] = mapped_column(JSON)
    explanation: Mapped[str] = mapped_column(Text)
    accepted_version: Mapped[int | None] = mapped_column(default=None)
    created_at: Mapped[str] = mapped_column(default=now)


class Conversation(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "request_id", "role"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(36))
    role: Mapped[str] = mapped_column(String(12))
    content: Mapped[str] = mapped_column(Text)
    profile_version: Mapped[int]
    created_at: Mapped[str] = mapped_column(default=now)


class Portrait(Base):
    __tablename__ = "character_images"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    parent_image_id: Mapped[str | None] = mapped_column(String(36))
    provider: Mapped[str] = mapped_column(String(50))
    model: Mapped[str] = mapped_column(String(200))
    prompt: Mapped[str] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(100))
    version: Mapped[int]
    created_at: Mapped[str] = mapped_column(default=now)
    __table_args__ = (UniqueConstraint("character_id", "version"),)


class ImageRequest(Base):
    __tablename__ = "image_requests"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[str] = mapped_column(default=now)


def make_engine(url: str):
    engine = create_engine(
        url,
        connect_args={"check_same_thread": False, "timeout": 20}
        if url.startswith("sqlite")
        else {},
    )
    if url.startswith("sqlite"):

        @event.listens_for(engine, "connect")
        def configure(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")
            connection.execute("PRAGMA journal_mode=WAL")

    return engine


def sessions(engine):
    return sessionmaker(engine, expire_on_commit=False)
