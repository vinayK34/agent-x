"""Telegram adapter — long-polling, fully local (no public URL required)."""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from telegram import Update
from telegram.ext import Application, ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest

from app.channels.base import ChannelAdapter, InboundMessage, OnMessage
from app.config import get_settings

log = logging.getLogger(__name__)


class TelegramChannel(ChannelAdapter):
    name = "telegram"

    def __init__(self, token: str | None = None) -> None:
        self.token = token or get_settings().telegram_bot_token
        self._app: Optional[Application] = None
        self._task: Optional[asyncio.Task] = None

    async def start(self, on_message: OnMessage) -> None:
        if not self.token:
            log.warning("telegram: TELEGRAM_BOT_TOKEN not set — adapter disabled")
            return

        # Fail fast if the network/token is bad, but never crash the host app.
        request = HTTPXRequest(connect_timeout=5.0, read_timeout=10.0, write_timeout=10.0, pool_timeout=5.0)
        self._app = (
            ApplicationBuilder()
            .token(self.token)
            .request(request)
            .get_updates_request(HTTPXRequest(connect_timeout=5.0, read_timeout=35.0))
            .build()
        )

        async def handler(update: Update, _ctx: ContextTypes.DEFAULT_TYPE) -> None:
            msg = update.effective_message
            if not msg or not msg.text:
                return
            await on_message(
                InboundMessage(
                    channel="telegram",
                    chat_id=str(msg.chat_id),
                    user=msg.from_user.username if msg.from_user else "unknown",
                    text=msg.text,
                )
            )

        self._app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handler))

        try:
            await self._app.initialize()
            await self._app.start()
            await self._app.updater.start_polling(drop_pending_updates=True)
            log.info("telegram: long-polling started")
        except Exception as e:  # noqa: BLE001
            log.error("telegram: failed to start (%s: %s) — disabling adapter", type(e).__name__, e)
            # Clean up partially-initialized state and swallow — host app must keep booting.
            try:
                await self._app.shutdown()
            except Exception:  # noqa: BLE001
                pass
            self._app = None

    async def stop(self) -> None:
        if not self._app:
            return
        try:
            await self._app.updater.stop()
            await self._app.stop()
            await self._app.shutdown()
        except Exception:  # noqa: BLE001
            pass

    async def send(self, chat_id: str, text: str) -> None:
        if not self._app:
            return
        await self._app.bot.send_message(chat_id=chat_id, text=text)
