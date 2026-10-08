"""Text embedding providers for long-term memory.

Distinct from `app.core.embeddings`, which encodes *speech* for speaker
verification. These encode *text* for memory retrieval.

- `PlaceholderTextEmbeddingProvider` is a deterministic bag-of-words hash. It
  makes related text land close together (identical and overlapping text score
  highly), which is enough to test retrieval, ordering and user isolation
  without a model. It is not a semantic embedding and must never be used in
  production.
- `OpenAITextEmbeddingProvider` calls any OpenAI-compatible `/embeddings`
  endpoint, so it also covers a local Ollama (`nomic-embed-text`) or vLLM.

The configured `embedding_dimension` must match both the model and the width of
the `memories.embedding` column.
"""

from __future__ import annotations

import hashlib
import math
import re
from typing import Protocol

import httpx

from app.core.config import Settings

_WORD = re.compile(r"[a-z0-9]+")


def _normalise(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class TextEmbeddingProvider(Protocol):
    dimensions: int
    model_version: str

    async def embed(self, text: str) -> list[float]:
        """Return an L2-normalised embedding for one piece of text."""


class PlaceholderTextEmbeddingProvider:
    """Deterministic bag-of-words embedding for tests.

    Each token hashes to a bucket and votes with a stable sign, so two texts
    that share words have positive cosine similarity. Identical texts are
    identical vectors (cosine 1.0); unrelated texts are near 0.
    """

    model_version = "placeholder-text-v1"

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def _bucket(self, token: str) -> tuple[int, float]:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % self.dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        return index, sign

    async def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in _WORD.findall(text.lower()):
            index, sign = self._bucket(token)
            vector[index] += sign
        return _normalise(vector)


class OpenAITextEmbeddingProvider:
    """OpenAI-compatible `/embeddings` client (OpenAI, Ollama, vLLM)."""

    def __init__(
        self,
        *,
        api_base: str,
        api_key: str,
        model: str,
        dimensions: int,
        timeout: float = 30.0,
    ) -> None:
        self.dimensions = dimensions
        self.model_version = f"{model}-v1"
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._timeout = timeout

    async def embed(self, text: str) -> list[float]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._api_base}/embeddings",
                headers=headers,
                json={"model": self._model, "input": text},
            )
            response.raise_for_status()
            payload = response.json()
        vector = payload["data"][0]["embedding"]
        return _normalise([float(value) for value in vector])


def build_text_embedding_provider(settings: Settings) -> TextEmbeddingProvider:
    if settings.text_embedding_provider == "openai":
        return OpenAITextEmbeddingProvider(
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
            model=settings.text_embedding_model,
            dimensions=settings.embedding_dimension,
            timeout=settings.llm_timeout_seconds,
        )
    return PlaceholderTextEmbeddingProvider(dimensions=settings.embedding_dimension)
