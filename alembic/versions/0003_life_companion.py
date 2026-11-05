"""Local accounts and private read-only calendar companion.

Frozen schema: never import mutable application metadata into this migration.
"""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    op.create_table(
        "user_accounts",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("username"),
    )
    op.create_table(
        "login_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.String(), nullable=False),
    )
    op.create_table(
        "calendar_connections",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("credentials", sa.Text(), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("calendar_timezone", sa.String(), nullable=False),
        sa.Column("sync_token", sa.Text(), nullable=True),
        sa.Column("last_sync", sa.String(), nullable=True),
        sa.Column("next_sync", sa.String(), nullable=False),
        sa.Column("full_sync_at", sa.String(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.UniqueConstraint("user_id"),
    )
    op.create_table(
        "calendar_oauth_attempts",
        sa.Column("id", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("verifier", sa.Text(), nullable=False),
        sa.Column(
            "character_id",
            sa.String(length=36),
            sa.ForeignKey("characters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("conversations.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
    )
    op.create_table(
        "companion_settings",
        sa.Column(
            "user_id",
            sa.String(length=36),
            sa.ForeignKey("user_accounts.id", ondelete="CASCADE"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "character_id",
            sa.String(length=36),
            sa.ForeignKey("characters.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "conversation_id",
            sa.String(length=36),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("timezone", sa.String(), nullable=False),
        sa.Column("quiet_start", sa.String(), nullable=False),
        sa.Column("quiet_end", sa.String(), nullable=False),
        sa.Column("snoozed_until", sa.String(), nullable=True),
    )
    op.create_table(
        "calendar_events",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "connection_id",
            sa.String(length=36),
            sa.ForeignKey("calendar_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("provider_id", sa.Text(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("starts_at", sa.String(), nullable=False),
        sa.Column("ends_at", sa.String(), nullable=False),
        sa.Column("all_day", sa.Boolean(), nullable=False),
        sa.Column("private", sa.Boolean(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("recurring_id", sa.Text(), nullable=True),
        sa.UniqueConstraint("connection_id", "provider_id"),
    )
    op.create_index(
        "ix_calendar_events_connection_id",
        "calendar_events",
        ["connection_id"],
        unique=False,
    )
    op.create_table(
        "companion_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "connection_id",
            sa.String(length=36),
            sa.ForeignKey("calendar_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("calendar_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("event_key", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("fingerprint", sa.String(), nullable=False),
        sa.Column("due_at", sa.String(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("delivered_at", sa.String(), nullable=True),
        sa.UniqueConstraint("connection_id", "event_key", "kind"),
    )
    op.create_index(
        "ix_companion_tasks_connection_id",
        "companion_tasks",
        ["connection_id"],
        unique=False,
    )
    op.create_table(
        "companion_event_memory",
        sa.Column("id", sa.String(length=36), primary_key=True, nullable=False),
        sa.Column(
            "connection_id",
            sa.String(length=36),
            sa.ForeignKey("calendar_connections.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "event_id",
            sa.String(length=36),
            sa.ForeignKey("calendar_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_quote", sa.Text(), nullable=False),
        sa.Column("expires_at", sa.String(), nullable=False),
    )
    # SQLite supports nullable inline REFERENCES without rebuilding the parent
    # table: rebuilding characters with FK enforcement would delete its children.
    if bind.dialect.name == "sqlite":
        op.execute(
            "ALTER TABLE characters ADD COLUMN owner_id VARCHAR(36) REFERENCES user_accounts(id)"
        )
    else:
        op.add_column(
            "characters",
            sa.Column(
                "owner_id",
                sa.String(36),
                sa.ForeignKey("user_accounts.id"),
            ),
        )
    op.create_index("ix_characters_owner_id", "characters", ["owner_id"])
    op.add_column(
        "messages",
        sa.Column(
            "source_type", sa.String(), nullable=False, server_default="user_chat"
        ),
    )
    op.add_column("messages", sa.Column("source_task_id", sa.String(36), nullable=True))
    op.add_column("messages", sa.Column("trigger_type", sa.String(30), nullable=True))
    op.add_column(
        "messages", sa.Column("source_event_id", sa.String(36), nullable=True)
    )
    op.create_index(
        "ix_messages_source_task_id", "messages", ["source_task_id"], unique=True
    )


def downgrade():
    op.drop_column("messages", "source_event_id")
    op.drop_column("messages", "trigger_type")
    op.drop_index("ix_messages_source_task_id", table_name="messages")
    op.drop_column("messages", "source_task_id")
    op.drop_column("messages", "source_type")
    op.drop_index("ix_characters_owner_id", table_name="characters")
    op.drop_column("characters", "owner_id")
    op.drop_table("companion_event_memory")
    op.drop_table("companion_tasks")
    op.drop_table("calendar_events")
    op.drop_table("companion_settings")
    op.drop_table("calendar_oauth_attempts")
    op.drop_table("calendar_connections")
    op.drop_table("login_sessions")
    op.drop_table("user_accounts")
