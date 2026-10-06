"""Single-use liveness challenges.

The client asks for a nonce, shows it to the speaker, and returns the id it was
shown alongside the recording. A nonce is bound to the owner, expires quickly
and is consumed on first use, so a recording captured before the nonce existed
cannot satisfy it. This raises the cost of replaying a captured sample without
pretending to detect a live human.

It is a freshness check, not liveness detection. A determined attacker can read
the nonce aloud over a replayed recording; spoken-phrase challenge-response and
audio deepfake checks are future work and must not be claimed until built.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ChallengeRequiredError
from app.db.models import VerificationChallenge


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """Treat a naive timestamp as UTC.

    SQLite (used in tests) hands back naive datetimes for timezone-aware
    columns, while Postgres keeps the offset. Normalising here means the expiry
    check behaves the same on both.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


@dataclass(frozen=True)
class IssuedChallenge:
    id: str
    nonce: str
    expires_at: datetime


async def issue(
    session: AsyncSession,
    *,
    owner_id: str,
    device_id: str | None,
    ttl_seconds: int,
) -> IssuedChallenge:
    now = _now()
    challenge = VerificationChallenge(
        owner_id=owner_id,
        device_id=device_id,
        nonce=secrets.token_hex(16),
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    session.add(challenge)
    await session.flush()
    return IssuedChallenge(
        id=challenge.id, nonce=challenge.nonce, expires_at=challenge.expires_at
    )


async def consume(
    session: AsyncSession, *, owner_id: str, challenge_id: str
) -> VerificationChallenge:
    """Return the matching challenge and mark it used.

    Raises `ChallengeRequiredError` if it is unknown, expired, already used, or
    belongs to a different owner. The same error is used for every case so the
    response does not reveal which condition failed.
    """
    result = await session.execute(
        select(VerificationChallenge).where(
            VerificationChallenge.id == challenge_id,
            VerificationChallenge.owner_id == owner_id,
        )
    )
    challenge = result.scalar_one_or_none()
    if challenge is None:
        raise ChallengeRequiredError(
            "Request a fresh challenge from /verification/challenge and try again."
        )
    if challenge.consumed_at is not None:
        raise ChallengeRequiredError("This challenge has already been used.")
    if _as_utc(challenge.expires_at) <= _now():
        raise ChallengeRequiredError("This challenge has expired. Request a new one.")
    challenge.consumed_at = _now()
    await session.flush()
    return challenge


async def purge_expired(session: AsyncSession, *, older_than_seconds: int) -> int:
    cutoff = _now() - timedelta(seconds=older_than_seconds)
    result = await session.execute(
        delete(VerificationChallenge).where(VerificationChallenge.created_at < cutoff)
    )
    return result.rowcount or 0
