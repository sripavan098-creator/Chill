"""Client version policy.

The app checks this on launch so a beta build can be retired when a breaking
change lands. `minimum_supported` is the oldest client version the backend will
serve; a client below it should prompt the user to update. The policy is public
(it carries no secrets), and it is intentionally separate from the API version
so the two can move independently.
"""

from __future__ import annotations

from pydantic import BaseModel


class VersionPolicyResponse(BaseModel):
    api_version: str
    # Oldest client version that is still served. Clients below this should ask
    # the user to update before continuing.
    minimum_supported: str
    # Newest client version this backend is known to work with.
    latest: str
    # Where to send a user who must update.
    update_url: str
    # Human-readable note, safe to display.
    message: str
