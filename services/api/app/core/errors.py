"""Domain errors and the JSON error envelope.

Errors are returned in a stable shape so the mobile client can branch on
`code` rather than parsing prose. Messages never include biometric data.
"""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class ChillError(Exception):
    status_code = 400
    code = "BAD_REQUEST"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class ValidationError(ChillError):
    status_code = 422
    code = "VALIDATION_ERROR"


class UnauthorizedError(ChillError):
    status_code = 401
    code = "UNAUTHORIZED"


class ConsentRequiredError(ChillError):
    status_code = 403
    code = "CONSENT_REQUIRED"


class EnrollmentRequiredError(ChillError):
    status_code = 409
    code = "ENROLLMENT_REQUIRED"


class IncompleteEnrollmentError(ChillError):
    status_code = 422
    code = "INCOMPLETE_ENROLLMENT"


class RateLimitedError(ChillError):
    status_code = 429
    code = "RATE_LIMITED"


class SampleQualityError(ChillError):
    """The submitted audio was unusable (too quiet, noisy, clipped, no speech).

    Distinct from a failed verification: it is rejected before scoring and does
    not count toward the lockout.
    """

    status_code = 422
    code = "SAMPLE_QUALITY"


class LockedOutError(ChillError):
    status_code = 429
    code = "LOCKED_OUT"


class ReplayDetectedError(ChillError):
    """The submitted recording has already been used.

    Distinct from a failed verification: it is rejected before scoring and does
    not count toward the lockout.
    """

    status_code = 422
    code = "REPLAY_DETECTED"


class DeviceNotBoundError(ChillError):
    """The voice profile is bound to a different device."""

    status_code = 403
    code = "DEVICE_NOT_BOUND"


class ChallengeRequiredError(ChillError):
    """A valid, unexpired, unused challenge nonce is required."""

    status_code = 422
    code = "CHALLENGE_REQUIRED"


class ChallengePhraseError(ChillError):
    """The speaker did not say the challenge phrase.

    Distinct from a failed verification: a mis-transcribed or wrong phrase is
    reported before scoring and does not count toward the lockout, so a bad
    microphone cannot lock an owner out of their own assistant.
    """

    status_code = 422
    code = "CHALLENGE_PHRASE_MISMATCH"


class NotFoundError(ChillError):
    status_code = 404
    code = "NOT_FOUND"


class ActionNotFoundError(NotFoundError):
    """The requested action does not exist, or is not the caller's."""

    code = "ACTION_NOT_FOUND"


class ActionNotAllowedError(ChillError):
    """Actions are disabled, or this tool is not on the deployment's allowlist."""

    status_code = 403
    code = "ACTION_NOT_ALLOWED"


class ActionPendingError(ChillError):
    """The action is not in a state that allows this transition."""

    status_code = 409
    code = "ACTION_NOT_PENDING"


class ConfirmationRequiredError(ChillError):
    """A high-risk action needs an explicit step-up confirmation.

    Approval alone is not enough for the most dangerous tools: the caller must
    echo the confirmation phrase. Voice recognition is never sufficient.
    """

    status_code = 403
    code = "CONFIRMATION_REQUIRED"


class TooManyPendingActionsError(ChillError):
    """The owner has too many actions awaiting approval."""

    status_code = 429
    code = "TOO_MANY_PENDING_ACTIONS"


async def chill_error_handler(_: Request, exc: ChillError) -> JSONResponse:
    headers = {}
    if exc.status_code == 429:
        headers["Retry-After"] = "60"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=headers,
    )
