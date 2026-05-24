"""Pydantic request/response schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class AgentIn(BaseModel):
    name: str
    role: str = ""
    avatar: str = "🤖"
    system_prompt: str = ""
    model: str = "gpt-4o-mini"
    temperature: float = 0.3
    max_tokens: int = 1024
    tools: list[str] = []
    memory: dict[str, Any] = Field(default_factory=lambda: {"strategy": "window", "n": 6})
    schedule: str | None = None
    skills: list[str] = []
    can_talk_to: list[str] = []
    guardrails: dict[str, Any] = Field(default_factory=lambda: {"max_steps": 20, "max_cost_usd": 1.0, "denylist_regex": []})
    channels: list[str] = []


class AgentOut(AgentIn):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class WorkflowIn(BaseModel):
    name: str
    description: str = ""
    spec: dict[str, Any]


class WorkflowOut(WorkflowIn):
    id: str
    created_at: datetime

    class Config:
        from_attributes = True


class RunIn(BaseModel):
    workflow_id: str
    input: str


class RunOut(BaseModel):
    id: str
    workflow_id: str
    status: str
    trigger: str
    input: str
    output: str
    cost_usd: float
    tokens: int
    started_at: datetime
    finished_at: datetime | None
    error: str | None

    class Config:
        from_attributes = True


class MessageOut(BaseModel):
    id: str
    run_id: str | None
    from_agent_id: str | None
    role: str
    channel: str | None
    content: str
    created_at: datetime

    class Config:
        from_attributes = True
