"""Owner data deletion.

Deleting an account removes everything the owner owns: devices, consent
records, enrollment and voice-derived data, chat, memories, actions and
feedback. The audit trail is kept but detached from the deleted owner, so a
deletion is still recorded without retaining the identity.

`delete_owner_data` is the single implementation; every deletion endpoint calls
it, so a new table is added to the purge in exactly one place.
"""

from __future__ import annotations

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    ActionRequest,
    ChatMessage,
    ConsentRecord,
    Device,
    Enrollment,
    EnrollmentSample,
    Feedback,
    Memory,
    Owner,
    SampleFingerprint,
    VerificationAttempt,
    VerificationChallenge,
)
from app.services import audit


async def delete_owner_data(
    session: AsyncSession,
    *,
    owner_id: str,
    device_id: str | None = None,
) -> None:
    """Delete the owner and every row that belongs to them.

    The caller is responsible for committing. Only the audit entry survives,
    detached from the owner id.
    """
    enrollment_ids = (
        await session.execute(
            Enrollment.__table__.select()
            .with_only_columns(Enrollment.id)
            .where(Enrollment.owner_id == owner_id)
        )
    ).scalars().all()

    if enrollment_ids:
        await session.execute(
            delete(EnrollmentSample).where(
                EnrollmentSample.enrollment_id.in_(enrollment_ids)
            )
        )
        await session.execute(delete(Enrollment).where(Enrollment.id.in_(enrollment_ids)))

    await session.execute(delete(ConsentRecord).where(ConsentRecord.owner_id == owner_id))
    await session.execute(
        delete(VerificationAttempt).where(VerificationAttempt.owner_id == owner_id)
    )
    await session.execute(
        delete(SampleFingerprint).where(SampleFingerprint.owner_id == owner_id)
    )
    await session.execute(
        delete(VerificationChallenge).where(VerificationChallenge.owner_id == owner_id)
    )

    # Assistant data: the conversation and the memories the owner asked Chill to
    # keep are personal data too, so they go with the account.
    await session.execute(delete(ChatMessage).where(ChatMessage.owner_id == owner_id))
    await session.execute(delete(Memory).where(Memory.owner_id == owner_id))
    await session.execute(
        delete(ActionRequest).where(ActionRequest.owner_id == owner_id)
    )
    await session.execute(delete(Feedback).where(Feedback.owner_id == owner_id))

    # Keep the audit trail but detach it from the deleted owner.
    await audit.record_event(
        session,
        event="account.deleted",
        outcome="ok",
        owner_id=None,
        device_id=device_id,
    )

    await session.execute(delete(Device).where(Device.owner_id == owner_id))
    await session.execute(delete(Owner).where(Owner.id == owner_id))
