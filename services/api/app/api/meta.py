"""Meta endpoints: health and client version policy.

Both are unauthenticated and carry no owner data, so the app can call them
before sign-in and a monitoring probe can hit them without a token.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.core.version import API_VERSION
from app.schemas.versions import VersionPolicyResponse

router = APIRouter(tags=["meta"])


@router.get("/version", response_model=VersionPolicyResponse)
async def version_policy(request: Request) -> VersionPolicyResponse:
    settings = request.app.state.settings
    return VersionPolicyResponse(
        api_version=API_VERSION,
        minimum_supported=settings.min_client_version,
        latest=settings.latest_client_version,
        update_url=settings.client_update_url,
        message="Chill is ready.",
    )
