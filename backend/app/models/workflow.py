from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def _id() -> str:
    return uuid.uuid4().hex


class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(32), primary_key=True, default=_id)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    # spec = {"entrypoint": str, "nodes": [...], "edges": [...]}
    spec: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
