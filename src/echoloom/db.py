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
    owner_id: Mapped[str | None] = mapped_column(
        ForeignKey("user_accounts.id"), default=None, index=True
    )
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
    next_timeline_order: Mapped[int] = mapped_column(default=0, server_default="0")
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class Message(Base):
    trigger_type: Mapped[str | None] = mapped_column(String(30), default=None)
    source_event_id: Mapped[str | None] = mapped_column(String(36), default=None)
    source_type: Mapped[str] = mapped_column(
        default="user_chat", server_default="user_chat"
    )
    source_task_id: Mapped[str | None] = mapped_column(
        String(36), unique=True, index=True, default=None
    )
    __tablename__ = "messages"
    timeline_order: Mapped[int] = mapped_column(default=0, server_default="0")
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


class Story(Base):
    __tablename__ = "stories"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    character_id: Mapped[str] = mapped_column(
        ForeignKey("characters.id", ondelete="CASCADE"), index=True
    )
    origin_conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    creation_request_id: Mapped[str] = mapped_column(String(36))
    title: Mapped[str] = mapped_column(String(160))
    snapshot_profile_json: Mapped[dict] = mapped_column(JSON)
    profile_version: Mapped[int]
    portrait_id: Mapped[str | None] = mapped_column(String(36), index=True)
    player_name: Mapped[str] = mapped_column(String(100))
    setup: Mapped[dict] = mapped_column(JSON)
    language: Mapped[str] = mapped_column(String(10), default="en")
    status: Mapped[str] = mapped_column(String(30), default="ready")
    stable_status: Mapped[str] = mapped_column(String(30), default="ready")
    revision: Mapped[int] = mapped_column(default=0)
    active_segment_id: Mapped[str | None] = mapped_column(String(36), default=None)
    reading_segment_id: Mapped[str | None] = mapped_column(String(36), default=None)
    last_revealed_block_id: Mapped[str | None] = mapped_column(String(36), default=None)
    last_error: Mapped[str | None] = mapped_column(Text, default=None)
    created_at: Mapped[str] = mapped_column(default=now)
    updated_at: Mapped[str] = mapped_column(default=now)


class StorySegment(Base):
    __tablename__ = "story_segments"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    parent_segment_id: Mapped[str | None] = mapped_column(String(36))
    revision: Mapped[int]
    input_event: Mapped[dict] = mapped_column(JSON)
    blocks: Mapped[list] = mapped_column(JSON)
    ending: Mapped[dict] = mapped_column(JSON)
    summary: Mapped[str] = mapped_column(Text)
    confirmed_facts: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(default=now)


class StoryRequest(Base):
    __tablename__ = "story_requests"
    __table_args__ = (UniqueConstraint("story_id", "request_id"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(
        ForeignKey("stories.id", ondelete="CASCADE"), index=True
    )
    request_id: Mapped[str] = mapped_column(String(36))
    expected_revision: Mapped[int]
    operation: Mapped[str] = mapped_column(String(20))
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20))
    result_segment_id: Mapped[str | None] = mapped_column(String(36), default=None)
    result_json: Mapped[dict | None] = mapped_column(JSON, default=None)
    created_at: Mapped[str] = mapped_column(default=now)


class ChatEvent(Base):
    __tablename__ = "chat_events"
    __table_args__ = (
        UniqueConstraint("conversation_id", "creation_request_id"),
        UniqueConstraint("conversation_id", "timeline_order"),
    )
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    conversation_id: Mapped[str] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    story_id: Mapped[str | None] = mapped_column(
        ForeignKey("stories.id", ondelete="SET NULL"), index=True
    )
    creation_request_id: Mapped[str] = mapped_column(String(36))
    creation_payload: Mapped[dict] = mapped_column(JSON)
    kind: Mapped[str] = mapped_column(String(20), default="story_card")
    fallback_title: Mapped[str] = mapped_column(String(160))
    preview: Mapped[str] = mapped_column(Text)
    timeline_order: Mapped[int]
    created_at: Mapped[str] = mapped_column(default=now)


def allocate_timeline(session, conversation_id, count=1):
    from sqlalchemy import update

    end = session.scalar(
        update(Conversation)
        .where(Conversation.id == conversation_id)
        .values(next_timeline_order=Conversation.next_timeline_order + count)
        .returning(Conversation.next_timeline_order)
    )
    if end is None:
        raise ValueError("Conversation not found")
    return list(range(end - count + 1, end + 1))


# Register companion tables with the shared metadata.
from . import companion_models  # noqa: F401
