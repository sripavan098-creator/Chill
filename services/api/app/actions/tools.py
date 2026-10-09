"""The tool registry for the Action Engine.

Every capability the assistant can invoke is declared here with an explicit
risk level. The engine refuses to run a tool that is not registered, so the
registry is the whole surface: there is no generic "run this code" tool and no
way for the model to reach outside it.

Risk levels:

- `low`    runs immediately. Read-only or trivially reversible.
- `medium` needs the owner's approval on an approval card first.
- `high`   needs approval *and* an explicit step-up confirmation. Voice
           recognition alone is never sufficient.

Tools receive a `ToolContext` with the owner-scoped session and the shared
services. A tool must not read or write another owner's data.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.crypto import EmbeddingCipher
from app.core.text_embeddings import TextEmbeddingProvider

RISK_LOW = "low"
RISK_MEDIUM = "medium"
RISK_HIGH = "high"

RISK_ORDER = {RISK_LOW: 0, RISK_MEDIUM: 1, RISK_HIGH: 2}


class ActionArgumentError(ValueError):
    """A tool was given arguments it cannot use."""


@dataclass
class ToolContext:
    """Everything a tool may use. Scoped to one owner."""

    owner_id: str
    device_id: str | None
    session: AsyncSession
    settings: Settings
    cipher: EmbeddingCipher
    text_embeddings: TextEmbeddingProvider


@dataclass(frozen=True)
class ActionTool:
    name: str
    description: str
    risk_level: str
    run: Callable[[ToolContext, dict], Awaitable[dict]]
    # Names of the parameters the tool accepts. Unknown arguments are rejected
    # before `run` is called.
    parameters: tuple[str, ...] = field(default_factory=tuple)

    @property
    def requires_approval(self) -> bool:
        return RISK_ORDER[self.risk_level] >= RISK_ORDER[RISK_MEDIUM]

    @property
    def requires_confirmation(self) -> bool:
        return self.risk_level == RISK_HIGH


def _require_text(arguments: dict, key: str, *, max_length: int) -> str:
    value = arguments.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ActionArgumentError(f"'{key}' is required.")
    value = value.strip()
    if len(value) > max_length:
        raise ActionArgumentError(f"'{key}' must be at most {max_length} characters.")
    return value


async def _memory_save(context: ToolContext, arguments: dict) -> dict:
    from app.services import memory as memory_service

    content = _require_text(arguments, "content", max_length=2000)
    memory = await memory_service.add_memory(
        context.session,
        owner_id=context.owner_id,
        content=content,
        provider=context.text_embeddings,
        cipher=context.cipher,
        source="action",
    )
    return {"memory_id": memory.id, "content": memory.content}


async def _memory_search(context: ToolContext, arguments: dict) -> dict:
    from app.services import memory as memory_service

    query = _require_text(arguments, "query", max_length=2000)
    matches = await memory_service.search_memories(
        context.session,
        owner_id=context.owner_id,
        query=query,
        provider=context.text_embeddings,
        cipher=context.cipher,
        top_k=context.settings.memory_top_k,
        scan_limit=context.settings.memory_scan_limit,
    )
    return {
        "matches": [
            {
                "memory_id": memory.id,
                "content": memory.content,
                "similarity": round(score, 4),
            }
            for memory, score in matches
        ]
    }


async def _list_memories(context: ToolContext, _arguments: dict) -> dict:
    from app.services import memory as memory_service

    memories = await memory_service.list_memories(
        context.session, owner_id=context.owner_id, limit=50
    )
    return {
        "memories": [
            {"memory_id": memory.id, "content": memory.content} for memory in memories
        ]
    }


async def _clear_memories(context: ToolContext, _arguments: dict) -> dict:
    from app.services import memory as memory_service

    memories = await memory_service.list_memories(
        context.session, owner_id=context.owner_id, limit=10_000
    )
    for memory in memories:
        await memory_service.delete_memory(
            context.session, owner_id=context.owner_id, memory_id=memory.id
        )
    return {"deleted": len(memories)}


async def _delete_voice_profile(context: ToolContext, _arguments: dict) -> dict:
    from app.services.voice_profile import purge_enrollment

    removed = await purge_enrollment(context.session, owner_id=context.owner_id)
    return {"deleted": bool(removed), "enrollments_removed": removed}


_TOOLS: tuple[ActionTool, ...] = (
    ActionTool(
        name="memory.save",
        description="Save a fact to the owner's long-term memory.",
        risk_level=RISK_LOW,
        run=_memory_save,
        parameters=("content",),
    ),
    ActionTool(
        name="memory.search",
        description="Search the owner's long-term memory.",
        risk_level=RISK_LOW,
        run=_memory_search,
        parameters=("query",),
    ),
    ActionTool(
        name="memory.list",
        description="List the facts stored in the owner's long-term memory.",
        risk_level=RISK_LOW,
        run=_list_memories,
    ),
    ActionTool(
        name="memory.clear",
        description="Delete every fact in the owner's long-term memory.",
        risk_level=RISK_MEDIUM,
        run=_clear_memories,
    ),
    ActionTool(
        name="voice.delete_profile",
        description="Delete the owner's voice profile and voice-derived data.",
        risk_level=RISK_HIGH,
        run=_delete_voice_profile,
    ),
)

REGISTRY: dict[str, ActionTool] = {tool.name: tool for tool in _TOOLS}


def get_tool(name: str) -> ActionTool | None:
    return REGISTRY.get(name)


def describe_tools() -> list[dict[str, object]]:
    """Registry summary, for the client and the model prompt."""
    return [
        {
            "name": tool.name,
            "description": tool.description,
            "risk_level": tool.risk_level,
            "requires_approval": tool.requires_approval,
            "requires_confirmation": tool.requires_confirmation,
            "parameters": list(tool.parameters),
        }
        for tool in _TOOLS
    ]
