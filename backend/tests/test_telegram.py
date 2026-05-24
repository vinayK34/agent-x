"""Telegram adapter wiring — uses the ABC directly with a fake transport
to verify inbound → runtime → outbound path without hitting Telegram API.
"""
import asyncio

import pytest

from app.channels.base import ChannelAdapter, InboundMessage


class FakeChannel(ChannelAdapter):
    name = "telegram"

    def __init__(self):
        self.sent: list[tuple[str, str]] = []
        self._cb = None

    async def start(self, on_message):
        self._cb = on_message

    async def stop(self):
        pass

    async def send(self, chat_id, text):
        self.sent.append((chat_id, text))

    async def simulate(self, text: str, chat_id: str = "42"):
        await self._cb(InboundMessage(channel="telegram", chat_id=chat_id, user="u", text=text))


@pytest.mark.asyncio
async def test_inbound_message_triggers_run(client):
    # seed an agent on telegram
    agent = (await client.post("/agents", json={
        "name": "Tel",
        "system_prompt": "echo",
        "channels": ["telegram"],
    })).json()

    # wrap it as a 1-node workflow
    spec = {
        "entrypoint": "n",
        "nodes": [{"id": "n", "type": "agent", "agent_id": agent["id"]}],
        "edges": [{"from": "n", "to": "__end__"}],
    }
    await client.post("/workflows", json={"name": "telwf", "spec": spec})

    from app.main import _on_channel_message
    ch = FakeChannel()
    await ch.start(lambda m: _on_channel_message(ch, m))
    await ch.simulate("ping")

    # Allow background tasks to run
    for _ in range(30):
        await asyncio.sleep(0.1)
        if ch.sent:
            break

    assert ch.sent, "channel never received an outbound reply"
    assert ch.sent[0][0] == "42"
