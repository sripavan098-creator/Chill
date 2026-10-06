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


class NotFoundError(ChillError):
    status_code = 404
    code = "NOT_FOUND"


async def chill_error_handler(_: Request, exc: ChillError) -> JSONResponse:
    headers = {}
    if exc.status_code == 429:
        headers["Retry-After"] = "60"
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=headers,
    )
