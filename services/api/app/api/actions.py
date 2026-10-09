"""Action Engine endpoints.

The flow is: the assistant (or the client) proposes an action, a low-risk action
runs at once, and a medium- or high-risk action becomes an approval card. The
owner approves or denies it; a high-risk action needs the confirmation phrase as
well. Every transition is audited.

Approval is owner-scoped: an action created by one owner is not visible to, and
cannot be approved by, another.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Query, Request

from app.actions import tools as tool_registry
from app.api.deps import DeviceDep, SessionDep
from app.db.models import ActionRequest
from app.schemas.actions import (
    ActionApproveRequest,
    ActionListResponse,
    ActionOut,
    ActionRequestIn,
    ActionToolListResponse,
    ActionToolOut,
)
from app.services import limits

router = APIRouter(tags=["actions"])


def _load(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def to_action_out(action: ActionRequest) -> ActionOut:
    tool = tool_registry.get_tool(action.tool_name)
    return ActionOut(
        id=action.id,
        tool_name=action.tool_name,
        risk_level=action.risk_level,
        status=action.status,
        summary=action.summary,
        arguments=_load(action.arguments),
        result=_load(action.result) if action.result else None,
        error=action.error,
        requires_confirmation=bool(tool and tool.requires_confirmation),
        expires_at=action.expires_at,
        created_at=action.created_at,
        executed_at=action.executed_at,
    )


@router.get("/actions/tools", response_model=ActionToolListResponse)
async def list_tools() -> ActionToolListResponse:
    """The registry, so the client can render the right approval affordance."""
    return ActionToolListResponse(
        tools=[ActionToolOut(**tool) for tool in tool_registry.describe_tools()]
    )


@router.post("/actions", response_model=ActionOut)
async def request_action(
    payload: ActionRequestIn,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ActionOut:
    engine = request.app.state.actions
    action = await engine.request_action(
        session,
        owner_id=device.owner_id,
        device_id=device.id,
        tool_name=payload.tool_name,
        arguments=payload.arguments,
        summary=payload.summary,
    )
    return to_action_out(action)


@router.get("/actions", response_model=ActionListResponse)
async def list_actions(
    request: Request,
    session: SessionDep,
    device: DeviceDep,
    status: str | None = Query(default=None, max_length=16),
) -> ActionListResponse:
    engine = request.app.state.actions
    actions = await engine.list_actions(
        session, owner_id=device.owner_id, status=status
    )
    return ActionListResponse(actions=[to_action_out(action) for action in actions])


@router.get("/actions/{action_id}", response_model=ActionOut)
async def get_action(
    action_id: str,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ActionOut:
    engine = request.app.state.actions
    action = await engine.get_action(
        session, owner_id=device.owner_id, action_id=action_id
    )
    return to_action_out(action)


@router.post("/actions/{action_id}/approve", response_model=ActionOut)
async def approve_action(
    action_id: str,
    payload: ActionApproveRequest,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ActionOut:
    settings = request.app.state.settings
    await limits.enforce_rate_limit(
        session,
        scope="action-approval",
        subject=device.id,
        limit=settings.action_approval_rate_limit,
        window_seconds=settings.rate_limit_window_seconds,
    )
    engine = request.app.state.actions
    action = await engine.approve_action(
        session,
        owner_id=device.owner_id,
        device_id=device.id,
        action_id=action_id,
        confirm=payload.confirm,
    )
    return to_action_out(action)


@router.post("/actions/{action_id}/deny", response_model=ActionOut)
async def deny_action(
    action_id: str,
    request: Request,
    session: SessionDep,
    device: DeviceDep,
) -> ActionOut:
    engine = request.app.state.actions
    action = await engine.deny_action(
        session,
        owner_id=device.owner_id,
        device_id=device.id,
        action_id=action_id,
    )
    return to_action_out(action)
