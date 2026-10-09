"""Chill voice backend.

Wires settings, database, encryption, the embedding provider and the routers
onto a FastAPI application. The ASGI app is created by `create_app` so tests can
build an isolated instance with their own database.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.actions.engine import ActionEngine
from app.api import (
    account,
    actions,
    assistant,
    consent,
    devices,
    enrollment,
    feedback,
    meta,
    verification,
)
from app.core.config import Settings, get_settings
from app.core.crypto import EmbeddingCipher
from app.core.embeddings import build_embedding_provider
from app.core.errors import ChillError, chill_error_handler
from app.core.llm import build_llm_provider
from app.core.logging import configure_logging, get_request_id
from app.core.middleware import RequestContextMiddleware
from app.core.speech import build_tts_provider
from app.core.text_embeddings import build_text_embedding_provider
from app.core.transcription import build_transcriber
from app.core.version import API_VERSION
from app.db.models import Base
from app.db.session import create_engine, create_session_factory

logger = logging.getLogger("chill.startup")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.settings = settings
        app.state.cipher = EmbeddingCipher(settings.encryption_key)
        app.state.embeddings = build_embedding_provider(settings)
        app.state.transcriber = build_transcriber(settings)
        app.state.llm = build_llm_provider(settings)
        app.state.text_embeddings = build_text_embedding_provider(settings)
        app.state.tts = build_tts_provider(settings)
        app.state.actions = ActionEngine(
            settings=settings,
            cipher=app.state.cipher,
            text_embeddings=app.state.text_embeddings,
        )

        # Alembic owns the schema in production. Creating tables here keeps
        # local development and tests one command shorter.
        if not settings.is_production:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

        logger.info(
            "Chill API started env=%s version=%s",
            settings.env,
            API_VERSION,
        )

        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Chill Voice API",
        version=API_VERSION,
        description=(
            "Enrollment and verification for the Chill personal assistant. "
            "Stores encrypted embeddings only; never raw audio."
        ),
        lifespan=lifespan,
    )

    app.add_exception_handler(ChillError, chill_error_handler)
    app.add_middleware(
        RequestContextMiddleware, max_body_bytes=settings.request_body_max_bytes
    )

    app.include_router(devices.router, prefix="/v1")
    app.include_router(consent.router, prefix="/v1")
    app.include_router(enrollment.router, prefix="/v1")
    app.include_router(verification.router, prefix="/v1")
    app.include_router(account.router, prefix="/v1")
    app.include_router(assistant.router, prefix="/v1")
    app.include_router(actions.router, prefix="/v1")
    app.include_router(feedback.router, prefix="/v1")
    app.include_router(meta.router, prefix="/v1")

    # Unauthenticated liveness probe. Kept at the root so infrastructure
    # does not have to know the API version.
    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {
            "status": "ok",
            "version": API_VERSION,
            "request_id": get_request_id() or "-",
        }

    return app


app = create_app()
