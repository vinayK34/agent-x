"""Live monitor WebSocket — subscribes the client to the EventBus."""
from __future__ import annotations

import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.events import bus

router = APIRouter()


@router.websocket("/ws/monitor")
async def monitor(ws: WebSocket) -> None:
    await ws.accept()
    try:
        async for event in bus.subscribe("monitor"):
            await ws.send_text(json.dumps(event, default=str))
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:  # pragma: no cover
        return
