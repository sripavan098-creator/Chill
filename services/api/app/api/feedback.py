"""Feedback and crash-report intake.

The beta needs a way for a tester to report a problem or a privacy concern. The
report is stored so it can be triaged, but it carries only what the user typed
plus the app version and platform: no device fingerprint, no location, no
conversation content, no audio.

The endpoint is rate-limited per device so a stuck client cannot flood the
table.
"""

from __future__ import annotations

from fastapi import APIRouter, Request

from app.api.deps import DeviceDep, SessionDep
from app.core.errors import ValidationError
from app.db.models import Feedback
from app.schemas.feedback import FEEDBACK_KINDS, FeedbackRequest, FeedbackResponse
from app.services import audit, limits

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    payload: FeedbackRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> FeedbackResponse:
    settings = request.app.state.settings
    kind = payload.kind.strip().lower()
    if kind not in FEEDBACK_KINDS:
        raise ValidationError(
            f"Unknown feedback kind. Expected one of: {', '.join(FEEDBACK_KINDS)}."
        )

    await limits.enforce_rate_limit(
        session,
        scope="feedback",
        subject=device.id,
        limit=settings.feedback_hourly_limit,
        window_seconds=3600,
    )

    report = Feedback(
        owner_id=device.owner_id,
        device_id=device.id,
        kind=kind,
        message=payload.message.strip(),
        app_version=payload.app_version,
        platform=payload.platform,
    )
    session.add(report)
    await session.flush()

    await audit.record_event(
        session,
        event="feedback.received",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"kind={kind}",
    )
    await session.commit()

    return FeedbackResponse(
        id=report.id,
        kind=report.kind,
        created_at=report.created_at,
        detail="Thanks — your feedback was recorded.",
    )
