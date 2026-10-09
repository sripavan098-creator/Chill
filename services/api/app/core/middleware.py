"""Request middleware: correlation ids, body-size limits and safe errors.

Three concerns:

- Every request gets an `X-Request-ID` (client-supplied when well-formed, else
  generated) so a report can be tied to the exact log lines.
- A request body is rejected early when it declares more than the configured
  maximum, before it is buffered into memory.
- Any unhandled exception is logged with its request id and turned into a
  generic JSON error. Stack traces and database details never reach the client.
"""

from __future__ import annotations

import logging
import re
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

from app.core.errors import ChillError
from app.core.logging import request_id_var

logger = logging.getLogger("chill.request")

# Client-supplied ids are accepted only when they look like a correlation id;
# otherwise a fresh one is generated. This keeps the header out of log
# injection reach.
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")


def _resolve_request_id(request: Request) -> str:
    supplied = request.headers.get("X-Request-ID")
    if supplied and _REQUEST_ID_RE.match(supplied):
        return supplied
    return uuid.uuid4().hex


class RequestContextMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, max_body_bytes: int) -> None:
        super().__init__(app)
        self._max_body_bytes = max_body_bytes

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = _resolve_request_id(request)
        request.state.request_id = request_id
        token = request_id_var.set(request_id)
        try:
            content_length = request.headers.get("content-length")
            if content_length is not None:
                try:
                    declared = int(content_length)
                except ValueError:
                    declared = 0
                if declared > self._max_body_bytes:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": {
                                "code": "PAYLOAD_TOO_LARGE",
                                "message": "The request body is too large.",
                            }
                        },
                        headers={"X-Request-ID": request_id},
                    )

            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            return response
        except ChillError:
            # Handled by the registered exception handler; re-raise so FastAPI
            # produces the stable error envelope.
            raise
        except Exception:
            logger.exception("unhandled error")
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "INTERNAL_ERROR",
                        "message": "Something went wrong. Please try again.",
                    }
                },
                headers={"X-Request-ID": request_id},
            )
        finally:
            request_id_var.reset(token)
