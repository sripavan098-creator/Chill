"""Parse action proposals out of a model reply.

The assistant proposes an action by emitting a fenced JSON block:

    ```action
    {"tool_name": "memory.save", "arguments": {"content": "..."},
     "summary": "Save a fact to memory"}
    ```

The block is data, not a command: the Action Engine still applies the risk
rules. A low-risk proposal runs; a medium- or high-risk one becomes an approval
card and does not run until the owner approves it.

Parsing is deliberately strict. A malformed block is dropped rather than
guessed at, and the block is removed from the visible reply so the owner reads
prose, not JSON.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

# Matches a fenced ```action ... ``` block, capturing the body.
_ACTION_BLOCK = re.compile(
    r"```action\s*\n(?P<body>.*?)\n?```",
    re.DOTALL | re.IGNORECASE,
)


@dataclass(frozen=True)
class ActionProposal:
    tool_name: str
    arguments: dict
    summary: str | None


def extract_action(reply: str) -> tuple[str, ActionProposal | None]:
    """Return the reply without its action block, and the proposal if any.

    Only the first block is used; a second is removed but ignored, so a model
    cannot smuggle two actions past a single approval card.
    """
    match = _ACTION_BLOCK.search(reply)
    if match is None:
        return reply, None

    clean = _ACTION_BLOCK.sub("", reply).strip()
    try:
        payload = json.loads(match.group("body"))
    except json.JSONDecodeError:
        return clean, None

    if not isinstance(payload, dict):
        return clean, None
    tool_name = payload.get("tool_name")
    if not isinstance(tool_name, str) or not tool_name.strip():
        return clean, None
    arguments = payload.get("arguments") or {}
    if not isinstance(arguments, dict):
        return clean, None
    summary = payload.get("summary")
    if summary is not None and not isinstance(summary, str):
        summary = None

    return clean, ActionProposal(
        tool_name=tool_name.strip(), arguments=arguments, summary=summary
    )
