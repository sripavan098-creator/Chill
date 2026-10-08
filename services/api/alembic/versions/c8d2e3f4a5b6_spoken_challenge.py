"""spoken challenge phrase

Revision ID: c8d2e3f4a5b6
Revises: b7c1a2d4e5f6
Create Date: 2026-10-06 16:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "c8d2e3f4a5b6"
down_revision: str | None = "b7c1a2d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("verification_challenges") as batch:
        batch.add_column(sa.Column("phrase", sa.String(length=200), nullable=True))
        batch.add_column(sa.Column("heard_text", sa.String(length=400), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("verification_challenges") as batch:
        batch.drop_column("heard_text")
        batch.drop_column("phrase")
