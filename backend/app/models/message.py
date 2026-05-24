from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _id() -> str:
    return uuid.uuid4().hex


class Message(Base):
    """Conversation log — persisted, visible in UI (success criterion)."""
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    run_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("runs.id"), nullable=True, index=True)
    from_agent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("agents.id"), nullable=True)
    to_agent_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("agents.id"), nullable=True)
    role: Mapped[str] = mapped_column(String(16))  # user | assistant | system | tool | agent
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    content: Mapped[str] = mapped_column(Text)
    tool_calls: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
