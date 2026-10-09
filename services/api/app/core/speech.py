"""Text-to-speech providers for spoken replies.

- `PlaceholderTTS` synthesises a short, deterministic tone as a valid WAV. It
  lets the speech endpoint, streaming and the mobile playback path be exercised
  without a model. It is not speech and must never be used in production.
- `OpenAITTS` calls any OpenAI-compatible `/audio/speech` endpoint (OpenAI,
  and compatible local servers).

The audio produced here is the assistant's voice. It is synthesised from text
the owner asked to hear, contains no recording of the owner and is not stored.
"""

from __future__ import annotations

import io
import math
import struct
import wave
from typing import Protocol

import httpx

from app.core.config import Settings

TTS_SAMPLE_RATE = 16_000
PLACEHOLDER_CONTENT_TYPE = "audio/wav"


class TTSProvider(Protocol):
    model_version: str
    content_type: str

    async def synthesize(self, text: str) -> bytes:
        """Return encoded audio for `text`."""


class PlaceholderTTS:
    """Deterministic tone stand-in used by tests."""

    model_version = "placeholder-tts-v1"
    content_type = PLACEHOLDER_CONTENT_TYPE

    def __init__(self, *, seconds_per_char: float = 0.01, max_seconds: float = 1.0) -> None:
        self._seconds_per_char = seconds_per_char
        self._max_seconds = max_seconds

    def _tone(self, seconds: float) -> bytes:
        count = max(int(TTS_SAMPLE_RATE * seconds), 1)
        frames = bytearray()
        for index in range(count):
            t = index / TTS_SAMPLE_RATE
            value = 0.2 * math.sin(2 * math.pi * 220.0 * t)
            frames += struct.pack("<h", int(value * 32767))
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(TTS_SAMPLE_RATE)
            handle.writeframes(bytes(frames))
        return buffer.getvalue()

    async def synthesize(self, text: str) -> bytes:
        seconds = min(len(text) * self._seconds_per_char, self._max_seconds)
        return self._tone(seconds)


class OpenAITTS:
    """OpenAI-compatible `/audio/speech` client."""

    def __init__(
        self,
        *,
        api_base: str,
        api_key: str,
        model: str,
        voice: str,
        timeout: float = 30.0,
    ) -> None:
        self.model_version = f"{model}-v1"
        self.content_type = "audio/mpeg"
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._timeout = timeout

    async def synthesize(self, text: str) -> bytes:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(
                f"{self._api_base}/audio/speech",
                headers=headers,
                json={"model": self._model, "voice": self._voice, "input": text},
            )
            response.raise_for_status()
            content_type = response.headers.get("content-type")
            if content_type:
                self.content_type = content_type.split(";")[0].strip()
            return response.content


def build_tts_provider(settings: Settings) -> TTSProvider:
    if settings.tts_provider == "openai":
        return OpenAITTS(
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
            model=settings.tts_model,
            voice=settings.tts_voice,
            timeout=settings.llm_timeout_seconds,
        )
    return PlaceholderTTS()
