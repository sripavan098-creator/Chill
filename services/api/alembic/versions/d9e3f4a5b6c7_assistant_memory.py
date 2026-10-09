"""assistant chat and long-term memory

Revision ID: d9e3f4a5b6c7
Revises: c8d2e3f4a5b6
Create Date: 2026-10-06 18:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "d9e3f4a5b6c7"
down_revision: str | None = "c8d2e3f4a5b6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "chat_messages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(length=36),
            sa.ForeignKey("owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", sa.String(length=16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_chat_message_owner_created",
        "chat_messages",
        ["owner_id", "created_at"],
    )
    op.create_index(
        "ix_chat_messages_owner_id", "chat_messages", ["owner_id"]
    )

    op.create_table(
        "memories",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "owner_id",
            sa.String(length=36),
            sa.ForeignKey("owners.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("embedding_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("embedding_dimensions", sa.Integer(), nullable=False),
        sa.Column(
            "model_version", sa.String(length=64), nullable=False,
            server_default="placeholder-text-v1",
        ),
        sa.Column(
            "source", sa.String(length=32), nullable=False, server_default="manual"
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_memory_owner_created", "memories", ["owner_id", "created_at"])
    op.create_index("ix_memories_owner_id", "memories", ["owner_id"])


def downgrade() -> None:
    op.drop_index("ix_memories_owner_id", table_name="memories")
    op.drop_index("ix_memory_owner_created", table_name="memories")
    op.drop_table("memories")
    op.drop_index("ix_chat_messages_owner_id", table_name="chat_messages")
    op.drop_index("ix_chat_message_owner_created", table_name="chat_messages")
    op.drop_table("chat_messages")
