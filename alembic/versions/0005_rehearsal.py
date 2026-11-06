"""Private scene rehearsals and durable operations; existing content is untouched."""

import sqlalchemy as sa

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rehearsal_scenes",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=True
        ),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
        sa.Column("updated_at", sa.String(), nullable=False),
    )
    op.create_index("ix_rehearsal_scenes_owner_id", "rehearsal_scenes", ["owner_id"])
    op.create_table(
        "rehearsal_operations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "owner_id", sa.String(36), sa.ForeignKey("user_accounts.id"), nullable=True
        ),
        sa.Column("scene_id", sa.String(36), nullable=True),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("result", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.String(), nullable=False),
    )
    op.create_index(
        "ix_rehearsal_operations_scene_id", "rehearsal_operations", ["scene_id"]
    )


def downgrade():
    op.drop_index("ix_rehearsal_operations_scene_id", table_name="rehearsal_operations")
    op.drop_table("rehearsal_operations")
    op.drop_index("ix_rehearsal_scenes_owner_id", table_name="rehearsal_scenes")
    op.drop_table("rehearsal_scenes")
