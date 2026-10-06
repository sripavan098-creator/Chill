"""Account deletion.

Deleting the account is the highest-risk action in the app, so it requires an
explicit step-up confirmation. It removes the owner, their devices, consent
records, enrollment and embeddings in one transaction.
"""

from __future__ import annotations

from fastapi import APIRouter
from sqlalchemy import delete

from app.api.deps import DeviceDep, SessionDep
from app.core.errors import ValidationError
from app.db.models import (
    ConsentRecord,
    Device,
    Enrollment,
    EnrollmentSample,
    Owner,
    VerificationAttempt,
)
from app.schemas.voice import DeleteAccountRequest, DeleteResponse
from app.services import audit

router = APIRouter(tags=["account"])

DELETE_CONFIRMATION = "DELETE"


@router.delete("/account", response_model=DeleteResponse)
async def delete_account(
    payload: DeleteAccountRequest,
    session: SessionDep,
    device: DeviceDep,
) -> DeleteResponse:
    if payload.confirm != DELETE_CONFIRMATION:
        raise ValidationError("Deleting the account requires confirmation.")

    owner_id = device.owner_id

    enrollment_ids = (
        await session.execute(
            Enrollment.__table__.select().with_only_columns(Enrollment.id).where(
                Enrollment.owner_id == owner_id
            )
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

    # Keep the audit trail but detach it from the deleted owner.
    await audit.record_event(
        session,
        event="account.deleted",
        outcome="ok",
        owner_id=None,
        device_id=device.id,
    )

    await session.execute(delete(Device).where(Device.owner_id == owner_id))
    await session.execute(delete(Owner).where(Owner.id == owner_id))
    await session.commit()

    return DeleteResponse(deleted=True, detail="Account and voice data deleted.")
