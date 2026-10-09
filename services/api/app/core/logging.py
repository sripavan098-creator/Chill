"""Request-scoped context for logging.

The request id is carried in a `ContextVar` so any log line emitted while a
request is in flight can include it without threading the value through every
function call. It is set by `RequestContextMiddleware`.

Nothing here logs request bodies, audio, embeddings or tokens; those never
reach a `logger` call in the first place.
"""

from __future__ import annotations

import logging
from contextvars import ContextVar

request_id_var: ContextVar[str | None] = ContextVar("chill_request_id", default=None)


def get_request_id() -> str | None:
    return request_id_var.get()


class RequestIdFilter(logging.Filter):
    """Attach the current request id to every record, when there is one."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


def configure_logging(level: str = "INFO") -> None:
    """Install a concise log format that always carries the request id."""
    handler = logging.StreamHandler()
    handler.addFilter(RequestIdFilter())
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s [%(request_id)s] %(name)s: %(message)s")
    )
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
