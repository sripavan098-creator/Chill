"""Rate limiting and verification lockout.

Both are backed by database rows rather than process memory so limits hold
across workers and restarts. The window is fixed, which is coarse but simple
and adequate for a v0.3 API; a sliding window can replace it later without
changing the call sites.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import LockedOutError, RateLimitedError
from app.db.models import RateLimitBucket, VerificationAttempt


def _now() -> datetime:
    return datetime.now(UTC)


async def enforce_rate_limit(
    session: AsyncSession,
    *,
    scope: str,
    subject: str,
    limit: int,
    window_seconds: int,
) -> int:
    """Increment the counter for `subject` and raise if the limit is exceeded.

    Returns the number of requests remaining in the current window.
    """
    now = _now()
    window_start = now - timedelta(
        seconds=now.timestamp() % window_seconds,
    )

    result = await session.execute(
        select(RateLimitBucket).where(
            RateLimitBucket.scope == scope,
            RateLimitBucket.subject == subject,
            RateLimitBucket.window_start == window_start,
        )
    )
    bucket = result.scalar_one_or_none()

    if bucket is None:
        bucket = RateLimitBucket(
            scope=scope, subject=subject, window_start=window_start, count=0
        )
        session.add(bucket)
        try:
            await session.flush()
        except IntegrityError:
            # Another request created the bucket first; re-read it.
            await session.rollback()
            result = await session.execute(
                select(RateLimitBucket).where(
                    RateLimitBucket.scope == scope,
                    RateLimitBucket.subject == subject,
                    RateLimitBucket.window_start == window_start,
                )
            )
            bucket = result.scalar_one()

    if bucket.count >= limit:
        raise RateLimitedError("Too many requests. Please wait and try again.")

    bucket.count += 1
    await session.flush()
    return max(limit - bucket.count, 0)


async def recent_failures(
    session: AsyncSession,
    *,
    owner_id: str,
    within_seconds: int,
) -> int:
    cutoff = _now() - timedelta(seconds=within_seconds)
    result = await session.execute(
        select(VerificationAttempt).where(
            VerificationAttempt.owner_id == owner_id,
            VerificationAttempt.success.is_(False),
            VerificationAttempt.created_at >= cutoff,
        )
    )
    return len(result.scalars().all())


async def enforce_lockout(
    session: AsyncSession,
    *,
    owner_id: str,
    max_attempts: int,
    lockout_seconds: int,
) -> None:
    """Raise if the owner has too many recent failed verification attempts."""
    failures = await recent_failures(
        session, owner_id=owner_id, within_seconds=lockout_seconds
    )
    if failures >= max_attempts:
        raise LockedOutError(
            "Too many failed voice attempts. Use the PIN fallback and try again later."
        )


async def record_attempt(
    session: AsyncSession,
    *,
    owner_id: str,
    device_id: str | None,
    success: bool,
    similarity: float,
    threshold: float,
    reason: str,
    duration_ms: int = 0,
) -> VerificationAttempt:
    attempt = VerificationAttempt(
        owner_id=owner_id,
        device_id=device_id,
        success=success,
        similarity=similarity,
        threshold=threshold,
        reason=reason,
        duration_ms=duration_ms,
    )
    session.add(attempt)
    await session.flush()
    return attempt
