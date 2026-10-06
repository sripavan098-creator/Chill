"""Append-only audit log.

Every security-relevant action records who, what and whether it succeeded.
Biometric data never enters the log. Retention is enforced by
`purge_expired`, which the deployment can run on a schedule.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import AuditLog


async def record_event(
    session: AsyncSession,
    *,
    event: str,
    outcome: str = "ok",
    owner_id: str | None = None,
    device_id: str | None = None,
    detail: str | None = None,
) -> AuditLog:
    entry = AuditLog(
        owner_id=owner_id,
        device_id=device_id,
        event=event,
        outcome=outcome,
        detail=detail,
    )
    session.add(entry)
    await session.flush()
    return entry


async def purge_expired(session: AsyncSession, *, retention_days: int) -> int:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    result = await session.execute(delete(AuditLog).where(AuditLog.created_at < cutoff))
    return result.rowcount or 0
