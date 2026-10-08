"""Long-term personal memory.

A memory is a short fact the owner asked Chill to remember. Each is stored with
an encrypted text embedding; retrieval embeds the query and ranks memories by
cosine similarity in the request scope.

Ranking is done in Python rather than in SQL. That keeps the same code path on
SQLite (tests, local dev) and Postgres, and it keeps the plaintext vectors out
of the database and out of the query log. The trade-off is that a very large
memory set is read into memory per query; `memory_scan_limit` caps that, and a
Postgres deployment can move ranking to pgvector later without changing the
callers.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.crypto import EmbeddingCipher
from app.core.embeddings import cosine_similarity
from app.core.text_embeddings import TextEmbeddingProvider
from app.core.vectors import pack_vector, unpack_vector
from app.db.models import Memory


async def add_memory(
    session: AsyncSession,
    *,
    owner_id: str,
    content: str,
    provider: TextEmbeddingProvider,
    cipher: EmbeddingCipher,
    source: str = "manual",
) -> Memory:
    """Embed and store one memory, returning the persisted row."""
    vector = await provider.embed(content)
    memory = Memory(
        owner_id=owner_id,
        content=content,
        embedding_encrypted=cipher.encrypt(pack_vector(vector)),
        embedding_dimensions=provider.dimensions,
        model_version=provider.model_version,
        source=source,
    )
    session.add(memory)
    await session.flush()
    return memory


async def list_memories(
    session: AsyncSession, *, owner_id: str, limit: int = 100
) -> list[Memory]:
    result = await session.execute(
        select(Memory)
        .where(Memory.owner_id == owner_id, Memory.deleted_at.is_(None))
        .order_by(Memory.created_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


async def delete_memory(
    session: AsyncSession, *, owner_id: str, memory_id: str
) -> bool:
    """Soft-delete a memory. Returns False when it is not the owner's."""
    memory = await session.get(Memory, memory_id)
    if memory is None or memory.owner_id != owner_id or memory.deleted_at is not None:
        return False
    memory.deleted_at = datetime.now(UTC)
    await session.flush()
    return True


async def purge_memories(session: AsyncSession, *, owner_id: str) -> None:
    """Hard-delete every memory for an owner (used on account deletion)."""
    await session.execute(delete(Memory).where(Memory.owner_id == owner_id))


async def search_memories(
    session: AsyncSession,
    *,
    owner_id: str,
    query: str,
    provider: TextEmbeddingProvider,
    cipher: EmbeddingCipher,
    top_k: int,
    scan_limit: int,
) -> list[tuple[Memory, float]]:
    """Return up to `top_k` memories ranked by cosine similarity to `query`.

    Only memories whose stored width matches the current provider are scored:
    a vector from a different model cannot be compared meaningfully, so it is
    skipped rather than producing a misleading score.
    """
    result = await session.execute(
        select(Memory)
        .where(Memory.owner_id == owner_id, Memory.deleted_at.is_(None))
        .order_by(Memory.created_at.desc())
        .limit(scan_limit)
    )
    memories = list(result.scalars().all())
    if not memories:
        return []

    query_vector = await provider.embed(query)
    scored: list[tuple[Memory, float]] = []
    for memory in memories:
        if memory.embedding_dimensions != provider.dimensions:
            continue
        vector = unpack_vector(cipher.decrypt(memory.embedding_encrypted))
        scored.append((memory, cosine_similarity(query_vector, vector)))

    scored.sort(key=lambda item: item[1], reverse=True)
    return scored[:top_k]
