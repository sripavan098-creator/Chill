"""action engine requests

Revision ID: e1f4a5b6c7d8
Revises: d9e3f4a5b6c7
Create Date: 2026-10-06 19:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "e1f4a5b6c7d8"
down_revision: str | None = "d9e3f4a5b6c7"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "action_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(length=36),
            sa.ForeignKey("owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("tool_name", sa.String(length=64), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
        sa.Column(
            "status", sa.String(length=16), nullable=False, server_default="pending"
        ),
        sa.Column("summary", sa.String(length=400), nullable=False),
        sa.Column("arguments", sa.Text(), nullable=False),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("error", sa.String(length=400), nullable=True),
        sa.Column("confirmation", sa.String(length=32), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_action_requests_owner_id", "action_requests", ["owner_id"])
    op.create_index("ix_action_requests_tool_name", "action_requests", ["tool_name"])
    op.create_index("ix_action_requests_risk_level", "action_requests", ["risk_level"])
    op.create_index("ix_action_requests_status", "action_requests", ["status"])
    op.create_index(
        "ix_action_owner_status", "action_requests", ["owner_id", "status"]
    )


def downgrade() -> None:
    op.drop_index("ix_action_owner_status", table_name="action_requests")
    op.drop_index("ix_action_requests_status", table_name="action_requests")
    op.drop_index("ix_action_requests_risk_level", table_name="action_requests")
    op.drop_index("ix_action_requests_tool_name", table_name="action_requests")
    op.drop_index("ix_action_requests_owner_id", table_name="action_requests")
    op.drop_table("action_requests")
