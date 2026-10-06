"""Chill voice backend.

Wires settings, database, encryption, the embedding provider and the routers
onto a FastAPI application. The ASGI app is created by `create_app` so tests can
build an isolated instance with their own database.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import account, consent, devices, enrollment, verification
from app.core.config import Settings, get_settings
from app.core.crypto import EmbeddingCipher
from app.core.embeddings import build_embedding_provider
from app.core.errors import ChillError, chill_error_handler
from app.db.models import Base
from app.db.session import create_engine, create_session_factory


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_engine(settings)
        app.state.engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.settings = settings
        app.state.cipher = EmbeddingCipher(settings.encryption_key)
        app.state.embeddings = build_embedding_provider(settings)

        # Alembic owns the schema in production. Creating tables here keeps
        # local development and tests one command shorter.
        if not settings.is_production:
            async with engine.begin() as connection:
                await connection.run_sync(Base.metadata.create_all)

        try:
            yield
        finally:
            await engine.dispose()

    app = FastAPI(
        title="Chill Voice API",
        version="0.5.0",
        description=(
            "Enrollment and verification for the Chill personal assistant. "
            "Stores encrypted embeddings only; never raw audio."
        ),
        lifespan=lifespan,
    )

    app.add_exception_handler(ChillError, chill_error_handler)

    app.include_router(devices.router, prefix="/v1")
    app.include_router(consent.router, prefix="/v1")
    app.include_router(enrollment.router, prefix="/v1")
    app.include_router(verification.router, prefix="/v1")
    app.include_router(account.router, prefix="/v1")

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok", "version": "0.5.0"}

    return app


app = create_app()
