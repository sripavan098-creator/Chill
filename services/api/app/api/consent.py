"""Voice biometric consent.

Consent is recorded before enrollment and can be withdrawn at any time.
Withdrawing consent deletes the stored enrollment, so there is nothing left to
process once the user opts out.
"""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import DeviceDep, SessionDep
from app.db.models import ConsentRecord
from app.schemas.voice import ConsentRequest, ConsentResponse
from app.services import audit
from app.services.voice_profile import purge_enrollment

router = APIRouter(tags=["consent"])


async def latest_consent(session: SessionDep, owner_id: str) -> ConsentRecord | None:
    result = await session.execute(
        select(ConsentRecord)
        .where(ConsentRecord.owner_id == owner_id)
        .order_by(ConsentRecord.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


def to_response(record: ConsentRecord) -> ConsentResponse:
    return ConsentResponse(
        granted=record.granted,
        policy_version=record.policy_version,
        granted_at=record.granted_at,
        withdrawn_at=record.withdrawn_at,
    )


@router.put("/consent", response_model=ConsentResponse)
async def set_consent(
    payload: ConsentRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ConsentResponse:
    settings = request.app.state.settings
    now = datetime.now(UTC)

    record = ConsentRecord(
        owner_id=device.owner_id,
        granted=payload.granted,
        policy_version=payload.policy_version or settings.consent_policy_version,
        granted_at=now if payload.granted else None,
        withdrawn_at=None if payload.granted else now,
    )
    session.add(record)

    # Withdrawing consent removes the enrollment: the user asked us to stop
    # processing their voice, so keeping the embedding would contradict that.
    if not payload.granted:
        await purge_enrollment(session, owner_id=device.owner_id)

    await audit.record_event(
        session,
        event="consent.granted" if payload.granted else "consent.withdrawn",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"policy={record.policy_version}",
    )
    await session.commit()
    return to_response(record)


@router.get("/consent", response_model=ConsentResponse)
async def get_consent(
    session: SessionDep,
    device: DeviceDep,
) -> ConsentResponse:
    record = await latest_consent(session, device.owner_id)
    if record is None:
        return ConsentResponse(
            granted=False,
            policy_version="none",
            granted_at=None,
            withdrawn_at=None,
        )
    return to_response(record)
