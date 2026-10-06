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
from app.core.audio import AudioDecodeError, prepare
from app.core.embeddings import cosine_similarity
from app.core.errors import (
    EnrollmentRequiredError,
    LockedOutError,
    SampleQualityError,
    ValidationError,
)
from app.core.vectors import unpack_vector
from app.db.models import Enrollment
from app.schemas.voice import VerificationResponse, VerifyRequest
from app.services import audit, limits

router = APIRouter(tags=["verification"])


def _confidence(similarity: float) -> float:
    """Map a cosine similarity onto a 0-1 confidence value.

    ECAPA similarities for the same speaker cluster well above zero and for
    different speakers well below, so the raw score is shifted into a readable
    range rather than reported as-is.
    """
    return max(0.0, min(1.0, (similarity + 1.0) / 2.0))


def _band(similarity: float, settings) -> str:
    if similarity >= settings.high_confidence_threshold:
        return "high"
    if similarity >= settings.medium_confidence_threshold:
        return "medium"
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

    try:
        decoded = prepare(audio)
    except AudioDecodeError as exc:
        raise ValidationError("The sample is not decodable audio.") from exc
    finally:
        del audio

    issues = decoded.quality.problems(
        min_speech_ms=settings.min_speech_ms,
        min_snr_db=settings.min_snr_db,
        max_clipping=settings.max_clipping_ratio,
    )
    if issues:
        # A bad sample is not a failed authentication attempt: it is rejected
        # before scoring, so it does not count toward the lockout.
        await audit.record_event(
            session,
            event="verification.rejected",
            outcome="denied",
            owner_id=device.owner_id,
            device_id=device.id,
            detail=f"quality={','.join(issues)}",
        )
        await session.commit()
        raise SampleQualityError(
            f"The recording was rejected ({', '.join(issues)}). "
            "Record again in a quiet room and speak clearly."
        )

    sample_embedding = await provider.embed(
        decoded.samples,
        sample_rate=decoded.sample_rate,
        duration_ms=decoded.quality.duration_ms,
    )
    sample_duration_ms = decoded.quality.duration_ms
    del decoded

    owner_embedding = unpack_vector(cipher.decrypt(enrollment.embedding_encrypted))
    similarity = cosine_similarity(sample_embedding, owner_embedding)
    passed = similarity >= settings.verification_threshold
    band = _band(similarity, settings)

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
        reason=band,
        duration_ms=sample_duration_ms,
    )
    await audit.record_event(
        session,
        event="verification.attempt",
        outcome="ok" if passed else "denied",
        owner_id=device.owner_id,
        device_id=device.id,
        detail=f"band={band} model={provider.model_version}",
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
        reason=band,
        attempts_remaining=attempts_remaining,
        locked_out=locked_out,
        model_version=provider.model_version,
    )
