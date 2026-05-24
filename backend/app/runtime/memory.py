"""Memory strategies. Each returns a list of prior turns to prepend to the prompt."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.message import Message


async def load_memory(
    session: AsyncSession,
    *,
    run_id: str | None,
    strategy: dict[str, Any],
) -> list[dict[str, str]]:
    kind = strategy.get("strategy", "window")
    if kind == "none" or not run_id:
        return []

    if kind == "window":
        n = int(strategy.get("n", 6))
        result = await session.execute(
            select(Message)
            .where(Message.run_id == run_id)
            .order_by(Message.created_at.desc())
            .limit(n * 2)
        )
        msgs = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in msgs]

    if kind == "summary":
        # MVP: behaves like window:N; the summarizer step is a follow-up.
        # See ARCHITECTURE §6 — pgvector + summarizer is the next iteration.
        n = int(strategy.get("n", 10))
        result = await session.execute(
            select(Message)
            .where(Message.run_id == run_id)
            .order_by(Message.created_at.desc())
            .limit(n * 2)
        )
        msgs = list(reversed(result.scalars().all()))
        return [{"role": m.role, "content": m.content} for m in msgs]

    return []
