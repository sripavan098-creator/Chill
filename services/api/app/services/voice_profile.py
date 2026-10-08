"""Voice-profile lifecycle helpers shared by consent, account and actions.

Removing a voice profile means removing everything derived from the owner's
voice: the enrollment and its samples, the replay fingerprints and any
outstanding verification challenges. These are grouped here so a deletion
request cannot leave one of them behind.
"""

from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    Enrollment,
    EnrollmentSample,
    SampleFingerprint,
    VerificationChallenge,
)


async def purge_enrollment(session: AsyncSession, *, owner_id: str) -> int:
    """Delete the owner's enrollment and all voice-derived rows.

    Returns the number of enrollment rows removed. Does not commit; the caller
    owns the transaction.
    """
    result = await session.execute(
        select(Enrollment.id).where(Enrollment.owner_id == owner_id)
    )
    enrollment_ids = result.scalars().all()
    if enrollment_ids:
        await session.execute(
            delete(EnrollmentSample).where(
                EnrollmentSample.enrollment_id.in_(enrollment_ids)
            )
        )
        await session.execute(
            delete(Enrollment).where(Enrollment.id.in_(enrollment_ids))
        )

    await session.execute(
        delete(SampleFingerprint).where(SampleFingerprint.owner_id == owner_id)
    )
    await session.execute(
        delete(VerificationChallenge).where(VerificationChallenge.owner_id == owner_id)
    )
    return len(enrollment_ids)
