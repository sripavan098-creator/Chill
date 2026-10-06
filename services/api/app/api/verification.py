"""Voice verification.

The flow is: rate-limit the device, refuse if the owner is locked out, embed the
submitted sample, compare it to the stored owner embedding, and record the
attempt. The similarity score and threshold are returned so the client can show
an honest confidence level; the embedding itself never leaves the server.

This endpoint answers "does this sound like the enrolled owner". It is a
convenience layer. High-risk actions still require the PIN/OS fallback.
"""

from __future__ import annotations

import base64
import binascii

from fastapi import APIRouter, Request
from sqlalchemy import select

from app.api.deps import DeviceDep, SessionDep
from app.core.embeddings import cosine_similarity
from app.core.errors import (
    EnrollmentRequiredError,
    LockedOutError,
    ValidationError,
)
from app.core.vectors import unpack_vector
from app.db.models import Enrollment
from app.schemas.voice import VerificationResponse, VerifyRequest
from app.services import audit, limits

router = APIRouter(tags=["verification"])

CONFIDENCE_BANDS = (
    (0.9, "high"),
    (0.8, "medium"),
    (0.0, "low"),
)


def _confidence(similarity: float) -> float:
    """Map a similarity score onto a 0-1 confidence value."""
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def _band(similarity: float) -> str:
    for threshold, label in CONFIDENCE_BANDS:
        if similarity >= threshold:
            return label
    return "low"


@router.post("/verification", response_model=VerificationResponse)
async def verify(
    payload: VerifyRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> VerificationResponse:
    settings = request.app.state.settings
    cipher = request.app.state.cipher
    provider = request.app.state.embeddings

    await limits.enforce_rate_limit(
        session,
        scope="verification",
        subject=device.id,
        limit=settings.verification_rate_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )

    result = await session.execute(
        select(Enrollment).where(Enrollment.owner_id == device.owner_id)
    )
    enrollment = result.scalar_one_or_none()
    if enrollment is None:
        await audit.record_event(
            session,
            event="verification.rejected",
            outcome="denied",
            owner_id=device.owner_id,
            device_id=device.id,
            detail="no_enrollment",
        )
        await session.commit()
        raise EnrollmentRequiredError("No voice profile is enrolled.")

    try:
        await limits.enforce_lockout(
            session,
            owner_id=device.owner_id,
            max_attempts=settings.max_verification_attempts,
            lockout_seconds=settings.lockout_seconds,
        )
    except LockedOutError:
        await audit.record_event(
            session,
            event="verification.locked_out",
            outcome="denied",
            owner_id=device.owner_id,
            device_id=device.id,
        )
        await session.commit()
        raise

    if payload.duration_ms < settings.min_sample_ms:
        raise ValidationError(
            f"Hold the phrase for at least {settings.min_sample_ms}ms."
        )

    try:
        audio = base64.b64decode(payload.audio_base64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError("The sample is not valid base64 audio.") from exc
    if not audio:
        raise ValidationError("The sample is empty.")

    sample_embedding = await provider.embed(audio, duration_ms=payload.duration_ms)
    del audio

    owner_embedding = unpack_vector(cipher.decrypt(enrollment.embedding_encrypted))
    similarity = cosine_similarity(sample_embedding, owner_embedding)
    passed = similarity >= settings.verification_threshold

    failures = await limits.recent_failures(
        session, owner_id=device.owner_id, within_seconds=settings.lockout_seconds
    )
    await limits.record_attempt(
        session,
        owner_id=device.owner_id,
        device_id=device.id,
        success=passed,
        similarity=similarity,
        threshold=settings.verification_threshold,
        reason=_band(similarity),
        duration_ms=payload.duration_ms,
    )
    await audit.record_event(
        session,
        event="verification.attempt",
        outcome="ok" if passed else "denied",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"similarity={similarity:.3f} band={_band(similarity)}",
    )

    # Failures counted before this one, plus this one if it failed.
    failure_count = failures + (0 if passed else 1)
    attempts_remaining = max(settings.max_verification_attempts - failure_count, 0)
    locked_out = failure_count >= settings.max_verification_attempts

    await session.commit()

    return VerificationResponse(
        outcome="success" if passed else "failure",
        similarity=round(similarity, 4),
        confidence=round(_confidence(similarity), 4),
        threshold=settings.verification_threshold,
        reason=_band(similarity),
        attempts_remaining=attempts_remaining,
        locked_out=locked_out,
    )
