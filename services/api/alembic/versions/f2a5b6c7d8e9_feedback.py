"""feedback reports

Revision ID: f2a5b6c7d8e9
Revises: e1f4a5b6c7d8
Create Date: 2026-10-09 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "f2a5b6c7d8e9"
down_revision: str | None = "e1f4a5b6c7d8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "feedback",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(length=36),
            sa.ForeignKey("owners.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False, server_default="general"),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("app_version", sa.String(length=32), nullable=True),
        sa.Column("platform", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_feedback_owner_id", "feedback", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_feedback_owner_id", table_name="feedback")
    op.drop_table("feedback")
