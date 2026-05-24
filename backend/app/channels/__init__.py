"""Channel registry — add a new channel by registering it here."""
from __future__ import annotations

from app.channels.base import ChannelAdapter
from app.channels.telegram import TelegramChannel

REGISTRY: dict[str, type[ChannelAdapter]] = {
    "telegram": TelegramChannel,
    # "slack": SlackChannel,        # add here
    # "whatsapp": WhatsAppChannel,
}

__all__ = ["REGISTRY", "ChannelAdapter"]
