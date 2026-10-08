"""stronger voice auth: device binding, replay digests, challenges

Revision ID: b7c1a2d4e5f6
Revises: e1796f3f7445
Create Date: 2026-10-06 15:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "b7c1a2d4e5f6"
down_revision: str | None = "e1796f3f7445"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Bind a voice profile to the device that enrolled it. Batched so SQLite
    # (used in tests) can add the foreign key too.
    with op.batch_alter_table("enrollments") as batch:
        batch.add_column(sa.Column("bound_device_id", sa.String(length=36), nullable=True))
        batch.create_foreign_key(
            "fk_enrollments_bound_device_id",
            "devices",
            ["bound_device_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_index("ix_enrollments_bound_device_id", ["bound_device_id"])

    op.create_table(
        "sample_fingerprints",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("fingerprint", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_sample_fingerprints_owner_id", "sample_fingerprints", ["owner_id"]
    )
    op.create_index(
        "ix_sample_fingerprint_owner_digest",
        "sample_fingerprints",
        ["owner_id", "fingerprint"],
    )

    op.create_table(
        "verification_challenges",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("owner_id", sa.String(length=36), nullable=False),
        sa.Column("device_id", sa.String(length=36), nullable=True),
        sa.Column("nonce", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["owner_id"], ["owners.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_verification_challenges_owner_id", "verification_challenges", ["owner_id"]
    )
    op.create_index(
        "ix_verification_challenge_owner_nonce",
        "verification_challenges",
        ["owner_id", "nonce"],
    )


def downgrade() -> None:
    op.drop_index("ix_verification_challenge_owner_nonce", table_name="verification_challenges")
    op.drop_index("ix_verification_challenges_owner_id", table_name="verification_challenges")
    op.drop_table("verification_challenges")

    op.drop_index("ix_sample_fingerprint_owner_digest", table_name="sample_fingerprints")
    op.drop_index("ix_sample_fingerprints_owner_id", table_name="sample_fingerprints")
    op.drop_table("sample_fingerprints")

    with op.batch_alter_table("enrollments") as batch:
        batch.drop_index("ix_enrollments_bound_device_id")
        batch.drop_constraint("fk_enrollments_bound_device_id", type_="foreignkey")
        batch.drop_column("bound_device_id")
