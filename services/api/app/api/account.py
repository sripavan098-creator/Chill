"""Account deletion.

Deleting the account is the highest-risk action in the app, so it requires an
explicit step-up confirmation. The actual purge lives in
`app.services.account_deletion` so profile deletion and account deletion remove
exactly the same set of rows.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DeviceDep, SessionDep
from app.core.errors import ValidationError
from app.schemas.voice import DeleteAccountRequest, DeleteResponse
from app.services.account_deletion import delete_owner_data

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

    await delete_owner_data(session, owner_id=device.owner_id, device_id=device.id)
    await session.commit()

    return DeleteResponse(deleted=True, detail="Account and voice data deleted.")
