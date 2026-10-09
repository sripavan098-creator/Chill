"""Single source of truth for the API version.

Kept in one place so the OpenAPI document, `/v1/health` and the startup log
cannot drift apart.
"""

from __future__ import annotations

API_VERSION = "0.8.0"
