"""Float-vector packing for at-rest storage.

Embeddings are stored as little-endian float32 blobs, which keeps the encrypted
payload compact and round-trips exactly for the precision a similarity score
needs.
"""

from __future__ import annotations

import struct

FLOAT_BYTES = 4


def pack_vector(vector: list[float]) -> bytes:
    return struct.pack(f"<{len(vector)}f", *vector)


def unpack_vector(blob: bytes) -> list[float]:
    if len(blob) % FLOAT_BYTES != 0:
        raise ValueError("blob length is not a multiple of 4")
    count = len(blob) // FLOAT_BYTES
    return list(struct.unpack(f"<{count}f", blob))
