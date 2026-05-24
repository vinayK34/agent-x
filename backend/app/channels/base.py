"""Channel adapter ABC. Implement once per messaging platform."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Awaitable, Callable


@dataclass
class InboundMessage:
    channel: str
    chat_id: str
    user: str
    text: str


OnMessage = Callable[[InboundMessage], Awaitable[None]]


class ChannelAdapter(ABC):
    name: str

    @abstractmethod
    async def start(self, on_message: OnMessage) -> None: ...
    @abstractmethod
    async def stop(self) -> None: ...
    @abstractmethod
    async def send(self, chat_id: str, text: str) -> None: ...
