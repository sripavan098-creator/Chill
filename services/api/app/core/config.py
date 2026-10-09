"""Application settings.

Secrets are supplied through the environment. Nothing sensitive has a usable
default: the service refuses to start if the encryption key is missing or
malformed, so a misconfigured deployment fails loudly instead of storing
embeddings in the clear.
"""

from __future__ import annotations

import base64
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Fallback values are for local development and tests only. They are fixed and
# public, so `CHILL_ENV=production` rejects both of them.
DEV_ENCRYPTION_KEY = base64.b64encode(b"chill-dev-only-key-32-bytes-lon!").decode()
DEV_TOKEN_SIGNING_KEY = "dev-signing-key-change-me"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CHILL_", env_file=".env", extra="ignore")

    env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./chill.db"

    # Base64-encoded 32-byte AES-256 key.
    encryption_key: str = DEV_ENCRYPTION_KEY

    # Shared secret used to sign device access tokens (HMAC-SHA256).
    token_signing_key: str = DEV_TOKEN_SIGNING_KEY

    # Rate limits and lockout.
    enrollment_rate_limit: int = 10
    verification_rate_limit: int = 10
    rate_limit_window_seconds: int = 60
    max_verification_attempts: int = 3
    lockout_seconds: int = 300

    # Recording constraints (mirrors the mobile app validation).
    min_sample_ms: int = 1500
    max_sample_ms: int = 15000
    required_phrases: int = 5
    embedding_dimensions: int = 192

    # Speaker encoder. "placeholder" is the deterministic stand-in used by the
    # default test suite; "ecapa" is the real ECAPA-TDNN model.
    embedding_provider: str = "placeholder"
    # Directory the encoder caches its downloaded weights in.
    model_cache_dir: str = "./.models"
    # Torch device for the encoder.
    model_device: str = "cpu"

    # Verification thresholds. ECAPA cosine similarity is high for the same
    # speaker and much lower across speakers. Measured on clean samples the
    # same-speaker range is ~0.84-0.92 and different-speaker ~0.12-0.18, so
    # 0.55 sits in the gap with margin. Re-tune against real field recordings
    # before relying on it in production; voice remains one layer, not the
    # boundary, for high-risk actions.
    verification_threshold: float = 0.55
    high_confidence_threshold: float = 0.75
    medium_confidence_threshold: float = 0.65

    # Sample quality gates, enforced after decoding and voice activity
    # detection.
    min_speech_ms: int = 1200
    min_snr_db: float = 8.0
    max_clipping_ratio: float = 0.05

    # Stronger voice auth (v0.5).
    #
    # Bind the voice profile to the device that enrolled it. Verification from
    # any other device is refused, so a stolen token alone cannot be used from
    # an attacker's phone. Turn off to allow the same owner to verify from a
    # second device.
    enforce_device_binding: bool = True
    # Require a single-use, time-boxed nonce with each verification. The client
    # obtains one from /verification/challenge and returns the id it was shown.
    # A recording captured before the nonce existed cannot satisfy it, which
    # makes a captured sample harder to replay.
    require_verification_challenge: bool = True
    challenge_ttl_seconds: int = 120
    # How long a used recording is remembered so it cannot be replayed.
    replay_window_seconds: int = 600
    # How often (at most) the same device may ask for a challenge.
    challenge_rate_limit: int = 30
    # Ask the speaker to say a specific phrase, then check what they said with
    # speech-to-text. This is a freshness check that a blind replay cannot
    # satisfy: the phrase did not exist when any earlier recording was made. It
    # is not liveness detection.
    require_spoken_challenge: bool = True
    # Speech-to-text provider. "placeholder" returns a transcript attached by a
    # test; "whisper" runs a small faster-whisper model and needs the `speaker`
    # extra (or faster-whisper) installed.
    transcription_provider: str = "placeholder"

    @field_validator("transcription_provider")
    @classmethod
    def _validate_transcriber(cls, value: str) -> str:
        allowed = {"placeholder", "whisper"}
        if value.lower() not in allowed:
            raise ValueError(
                f"CHILL_TRANSCRIPTION_PROVIDER must be one of {sorted(allowed)}"
            )
        return value.lower()

    consent_policy_version: str = "2026-10-01"

    audit_log_retention_days: int = Field(default=90, ge=1)

    # Assistant: LLM chat and long-term memory (v0.6).
    #
    # "placeholder" is the deterministic stand-in the default test suite uses;
    # "openai" talks to any OpenAI-compatible endpoint, which covers OpenAI
    # itself, a local Ollama (`LLM_API_BASE=http://host:11434/v1`) and vLLM.
    llm_provider: str = "placeholder"
    llm_api_base: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: float = 30.0
    llm_max_tokens: int = 512

    # Text embeddings for memory retrieval. `embedding_dimension` must match the
    # model and the width of the `memories.embedding` column: 1536 for OpenAI's
    # text-embedding-3-small, 768 for nomic-embed-text, 384 for MiniLM.
    text_embedding_provider: str = "placeholder"
    text_embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536

    # Text-to-speech for spoken replies. "placeholder" synthesises a short
    # deterministic tone for tests; "openai" calls any OpenAI-compatible
    # `/audio/speech` endpoint. The assistant's voice carries no biometric data.
    tts_provider: str = "placeholder"
    tts_model: str = "tts-1"
    tts_voice: str = "alloy"

    # Chat behaviour.
    chat_history_limit: int = 10
    memory_top_k: int = 3
    chat_rate_limit: int = 30
    chat_message_max_chars: int = 4000
    # Cap on memories loaded for a Python-side search on non-Postgres backends.
    memory_scan_limit: int = 500

    # Action Engine (v0.7).
    #
    # Low-risk actions run immediately. Medium- and high-risk actions are
    # queued as pending approvals and only run when the owner approves them with
    # an explicit confirmation. Voice recognition is never sufficient on its
    # own for a high-risk action.
    actions_enabled: bool = True
    action_rate_limit: int = 30
    # How long a pending approval stays open before it expires.
    action_approval_ttl_seconds: int = 900
    # Cap on outstanding pending approvals per owner, so a caller cannot queue
    # unbounded work.
    action_max_pending: int = 20
    # Comma-separated action names a deployment allows. Empty means the
    # built-in set. Narrowing this is how a deployment shrinks the surface.
    action_allowlist: str = ""

    @property
    def allowed_action_names(self) -> set[str] | None:
        names = {name.strip() for name in self.action_allowlist.split(",") if name.strip()}
        return names or None

    @field_validator("llm_provider", "text_embedding_provider", "tts_provider")
    @classmethod
    def _validate_assistant_provider(cls, value: str) -> str:
        allowed = {"placeholder", "openai"}
        if value.lower() not in allowed:
            raise ValueError(f"assistant provider must be one of {sorted(allowed)}")
        return value.lower()

    @field_validator("embedding_dimension")
    @classmethod
    def _validate_embedding_dimension(cls, value: int) -> int:
        if value < 1 or value > 8192:
            raise ValueError("CHILL_EMBEDDING_DIMENSION must be between 1 and 8192")
        return value

    @field_validator("embedding_provider")
    @classmethod
    def _validate_provider(cls, value: str) -> str:
        allowed = {"placeholder", "ecapa"}
        if value.lower() not in allowed:
            raise ValueError(
                f"CHILL_EMBEDDING_PROVIDER must be one of {sorted(allowed)}"
            )
        return value.lower()

    @field_validator("encryption_key")
    @classmethod
    def _validate_key(cls, value: str) -> str:
        try:
            raw = base64.b64decode(value, validate=True)
        except Exception as exc:  # noqa: BLE001 - re-raised as a clear config error
            raise ValueError("CHILL_ENCRYPTION_KEY must be base64-encoded") from exc
        if len(raw) != 32:
            raise ValueError("CHILL_ENCRYPTION_KEY must decode to exactly 32 bytes")
        return value

    @property
    def is_production(self) -> bool:
        return self.env.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.is_production:
        if settings.encryption_key == DEV_ENCRYPTION_KEY:
            raise RuntimeError(
                "CHILL_ENCRYPTION_KEY must be set to a real secret in production."
            )
        if settings.token_signing_key == DEV_TOKEN_SIGNING_KEY:
            raise RuntimeError(
                "CHILL_TOKEN_SIGNING_KEY must be set to a real secret in production."
            )
        needs_llm_key = settings.llm_provider == "openai" or any(
            provider == "openai"
            for provider in (settings.text_embedding_provider, settings.tts_provider)
        )
        if needs_llm_key and not settings.llm_api_key:
            raise RuntimeError(
                "CHILL_LLM_API_KEY must be set when an OpenAI-compatible "
                "provider (llm, text embedding or tts) is selected. For a "
                "local model set it to any placeholder value."
            )
    return settings
