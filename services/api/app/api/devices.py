"""Device registration.

A device registers once to obtain an owner id and an access token. The owner is
created implicitly on first registration; this is a single-user personal
assistant, so there is no account signup flow yet.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, status

from app.api.deps import SessionDep
from app.core.tokens import generate_token, hash_token
from app.db.models import Device, Owner
from app.schemas.voice import RegisterDeviceRequest, RegisterDeviceResponse
from app.services import audit

router = APIRouter(tags=["devices"])


@router.post(
    "/devices",
    response_model=RegisterDeviceResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_device(
    payload: RegisterDeviceRequest,
    request: Request,
    session: SessionDep,
) -> RegisterDeviceResponse:
    owner = Owner()
    session.add(owner)
    await session.flush()

    token = generate_token()
    device = Device(
        owner_id=owner.id,
        token_hash=hash_token(token, request.app.state.settings.token_signing_key),
        platform=payload.platform,
        label=payload.label,
    )
    session.add(device)
    await session.flush()

    await audit.record_event(
        session,
        event="device.registered",
        owner_id=owner.id,
        device_id=device.id,
        detail=f"platform={payload.platform}",
    )
    await session.commit()

    return RegisterDeviceResponse(
        owner_id=owner.id,
        device_id=device.id,
        access_token=token,
        created_at=device.created_at,
    )
