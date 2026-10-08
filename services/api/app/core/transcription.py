"""Speech-to-text providers for spoken challenge verification.

Two implementations sit behind the same interface:

- `PlaceholderTranscriber` is the deterministic stand-in used by the default
  test suite. It returns a transcript that a test attaches with
  `attach_transcript`, so the challenge pipeline can be exercised without a
  model. It is **not** a speech recogniser and must never be used in production.
- `WhisperTranscriber` is the real recogniser. It wraps a small
  faster-whisper model, which runs on CPU without a GPU.

The model is loaded lazily and cached under `CHILL_MODEL_CACHE_DIR`, and the
call runs in a worker thread because it is synchronous and CPU-bound.

Transcription is a step in spoken challenge-response, not liveness detection: a
replayed recording that contains the right words still transcribes correctly.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from typing import Protocol

from app.core.audio import TARGET_SAMPLE_RATE
from app.core.config import Settings

WHISPER_MODEL = "small"

# The placeholder carries a transcript out of band because the decoded samples
# have no speech to recognise. `attach_transcript` is used by unit tests; the
# header path lets an end-to-end smoke test drive the real ASGI app.
_active_transcript: str | None = None


@contextmanager
def attach_transcript(transcript: str | None):
    """Make `transcript` the answer `PlaceholderTranscriber` returns.

    Process-local and intended for tests only. The real transcriber ignores it.
    """
    global _active_transcript
    previous = _active_transcript
    _active_transcript = transcript
    try:
        yield
    finally:
        _active_transcript = previous


class Transcriber(Protocol):
    model_version: str

    async def transcribe(self, samples, *, sample_rate: int) -> str:
        """Return the words spoken in one decoded sample.

        `samples` is a mono float32 numpy array. An empty string means no words
        were recognised; callers treat that as a mismatch, not an error.
        """


class PlaceholderTranscriber:
    """Deterministic stand-in. Returns whatever a test attached, else ""."""

    model_version = "placeholder-stt"

    async def transcribe(self, samples, *, sample_rate: int) -> str:
        return _active_transcript or ""


class WhisperTranscriber:
    """faster-whisper small model, CPU-friendly."""

    model_version = f"whisper-{WHISPER_MODEL}-v1"

    def __init__(self, *, cache_dir: str = "./.models", device: str = "cpu") -> None:
        self._cache_dir = cache_dir
        self._device = device
        self._model = None
        self._load_lock = asyncio.Lock()

    async def _get_model(self):
        if self._model is not None:
            return self._model
        async with self._load_lock:
            if self._model is None:
                self._model = await asyncio.to_thread(self._load)
        return self._model

    def _load(self):
        from faster_whisper import WhisperModel

        return WhisperModel(
            WHISPER_MODEL, device=self._device, download_root=self._cache_dir
        )

    def _run(self, samples, model) -> str:
        import numpy as np

        audio = np.asarray(samples, dtype=np.float32)
        segments, _ = model.transcribe(
            audio,
            language="en",
            # The phrases are fixed vocabulary, so a greedy decode is enough and
            # avoids the sampling cost.
            beam_size=1,
            vad_filter=False,
        )
        return " ".join(segment.text for segment in segments).strip()

    async def transcribe(self, samples, *, sample_rate: int) -> str:
        if sample_rate != TARGET_SAMPLE_RATE:
            from app.core.audio import resample

            samples = resample(samples, sample_rate, TARGET_SAMPLE_RATE)
        model = await self._get_model()
        return await asyncio.to_thread(self._run, samples, model)


def build_transcriber(settings: Settings) -> Transcriber:
    if settings.transcription_provider == "whisper":
        return WhisperTranscriber(
            cache_dir=settings.model_cache_dir, device=settings.model_device
        )
    return PlaceholderTranscriber()
