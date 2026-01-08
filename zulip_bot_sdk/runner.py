from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, Iterable, List, Optional, Type

from .async_zulip import AsyncClient
from .bot import BaseBot
from .logging import logger


class BotRunner:
    """Glue code to run a bot with AsyncClient."""

    def __init__(
        self,
        bot_factory: Callable[[AsyncClient], BaseBot],
        *,
        event_types: Optional[List[str]] = None,
        narrow: Optional[List[List[str]]] = None,
        client_kwargs: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.bot_factory = bot_factory
        self.event_types = event_types or ["message"]
        self.narrow = narrow or []
        self.client_kwargs = client_kwargs or {}
        self.client: Optional[AsyncClient] = None
        self.bot: Optional[BaseBot] = None

    async def __aenter__(self) -> "BotRunner":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        self.client = AsyncClient(**self.client_kwargs)
        self.bot = self.bot_factory(self.client)
        logger.info("Bot started with event types {}", self.event_types)
        await self.client.ensure_session()
        await self.bot.on_start()

    async def stop(self) -> None:
        if self.bot:
            await self.bot.on_stop()
        if self.client:
            await self.client.aclose()
            logger.info("Bot stopped")

    async def run_forever(self) -> None:
        if not self.client or not self.bot:
            await self.start()
        assert self.client and self.bot
        await self.client.call_on_each_event(self.bot.on_event, self.event_types, self.narrow)


def run_bot(
    bot_cls: Type[BaseBot],
    *,
    event_types: Optional[List[str]] = None,
    narrow: Optional[List[List[str]]] = None,
    client_kwargs: Optional[Dict[str, Any]] = None,
) -> None:
    """Convenience entrypoint."""

    runner = BotRunner(lambda c: bot_cls(c), event_types=event_types, narrow=narrow, client_kwargs=client_kwargs)

    async def _run() -> None:
        async with runner:
            await runner.run_forever()

    asyncio.run(_run())


__all__ = ["BotRunner", "run_bot"]
