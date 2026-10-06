"""FastAPI dependencies: database session and device authentication."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends, Header, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.tokens import hash_token
from app.db.models import Device, Owner


async def get_session(request: Request) -> AsyncSession:
    factory = request.app.state.session_factory
    async with factory() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]


async def get_current_device(
    request: Request,
    session: SessionDep,
    authorization: Annotated[str | None, Header()] = None,
) -> Device:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("A device access token is required.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise UnauthorizedError("A device access token is required.")

    settings = request.app.state.settings
    token_hash = hash_token(token, settings.token_signing_key)

    result = await session.execute(
        select(Device).where(Device.token_hash == token_hash)
    )
    device = result.scalar_one_or_none()

    if device is None or device.revoked_at is not None:
        raise UnauthorizedError("The device access token is not valid.")

    owner = await session.get(Owner, device.owner_id)
    if owner is None or owner.deleted_at is not None:
        raise UnauthorizedError("The device access token is not valid.")

    device.last_seen_at = datetime.now(UTC)
    return device


DeviceDep = Annotated[Device, Depends(get_current_device)]
