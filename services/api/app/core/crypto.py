"""AES-256-GCM encryption for voice embeddings at rest.

Embeddings are the only biometric artifact the backend keeps, and they are
never returned to a client. Encryption is authenticated (GCM), so tampering is
detected on decrypt. The nonce is random per record and stored alongside the
ciphertext; the caller keeps the key out of the database.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_BYTES = 12


class EmbeddingCipher:
    def __init__(self, key_b64: str) -> None:
        self._aead = AESGCM(base64.b64decode(key_b64, validate=True))

    def encrypt(self, plaintext: bytes) -> bytes:
        nonce = os.urandom(NONCE_BYTES)
        ciphertext = self._aead.encrypt(nonce, plaintext, associated_data=None)
        return nonce + ciphertext

    def decrypt(self, blob: bytes) -> bytes:
        if len(blob) <= NONCE_BYTES:
            raise ValueError("ciphertext is too short to contain a nonce")
        nonce, ciphertext = blob[:NONCE_BYTES], blob[NONCE_BYTES:]
        return self._aead.decrypt(nonce, ciphertext, associated_data=None)
