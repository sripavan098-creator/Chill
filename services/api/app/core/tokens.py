"""Device access tokens.

A device token is an opaque, signed string the mobile app stores in secure
storage. The database keeps only a SHA-256 hash of the token, so a leak of the
`devices` table cannot be replayed against the API.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

TOKEN_BYTES = 32


def generate_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str, signing_key: str) -> str:
    """Keyed hash so the stored value is useless without the server secret."""
    return hmac.new(signing_key.encode(), token.encode(), hashlib.sha256).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a, b)
