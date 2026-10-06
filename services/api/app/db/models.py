"""SQLAlchemy models.

Design notes:

- An `Owner` is the person; `Device` is an enrolled client. Verification is
  scoped to an owner so the same person can sign in from a second device later.
- Raw audio is never represented by a model. Only encrypted embeddings are
  stored, on `EnrollmentSample` and `Enrollment`.
- `AuditLog` is append-only and intentionally free of biometric data.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    LargeBinary,
    String,
    Text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class Owner(Base):
    __tablename__ = "owners"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    display_name: Mapped[str] = mapped_column(String(120), default="Chill owner")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    devices: Mapped[list[Device]] = relationship(
        back_populates="owner", cascade="all, delete-orphan"
    )
    enrollment: Mapped[Enrollment | None] = relationship(
        back_populates="owner", cascade="all, delete-orphan", uselist=False
    )


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"), index=True
    )
    # Only the hash of the access token is stored, so a database leak does not
    # hand out working tokens.
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    platform: Mapped[str] = mapped_column(String(32), default="unknown")
    label: Mapped[str | None] = mapped_column(String(120))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    owner: Mapped[Owner] = relationship(back_populates="devices")


class ConsentRecord(Base):
    __tablename__ = "consent_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"), index=True
    )
    granted: Mapped[bool] = mapped_column(Boolean, default=False)
    policy_version: Mapped[str] = mapped_column(String(32))
    granted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Enrollment(Base):
    __tablename__ = "enrollments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"), unique=True, index=True
    )
    # Device that enrolled the voice profile. Verification from any other
    # device is refused unless device binding is turned off in settings.
    bound_device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL"), index=True
    )
    phrase_count: Mapped[int] = mapped_column(Integer, default=0)
    embedding_dimensions: Mapped[int] = mapped_column(Integer)
    # AES-256-GCM blob: nonce || ciphertext.
    embedding_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    model_version: Mapped[str] = mapped_column(String(32), default="placeholder-v0.3")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now
    )

    owner: Mapped[Owner] = relationship(back_populates="enrollment")
    samples: Mapped[list[EnrollmentSample]] = relationship(
        back_populates="enrollment", cascade="all, delete-orphan"
    )


class EnrollmentSample(Base):
    __tablename__ = "enrollment_samples"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    enrollment_id: Mapped[str] = mapped_column(
        ForeignKey("enrollments.id", ondelete="CASCADE"), index=True
    )
    phrase_id: Mapped[str] = mapped_column(String(64))
    duration_ms: Mapped[int] = mapped_column(Integer)
    quality: Mapped[float] = mapped_column(Float, default=0.0)
    embedding_encrypted: Mapped[bytes] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    enrollment: Mapped[Enrollment] = relationship(back_populates="samples")


class VerificationAttempt(Base):
    __tablename__ = "verification_attempts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL")
    )
    success: Mapped[bool] = mapped_column(Boolean)
    similarity: Mapped[float] = mapped_column(Float)
    threshold: Mapped[float] = mapped_column(Float)
    reason: Mapped[str] = mapped_column(String(200))
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str | None] = mapped_column(
        ForeignKey("owners.id", ondelete="SET NULL"), index=True
    )
    device_id: Mapped[str | None] = mapped_column(String(36))
    event: Mapped[str] = mapped_column(String(64), index=True)
    outcome: Mapped[str] = mapped_column(String(16), default="ok")
    detail: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class RateLimitBucket(Base):
    """Fixed-window counter, keyed by scope + subject."""

    __tablename__ = "rate_limit_buckets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    scope: Mapped[str] = mapped_column(String(64))
    subject: Mapped[str] = mapped_column(String(128))
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index(
            "ix_rate_limit_scope_subject_window",
            "scope",
            "subject",
            "window_start",
            unique=True,
        ),
    )


class SampleFingerprint(Base):
    """Digest of a recording the API has already seen.

    Replay protection. When a sample is accepted for scoring, its fingerprint is
    recorded; a later submission whose fingerprint matches an earlier one is
    rejected before it reaches the encoder. The digest is of the decoded audio
    and is not reversible, so no audio is retained. Rows are scoped to an owner
    and can be pruned on a schedule like the audit log.
    """

    __tablename__ = "sample_fingerprints"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"), index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_sample_fingerprint_owner_digest", "owner_id", "fingerprint"),
    )


class VerificationChallenge(Base):
    """A single-use liveness challenge.

    The client requests a nonce, shows it to the speaker and submits the same
    value back with the sample. A recording made earlier cannot satisfy a nonce
    that did not exist when it was captured, so a matching fingerprint under a
    fresh nonce is stronger evidence than a bare sample. This is a cheap
    freshness check, not full liveness detection: a determined attacker can
    still read the nonce aloud over a replayed recording. Challenge-response
    with a spoken phrase and audio deepfake checks are future work.
    """

    __tablename__ = "verification_challenges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    owner_id: Mapped[str] = mapped_column(
        ForeignKey("owners.id", ondelete="CASCADE"), index=True
    )
    device_id: Mapped[str | None] = mapped_column(
        ForeignKey("devices.id", ondelete="SET NULL")
    )
    nonce: Mapped[str] = mapped_column(String(64))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_verification_challenge_owner_nonce", "owner_id", "nonce"),
    )
