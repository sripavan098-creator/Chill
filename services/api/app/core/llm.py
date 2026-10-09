"""LLM providers for the assistant chat endpoint.

- `PlaceholderLLM` is a deterministic, offline stand-in. It streams a short
  templated reply that echoes the prompt, which lets the streaming endpoint,
  history and memory wiring be tested without a model. It is not an assistant
  and must never be used in production.
- `OpenAICompatibleLLM` streams from any OpenAI-compatible
  `/chat/completions` endpoint, so it covers OpenAI, a local Ollama
  (`LLM_API_BASE=http://host:11434/v1`, model `llama3`) and vLLM.

The system prompt (identity + prompt-injection guardrail) is assembled by
`app.assistant.prompts`, not here; this module only moves tokens.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Protocol

import httpx

from app.core.config import Settings


class LLMProvider(Protocol):
    model_version: str

    def stream(
        self, *, system_prompt: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        """Yield response text chunks for the given conversation."""


class PlaceholderLLM:
    """Deterministic offline stand-in used by tests."""

    model_version = "placeholder-llm-v1"

    def __init__(self, *, chunk_size: int = 8, delay: float = 0.0) -> None:
        self._chunk_size = chunk_size
        self._delay = delay

    def _compose(self, system_prompt: str, messages: list[dict[str, str]]) -> str:
        last_user = next(
            (m["content"] for m in reversed(messages) if m["role"] == "user"), ""
        )
        return f"I heard you say: {last_user}"

    async def stream(
        self, *, system_prompt: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        text = self._compose(system_prompt, messages)
        for start in range(0, len(text), self._chunk_size):
            if self._delay:
                await asyncio.sleep(self._delay)
            yield text[start : start + self._chunk_size]


class OpenAICompatibleLLM:
    """Streaming client for an OpenAI-compatible /chat/completions endpoint."""

    def __init__(
        self,
        *,
        api_base: str,
        api_key: str,
        model: str,
        max_tokens: int = 512,
        timeout: float = 30.0,
    ) -> None:
        self.model_version = f"{model}-v1"
        self._api_base = api_base.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._max_tokens = max_tokens
        self._timeout = timeout

    async def stream(
        self, *, system_prompt: str, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        payload = {
            "model": self._model,
            "messages": [{"role": "system", "content": system_prompt}, *messages],
            "max_tokens": self._max_tokens,
            "stream": True,
        }
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            async with client.stream(
                "POST", f"{self._api_base}/chat/completions", headers=headers, json=payload
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    chunk = _parse_sse_line(line)
                    if chunk:
                        yield chunk

def _parse_sse_line(line: str) -> str:
    if not line.startswith("data:"):
        return ""
    data = line[5:].strip()
    if not data:
        return ""
    try:
        return json.loads(data)["choices"][0]["delta"].get("content", "")
    except (json.JSONDecodeError, KeyError, IndexError, TypeError):
        return ""


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.llm_provider == "openai":
        return OpenAICompatibleLLM(
            api_base=settings.llm_api_base,
            api_key=settings.llm_api_key,
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            timeout=settings.llm_timeout_seconds,
        )
    return PlaceholderLLM()
