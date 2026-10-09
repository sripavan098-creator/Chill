"""Upload decoding and validation.

Audio arrives base64-encoded in JSON. Every entry point that accepts it goes
through `decode_audio_upload`, so a single place enforces the size limit and
rejects malformed payloads with a stable error code. The decoded bytes live
only for the request; nothing here writes to disk or logs the content.
"""

from __future__ import annotations

import base64
import binascii

from app.core.errors import PayloadTooLargeError, ValidationError


def decode_audio_upload(
    value: str,
    *,
    max_bytes: int,
    label: str = "sample",
) -> bytes:
    """Decode a base64 audio payload, enforcing the size limit.

    The limit is checked against the encoded length first, so an oversized
    payload is refused before it is decoded into memory.
    """
    # base64 inflates by 4/3; compare against the encoded size to avoid
    # allocating the decoded buffer for a body that is already too large.
    if len(value) > (max_bytes * 4 // 3) + 4:
        raise PayloadTooLargeError(
            f"The {label} is too large. The maximum is {max_bytes // (1024 * 1024)} MB."
        )

    try:
        audio = base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValidationError(f"The {label} is not valid base64 audio.") from exc

    if not audio:
        raise ValidationError(f"The {label} is empty.")
    if len(audio) > max_bytes:
        raise PayloadTooLargeError(
            f"The {label} is too large. The maximum is {max_bytes // (1024 * 1024)} MB."
        )
    return audio
