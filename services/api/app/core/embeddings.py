"""Speaker embedding providers.

Two implementations sit behind the same interface:

- `PlaceholderEmbeddingProvider` is a deterministic stand-in. It exercises the
  whole pipeline (enrollment, encryption, storage, similarity) without a model,
  which keeps the default test suite fast. It is **not** a security boundary.
- `EcapaEmbeddingProvider` is the real speaker encoder. It wraps
  ECAPA-TDNN (SpeechBrain's `spkrec-ecapa-voxceleb`), which produces a
  192-dimensional embedding per utterance. Verification compares a sample
  against the enrolled centroid with cosine similarity.

The model is loaded lazily and its weights are cached under
`CHILL_MODEL_CACHE_DIR`, so a cold start downloads once and later starts are
offline. Encoding runs in a worker thread because the model call is
synchronous and would otherwise block the event loop.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
from typing import Protocol

from app.core.audio import TARGET_SAMPLE_RATE, resample
from app.core.config import Settings

ECAPA_MODEL_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"


class EmbeddingProvider(Protocol):
    dimensions: int
    model_version: str

    async def embed(
        self, samples, *, sample_rate: int, duration_ms: int
    ) -> list[float]:
        """Return an L2-normalised embedding for one decoded sample.

        `samples` is a mono float32 numpy array already resampled to
        `TARGET_SAMPLE_RATE` and trimmed of silence.
        """

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
    """Deterministic stand-in for a speaker encoder.

    Content-addressed: the same decoded audio always yields the same vector, so
    the pipeline can be tested without a model. Not a security boundary.
    """

    model_version = "placeholder-v0.4"

    def __init__(self, dimensions: int = 192) -> None:
        self.dimensions = dimensions

    async def embed(self, samples, *, sample_rate: int, duration_ms: int) -> list[float]:
        import numpy as np

        quantised = np.clip(np.round(np.asarray(samples) * 32767.0), -32768, 32767)
        digest = hashlib.sha256(quantised.astype("<i2").tobytes()).digest()
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


class EcapaEmbeddingProvider:
    """ECAPA-TDNN speaker encoder (SpeechBrain).

    The classifier is built on first use. `encode_batch` is CPU/GPU bound and
    blocking, so it runs in a thread to keep the request loop responsive.
    """

    model_version = "ecapa-voxceleb-v1"

    def __init__(
        self,
        *,
        cache_dir: str = "./.models",
        device: str = "cpu",
        dimensions: int = 192,
    ) -> None:
        self.dimensions = dimensions
        self._cache_dir = cache_dir
        self._device = device
        self._classifier = None
        self._load_lock = asyncio.Lock()

    async def _get_classifier(self):
        if self._classifier is not None:
            return self._classifier
        async with self._load_lock:
            if self._classifier is None:
                self._classifier = await asyncio.to_thread(self._load)
        return self._classifier

    def _load(self):
        from speechbrain.inference.speaker import EncoderClassifier

        return EncoderClassifier.from_hparams(
            source=ECAPA_MODEL_SOURCE,
            savedir=self._cache_dir,
            run_opts={"device": self._device},
        )

    def _encode(self, samples, classifier) -> list[float]:
        import numpy as np
        import torch

        with torch.no_grad():
            tensor = torch.from_numpy(np.asarray(samples, dtype=np.float32)).unsqueeze(0)
            embedding = classifier.encode_batch(tensor).squeeze().cpu().numpy()
        return _l2_normalise([float(value) for value in embedding.reshape(-1)])

    async def embed(self, samples, *, sample_rate: int, duration_ms: int) -> list[float]:
        if sample_rate != TARGET_SAMPLE_RATE:
            samples = resample(samples, sample_rate, TARGET_SAMPLE_RATE)
        classifier = await self._get_classifier()
        return await asyncio.to_thread(self._encode, samples, classifier)

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
    if settings.embedding_provider == "ecapa":
        return EcapaEmbeddingProvider(
            cache_dir=settings.model_cache_dir,
            device=settings.model_device,
            dimensions=settings.embedding_dimensions,
        )
    return PlaceholderEmbeddingProvider(dimensions=settings.embedding_dimensions)
