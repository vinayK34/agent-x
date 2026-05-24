"""In-process pub/sub for live monitoring.

Replace with Redis pub/sub when going multi-replica (see ARCHITECTURE §9).
"""
from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any, AsyncIterator


class EventBus:
    def __init__(self) -> None:
        self._subs: dict[str, set[asyncio.Queue]] = defaultdict(set)

    async def publish(self, topic: str, event: dict[str, Any]) -> None:
        for q in list(self._subs[topic]):
            await q.put(event)
        # Wildcard subscribers see everything
        for q in list(self._subs["*"]):
            await q.put({"topic": topic, **event})

    async def subscribe(self, topic: str = "*") -> AsyncIterator[dict[str, Any]]:
        q: asyncio.Queue = asyncio.Queue(maxsize=1024)
        self._subs[topic].add(q)
        try:
            while True:
                yield await q.get()
        finally:
            self._subs[topic].discard(q)


bus = EventBus()
