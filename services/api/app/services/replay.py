"""Replay protection.

A recording that has already been scored is refused if it is submitted again.
The check is a digest of the decoded audio, so re-encoding the same take does
not produce a fresh fingerprint. Only the digest is stored, never the audio.

The comparison is deliberately exact: it catches the obvious replay of a
previously accepted file, which is what a client-side capture can realistically
attempt. It does not defeat a re-recording of a playback (that is what the
liveness challenge and, later, deepfake detection are for).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import SampleFingerprint


def _now() -> datetime:
    return datetime.now(UTC)


async def is_replayed(
    session: AsyncSession, *, owner_id: str, fingerprint: str
) -> bool:
    result = await session.execute(
        select(SampleFingerprint.id).where(
            SampleFingerprint.owner_id == owner_id,
            SampleFingerprint.fingerprint == fingerprint,
        )
    )
    return result.first() is not None


async def remember(
    session: AsyncSession, *, owner_id: str, fingerprint: str
) -> SampleFingerprint:
    """Record a digest so the same recording cannot be used again."""
    row = SampleFingerprint(owner_id=owner_id, fingerprint=fingerprint)
    session.add(row)
    await session.flush()
    return row


async def purge_expired(session: AsyncSession, *, window_seconds: int) -> int:
    """Drop digests older than the replay window.

    The window is the longest a recording could stay useful to an attacker; past
    it, remembering every digest would grow without bound for no benefit.
    """
    cutoff = _now() - timedelta(seconds=window_seconds)
    result = await session.execute(
        delete(SampleFingerprint).where(SampleFingerprint.created_at < cutoff)
    )
    return result.rowcount or 0
