from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _id() -> str:
    return uuid.uuid4().hex


class Run(Base):
    __tablename__ = "runs"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    workflow_id: Mapped[str] = mapped_column(String(32), ForeignKey("workflows.id"))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    trigger: Mapped[str] = mapped_column(String(32), default="manual")  # manual | telegram | schedule
    input: Mapped[str] = mapped_column(Text, default="")
    output: Mapped[str] = mapped_column(Text, default="")
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)


class RunEvent(Base):
    """Append-only event log per run — replays the live monitor."""
    __tablename__ = "run_events"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    run_id: Mapped[str] = mapped_column(String(32), ForeignKey("runs.id"), index=True)
    type: Mapped[str] = mapped_column(String(48))  # node_start, node_end, tool_call, llm_token, message, guardrail
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
