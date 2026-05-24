"""Typed run state — what flows between LangGraph nodes."""
from __future__ import annotations

from typing import Annotated, Any, TypedDict

from langgraph.graph.message import add_messages


class RunState(TypedDict, total=False):
    run_id: str
    workflow_id: str
    input: str
    # message log (LangChain BaseMessage-compatible dicts)
    messages: Annotated[list[dict[str, Any]], add_messages]
    # free-form scratchpad agents can write to (e.g., {"draft": "...", "facts": [...]})
    scratch: dict[str, Any]
    # accounting
    steps: int
    cost_usd: float
    tokens: int
    # control
    halted: bool
    halt_reason: str
