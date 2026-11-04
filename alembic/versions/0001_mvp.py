"""Initial character, conversation, profile and portrait storage.

This schema is frozen here; future model changes require a new migration.
"""

import sqlalchemy as sa

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def identity():
    return sa.Column("id", sa.String(36), primary_key=True)


def owner(table="characters", name="character_id"):
    return sa.Column(
        name,
        sa.String(36),
        sa.ForeignKey(f"{table}.id", ondelete="CASCADE"),
        nullable=False,
    )


def created():
    return sa.Column("created_at", sa.String(), nullable=False)


def upgrade():
    op.create_table(
        "characters",
        identity(),
        sa.Column("original_description", sa.Text(), nullable=False),
        sa.Column("current_profile_version", sa.Integer(), nullable=False),
        sa.Column("current_image_id", sa.String(36), nullable=True),
        created(),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "character_profiles",
        identity(),
        owner(),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=False),
        created(),
        sa.UniqueConstraint("character_id", "version"),
    )
    op.create_table(
        "profile_proposals",
        identity(),
        owner(),
        sa.Column("base_version", sa.Integer(), nullable=False),
        sa.Column("profile_json", sa.JSON(), nullable=False),
        sa.Column("diff", sa.JSON(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("accepted_version", sa.Integer(), nullable=True),
        created(),
    )
    op.create_table(
        "conversations",
        identity(),
        owner(),
        created(),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_table(
        "messages",
        identity(),
        owner("conversations", "conversation_id"),
        sa.Column("request_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(12), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        created(),
        sa.UniqueConstraint("conversation_id", "request_id", "role"),
    )
    op.create_table(
        "character_images",
        identity(),
        owner(),
        sa.Column("parent_image_id", sa.String(36), nullable=True),
        sa.Column("provider", sa.String(50), nullable=False),
        sa.Column("model", sa.String(200), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(100), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        created(),
        sa.UniqueConstraint("character_id", "version"),
    )
    op.create_table("image_requests", identity(), owner(), created())
    for table in (
        "character_profiles",
        "profile_proposals",
        "conversations",
        "character_images",
        "image_requests",
        "messages",
    ):
        column = "conversation_id" if table == "messages" else "character_id"
        op.create_index(f"ix_{table}_{column}", table, [column])


def downgrade():
    for table in (
        "messages",
        "conversations",
        "profile_proposals",
        "character_profiles",
        "character_images",
        "image_requests",
        "characters",
    ):
        op.drop_table(table)
