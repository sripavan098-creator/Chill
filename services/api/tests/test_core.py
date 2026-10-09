"""Unit tests for crypto, vectors, embeddings and rate limiting."""

from __future__ import annotations

import base64

import pytest
from cryptography.exceptions import InvalidTag

from app.core.crypto import EmbeddingCipher
from app.core.embeddings import (
    PlaceholderEmbeddingProvider,
    cosine_similarity,
)
from app.core.tokens import generate_token, hash_token, tokens_equal
from app.core.vectors import pack_vector, unpack_vector


def _wave(seed: float, count: int = 4000):
    """A small deterministic float32 signal standing in for decoded audio."""
    import math

    import numpy as np

    return np.array(
        [math.sin(2 * math.pi * (0.05 + seed * 0.01) * i) for i in range(count)],
        dtype=np.float32,
    )


def test_cipher_round_trips() -> None:
    key = base64.b64encode(b"k" * 32).decode()
    cipher = EmbeddingCipher(key)
    plaintext = b"embedding-bytes"

    blob = cipher.encrypt(plaintext)
    assert blob != plaintext
    assert cipher.decrypt(blob) == plaintext


def test_cipher_uses_a_fresh_nonce_per_call() -> None:
    key = base64.b64encode(b"k" * 32).decode()
    cipher = EmbeddingCipher(key)
    assert cipher.encrypt(b"same") != cipher.encrypt(b"same")


def test_cipher_rejects_tampered_ciphertext() -> None:
    key = base64.b64encode(b"k" * 32).decode()
    cipher = EmbeddingCipher(key)
    blob = bytearray(cipher.encrypt(b"data"))
    blob[-1] ^= 0xFF
    with pytest.raises(InvalidTag):
        cipher.decrypt(bytes(blob))


def test_vector_round_trips_within_float_precision() -> None:
    vector = [0.5, -0.25, 1.0 / 3.0]
    restored = unpack_vector(pack_vector(vector))
    assert restored == pytest.approx(vector, rel=1e-6)


def test_unpack_rejects_misaligned_blob() -> None:
    with pytest.raises(ValueError):
        unpack_vector(b"\x01\x02\x03")


def test_token_hashing_is_keyed_and_stable() -> None:
    token = generate_token()
    assert hash_token(token, "key-a") == hash_token(token, "key-a")
    assert hash_token(token, "key-a") != hash_token(token, "key-b")
    assert tokens_equal(hash_token(token, "key-a"), hash_token(token, "key-a"))
    assert len(token) > 20


async def test_embedding_is_normalised_and_deterministic() -> None:
    provider = PlaceholderEmbeddingProvider(dimensions=32)
    first = await provider.embed(_wave(1.0), sample_rate=16000, duration_ms=2000)
    second = await provider.embed(_wave(1.0), sample_rate=16000, duration_ms=2000)

    assert len(first) == 32
    assert first == second
    assert cosine_similarity(first, first) == pytest.approx(1.0, abs=1e-6)


async def test_identical_audio_scores_high_and_different_scores_low() -> None:
    provider = PlaceholderEmbeddingProvider(dimensions=64)
    a = await provider.embed(_wave(1.0), sample_rate=16000, duration_ms=2000)
    b = await provider.embed(_wave(2.0), sample_rate=16000, duration_ms=2000)

    assert cosine_similarity(a, a) > 0.99
    assert cosine_similarity(a, b) < 0.9


async def test_average_returns_unit_vector() -> None:
    provider = PlaceholderEmbeddingProvider(dimensions=16)
    vectors = [
        await provider.embed(_wave(float(i + 1)), sample_rate=16000, duration_ms=2000)
        for i in range(3)
    ]
    centroid = await provider.average(vectors)

    assert len(centroid) == 16
    assert cosine_similarity(centroid, centroid) == pytest.approx(1.0, abs=1e-6)


def test_cosine_similarity_rejects_mismatched_lengths() -> None:
    with pytest.raises(ValueError):
        cosine_similarity([1.0, 0.0], [1.0])


async def test_embedding_provider_dimensions_match_settings() -> None:
    provider = PlaceholderEmbeddingProvider(dimensions=192)
    vector = await provider.embed(_wave(3.0), sample_rate=16000, duration_ms=2000)
    assert len(vector) == 192


def test_production_rejects_dev_encryption_key(monkeypatch) -> None:
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("CHILL_ENV", "production")
    monkeypatch.setenv("CHILL_ENCRYPTION_KEY", config.DEV_ENCRYPTION_KEY)
    monkeypatch.setenv("CHILL_TOKEN_SIGNING_KEY", "a-real-signing-secret")
    try:
        with pytest.raises(RuntimeError, match="ENCRYPTION_KEY"):
            config.get_settings()
    finally:
        config.get_settings.cache_clear()


def test_production_rejects_dev_signing_key(monkeypatch) -> None:
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("CHILL_ENV", "production")
    # 32 zero bytes: valid, and distinct from the development key.
    monkeypatch.setenv("CHILL_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    monkeypatch.setenv("CHILL_TOKEN_SIGNING_KEY", config.DEV_TOKEN_SIGNING_KEY)
    try:
        with pytest.raises(RuntimeError, match="TOKEN_SIGNING_KEY"):
            config.get_settings()
    finally:
        config.get_settings.cache_clear()


def test_production_accepts_real_secrets(monkeypatch) -> None:
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("CHILL_ENV", "production")
    monkeypatch.setenv("CHILL_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    monkeypatch.setenv("CHILL_TOKEN_SIGNING_KEY", "a-real-signing-secret-that-is-32-chars")
    try:
        assert config.get_settings().is_production
    finally:
        config.get_settings.cache_clear()


def test_production_rejects_short_signing_key(monkeypatch) -> None:
    from app.core import config

    config.get_settings.cache_clear()
    monkeypatch.setenv("CHILL_ENV", "production")
    monkeypatch.setenv("CHILL_ENCRYPTION_KEY", "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=")
    monkeypatch.setenv("CHILL_TOKEN_SIGNING_KEY", "too-short")
    try:
        with pytest.raises(RuntimeError, match="at least 32"):
            config.get_settings()
    finally:
        config.get_settings.cache_clear()
