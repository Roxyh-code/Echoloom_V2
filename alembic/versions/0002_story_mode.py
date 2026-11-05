"""Independent stories and a stable mixed conversation timeline."""

import sqlalchemy as sa

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "conversations",
        sa.Column(
            "next_timeline_order", sa.Integer(), nullable=False, server_default="0"
        ),
    )
    op.add_column(
        "messages",
        sa.Column("timeline_order", sa.Integer(), nullable=False, server_default="0"),
    )
    connection = op.get_bind()
    counts = {}
    for row in connection.execute(
        sa.text(
            "SELECT id, conversation_id FROM messages ORDER BY conversation_id, created_at, id"
        )
    ).mappings():
        count = counts.get(row["conversation_id"], 0) + 1
        counts[row["conversation_id"]] = count
        connection.execute(
            sa.text("UPDATE messages SET timeline_order=:n WHERE id=:id"),
            {"n": count, "id": row["id"]},
        )
    for conv, count in counts.items():
        connection.execute(
            sa.text("UPDATE conversations SET next_timeline_order=:n WHERE id=:id"),
            {"n": count, "id": conv},
        )
    # Freeze this migration independently of future ORM model changes.
    op.create_table(
        "stories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "character_id",
            sa.String(36),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "origin_conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("creation_request_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(160), nullable=False),
        sa.Column("snapshot_profile_json", sa.JSON(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("portrait_id", sa.String(36)),
        sa.Column("player_name", sa.String(100), nullable=False),
        sa.Column("setup", sa.JSON(), nullable=False),
        sa.Column("language", sa.String(10), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("stable_status", sa.String(30), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active_segment_id", sa.String(36)),
        sa.Column("reading_segment_id", sa.String(36)),
        sa.Column("last_revealed_block_id", sa.String(36)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "story_segments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "story_id",
            sa.String(36),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("parent_segment_id", sa.String(36)),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("input_event", sa.JSON(), nullable=False),
        sa.Column("blocks", sa.JSON(), nullable=False),
        sa.Column("ending", sa.JSON(), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("confirmed_facts", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_table(
        "story_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "story_id",
            sa.String(36),
            sa.ForeignKey("stories.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("expected_revision", sa.Integer(), nullable=False),
        sa.Column("operation", sa.String(20), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("result_segment_id", sa.String(36)),
        sa.Column("result_json", sa.JSON()),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("story_id", "request_id"),
    )
    op.create_table(
        "chat_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "story_id", sa.String(36), sa.ForeignKey("stories.id", ondelete="SET NULL")
        ),
        sa.Column("creation_request_id", sa.String(36), nullable=False),
        sa.Column("creation_payload", sa.JSON(), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("fallback_title", sa.String(160), nullable=False),
        sa.Column("preview", sa.Text(), nullable=False),
        sa.Column("timeline_order", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("conversation_id", "creation_request_id"),
        sa.UniqueConstraint("conversation_id", "timeline_order"),
    )
    for table, cols in {
        "stories": ["character_id", "origin_conversation_id", "portrait_id"],
        "story_segments": ["story_id"],
        "story_requests": ["story_id"],
        "chat_events": ["conversation_id", "story_id"],
    }.items():
        for col in cols:
            op.create_index(f"ix_{table}_{col}", table, [col])


def downgrade():
    for table in ("chat_events", "story_requests", "story_segments", "stories"):
        op.drop_table(table)
    op.drop_column("messages", "timeline_order")
    op.drop_column("conversations", "next_timeline_order")
