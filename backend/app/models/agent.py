"""Agent ORM — the heart of the configuration surface."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _id() -> str:
    return uuid.uuid4().hex


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    role: Mapped[str] = mapped_column(String(120), default="")
    avatar: Mapped[str] = mapped_column(String(8), default="🤖")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    model: Mapped[str] = mapped_column(String(80), default="gpt-4o-mini")
    temperature: Mapped[float] = mapped_column(Float, default=0.3)
    max_tokens: Mapped[int] = mapped_column(Integer, default=1024)

    # JSON columns — agent configuration evolves fast; see ARCHITECTURE §3
    tools: Mapped[list[str]] = mapped_column(JSON, default=list)
    memory: Mapped[dict[str, Any]] = mapped_column(JSON, default=lambda: {"strategy": "window", "n": 6})
    schedule: Mapped[str | None] = mapped_column(String(64), nullable=True)
    skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    can_talk_to: Mapped[list[str]] = mapped_column(JSON, default=list)
    guardrails: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=lambda: {"max_steps": 20, "max_cost_usd": 1.0, "denylist_regex": []}
    )
    channels: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
