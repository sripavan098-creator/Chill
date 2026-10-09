"""The Action Engine: risk gating, approval and safe execution.

The engine is the only path from a request to a tool. It enforces, in order:

1. The tool must be registered and (if the deployment narrowed the surface)
   allowed by `action_allowlist`.
2. The request is rate-limited per device.
3. A low-risk tool runs immediately.
4. A medium-risk tool is queued as `pending` and runs only on approval.
5. A high-risk tool additionally requires the exact confirmation phrase. Voice
   recognition is never sufficient on its own.

Every state change is written to the append-only audit log. Approval is bound
to the owner: an action created for one owner cannot be approved or executed by
another.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.actions.tools import (
    RISK_HIGH,
    ActionArgumentError,
    ActionTool,
    ToolContext,
    get_tool,
)
from app.core.config import Settings
from app.core.crypto import EmbeddingCipher
from app.core.errors import (
    ActionNotAllowedError,
    ActionNotFoundError,
    ActionPendingError,
    ConfirmationRequiredError,
    TooManyPendingActionsError,
    ValidationError,
)
from app.core.text_embeddings import TextEmbeddingProvider
from app.db.models import ActionRequest
from app.services import audit, limits

CONFIRMATION_PHRASE = "CONFIRM"
PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
EXECUTED = "executed"
FAILED = "failed"
EXPIRED = "expired"
REJECTED = "rejected"


def _now() -> datetime:
    return datetime.now(UTC)


def _as_utc(value: datetime) -> datetime:
    """Treat a naive timestamp as UTC.

    SQLite hands back naive datetimes for timezone-aware columns while Postgres
    keeps the offset; normalising keeps the expiry check identical on both.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def _dump(arguments: dict) -> str:
    return json.dumps(arguments, sort_keys=True)


def _load(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


class ActionEngine:
    """Owner-scoped tool execution with risk gating and approvals."""

    def __init__(
        self,
        *,
        settings: Settings,
        cipher: EmbeddingCipher,
        text_embeddings: TextEmbeddingProvider,
    ) -> None:
        self._settings = settings
        self._cipher = cipher
        self._text_embeddings = text_embeddings

    def _allowed(self, tool: ActionTool) -> bool:
        allowlist = self._settings.allowed_action_names
        return allowlist is None or tool.name in allowlist

    def _context(
        self, session: AsyncSession, *, owner_id: str, device_id: str | None
    ) -> ToolContext:
        return ToolContext(
            owner_id=owner_id,
            device_id=device_id,
            session=session,
            settings=self._settings,
            cipher=self._cipher,
            text_embeddings=self._text_embeddings,
        )

    def _validate_arguments(self, tool: ActionTool, arguments: dict) -> None:
        unknown = set(arguments) - set(tool.parameters)
        if unknown:
            # A client error, so it is a 422 rather than a tool failure. This
            # runs before the action is created, so nothing is left behind.
            raise ValidationError(
                f"Unknown argument(s) for '{tool.name}': {', '.join(sorted(unknown))}."
            )

    async def _run_tool(
        self, session: AsyncSession, action: ActionRequest
    ) -> ActionRequest:
        tool = get_tool(action.tool_name)
        assert tool is not None  # only registered tools are ever stored
        context = self._context(
            session, owner_id=action.owner_id, device_id=action.device_id
        )
        try:
            result = await tool.run(context, _load(action.arguments))
        except ActionArgumentError as exc:
            action.status = FAILED
            action.error = str(exc)
        except Exception as exc:  # noqa: BLE001 - a tool failure must not leak
            # The message may name internal state, so it is kept short and the
            # full error is left to the server log rather than the response.
            action.status = FAILED
            action.error = f"The action failed: {type(exc).__name__}."
        else:
            action.status = EXECUTED
            action.result = json.dumps(result, sort_keys=True)
            action.error = None
        action.executed_at = _now()
        await audit.record_event(
            session,
            event="action.executed" if action.status == EXECUTED else "action.failed",
            outcome="ok" if action.status == EXECUTED else "error",
            owner_id=action.owner_id,
            device_id=action.device_id,
            detail=f"tool={action.tool_name} risk={action.risk_level}",
        )
        await session.flush()
        return action

    async def request_action(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        device_id: str | None,
        tool_name: str,
        arguments: dict | None = None,
        summary: str | None = None,
    ) -> ActionRequest:
        """Ask for a tool to run. Low-risk tools run now; others become pending."""
        if not self._settings.actions_enabled:
            raise ActionNotAllowedError("Actions are disabled on this deployment.")

        arguments = arguments or {}
        tool = get_tool(tool_name)
        if tool is None:
            await audit.record_event(
                session,
                event="action.rejected",
                outcome="denied",
                owner_id=owner_id,
                device_id=device_id,
                detail=f"unknown_tool={tool_name}",
            )
            await session.commit()
            raise ActionNotFoundError(f"Unknown action '{tool_name}'.")

        if not self._allowed(tool):
            await audit.record_event(
                session,
                event="action.rejected",
                outcome="denied",
                owner_id=owner_id,
                device_id=device_id,
                detail=f"not_allowed={tool_name}",
            )
            await session.commit()
            raise ActionNotAllowedError(f"Action '{tool_name}' is not allowed.")

        self._validate_arguments(tool, arguments)

        await limits.enforce_rate_limit(
            session,
            scope="action",
            subject=device_id or owner_id,
            limit=self._settings.action_rate_limit,
            window_seconds=self._settings.rate_limit_window_seconds,
        )

        action = ActionRequest(
            owner_id=owner_id,
            device_id=device_id,
            tool_name=tool.name,
            risk_level=tool.risk_level,
            status=PENDING,
            summary=(summary or tool.description)[:400],
            arguments=_dump(arguments),
        )

        if not tool.requires_approval:
            session.add(action)
            await session.flush()
            await self._run_tool(session, action)
            await session.commit()
            return action

        # Medium and high risk: queue for approval, bounded by a cap so a caller
        # cannot fill the queue.
        pending_count = await session.scalar(
            select(func.count())
            .select_from(ActionRequest)
            .where(
                ActionRequest.owner_id == owner_id,
                ActionRequest.status == PENDING,
            )
        )
        if (pending_count or 0) >= self._settings.action_max_pending:
            raise TooManyPendingActionsError(
                "Too many actions are waiting for approval. Resolve them first."
            )

        action.expires_at = _now() + timedelta(
            seconds=self._settings.action_approval_ttl_seconds
        )
        session.add(action)
        await session.flush()
        await audit.record_event(
            session,
            event="action.requested",
            owner_id=owner_id,
            device_id=device_id,
            detail=f"tool={tool.name} risk={tool.risk_level}",
        )
        await session.commit()
        return action

    async def list_actions(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        status: str | None = None,
        limit: int = 50,
    ) -> list[ActionRequest]:
        query = select(ActionRequest).where(ActionRequest.owner_id == owner_id)
        if status:
            query = query.where(ActionRequest.status == status)
        query = query.order_by(ActionRequest.created_at.desc()).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_action(
        self, session: AsyncSession, *, owner_id: str, action_id: str
    ) -> ActionRequest:
        action = await session.get(ActionRequest, action_id)
        if action is None or action.owner_id != owner_id:
            raise ActionNotFoundError("Action not found.")
        return action

    async def approve_action(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        device_id: str | None,
        action_id: str,
        confirm: str | None = None,
    ) -> ActionRequest:
        """Approve and run a pending action.

        A high-risk action also needs `confirm == CONFIRM`. This is the step-up
        gate: approval alone is not enough for the most dangerous tools.
        """
        action = await self.get_action(session, owner_id=owner_id, action_id=action_id)
        if action.status != PENDING:
            raise ActionPendingError(
                f"This action is already {action.status} and cannot be approved."
            )
        if action.expires_at is not None and _as_utc(action.expires_at) < _now():
            action.status = EXPIRED
            await session.commit()
            raise ActionPendingError("This approval request has expired.")

        if action.risk_level == RISK_HIGH and confirm != CONFIRMATION_PHRASE:
            raise ConfirmationRequiredError(
                f"Deleting this requires typing '{CONFIRMATION_PHRASE}' to confirm."
            )

        action.status = APPROVED
        action.confirmation = confirm
        action.decided_at = _now()
        await audit.record_event(
            session,
            event="action.approved",
            owner_id=owner_id,
            device_id=device_id,
            detail=f"tool={action.tool_name} risk={action.risk_level}",
        )
        await self._run_tool(session, action)
        await session.commit()
        return action

    async def deny_action(
        self,
        session: AsyncSession,
        *,
        owner_id: str,
        device_id: str | None,
        action_id: str,
    ) -> ActionRequest:
        action = await self.get_action(session, owner_id=owner_id, action_id=action_id)
        if action.status != PENDING:
            raise ActionPendingError(
                f"This action is already {action.status} and cannot be denied."
            )
        action.status = DENIED
        action.decided_at = _now()
        await audit.record_event(
            session,
            event="action.denied",
            owner_id=owner_id,
            device_id=device_id,
            detail=f"tool={action.tool_name}",
        )
        await session.commit()
        return action
