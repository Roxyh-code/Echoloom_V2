"""Creator stories, idempotent requests, and non-destructive character archive."""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "characters",
        sa.Column("archived", sa.Boolean(), nullable=False, server_default="0"),
    )
    op.create_table(
        "creator_works",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=True
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ix_creator_works_owner_id", "creator_works", ["owner_id"])
    op.create_table(
        "creator_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=True
        ),
        sa.Column("scope", sa.String(80), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.String(), nullable=False),
    )


def downgrade():
    op.drop_table("creator_requests")
    op.drop_index("ix_creator_works_owner_id", table_name="creator_works")
    op.drop_table("creator_works")
    op.drop_column("characters", "archived")
