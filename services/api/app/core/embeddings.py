"""Speaker embedding provider.

v0.3 ships the pipeline, not the model. The provider turns raw audio bytes into
a fixed-size, L2-normalised vector so enrollment, storage, encryption and
similarity scoring can all be exercised end to end. Milestone 4 replaces
`PlaceholderEmbeddingProvider` with ECAPA-TDNN / WeSpeaker behind the same
interface.

The placeholder is deterministic: the same audio yields the same vector, and
different audio yields a low-similarity vector. That makes it useful for tests
and demos, but it is **not** a security boundary and must not be relied on for
real verification.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol

from app.core.config import Settings


class EmbeddingProvider(Protocol):
    dimensions: int

    async def embed(self, audio: bytes, *, duration_ms: int) -> list[float]:
        """Return an L2-normalised embedding for a single sample."""

    async def average(self, embeddings: list[list[float]]) -> list[float]:
        """Return the centroid of several sample embeddings."""


def _l2_normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Cosine similarity of two vectors, clamped to [-1, 1]."""
    if len(a) != len(b):
        raise ValueError("vectors must have the same length")
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


class PlaceholderEmbeddingProvider:
    """Deterministic stand-in for a speaker encoder."""

    def __init__(self, dimensions: int = 192) -> None:
        self.dimensions = dimensions

    async def embed(self, audio: bytes, *, duration_ms: int) -> list[float]:
        digest = hashlib.sha256(audio).digest()
        # Expand the digest deterministically across the requested dimensions.
        values: list[float] = []
        counter = 0
        while len(values) < self.dimensions:
            block = hashlib.sha256(digest + counter.to_bytes(4, "big")).digest()
            values.extend((byte / 255.0) * 2.0 - 1.0 for byte in block)
            counter += 1
        return _l2_normalise(values[: self.dimensions])

    async def average(self, embeddings: list[list[float]]) -> list[float]:
        if not embeddings:
            raise ValueError("cannot average an empty set of embeddings")
        centroid = [0.0] * len(embeddings[0])
        for embedding in embeddings:
            if len(embedding) != len(centroid):
                raise ValueError("embeddings must share a length")
            for index, value in enumerate(embedding):
                centroid[index] += value
        return _l2_normalise([value / len(embeddings) for value in centroid])


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    return PlaceholderEmbeddingProvider(dimensions=settings.embedding_dimensions)
