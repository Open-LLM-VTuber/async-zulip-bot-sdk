from __future__ import annotations

import asyncio
from typing import Any, Callable, Dict, List, Optional, Set, Type

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
        max_concurrency: int = 8,
    ) -> None:
        self.bot_factory = bot_factory
        self.event_types = event_types or ["message"]
        self.narrow = narrow or []
        self.client_kwargs = client_kwargs or {}
        self.client: Optional[AsyncClient] = None
        self.bot: Optional[BaseBot] = None
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._tasks: Set[asyncio.Task[None]] = set()
        self._max_concurrency = max_concurrency

    async def __aenter__(self) -> "BotRunner":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        self.client = AsyncClient(**self.client_kwargs)
        self.bot = self.bot_factory(self.client)
        await self.bot.post_init()
        logger.info("Bot started with event types {}", self.event_types)
        await self.client.ensure_session()
        await self.bot.on_start()

    async def stop(self) -> None:
        # Stop accepting new work and drain in-flight event tasks.
        for task in list(self._tasks):
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks.clear()

        if self.bot:
            await self.bot.on_stop()
        if self.client:
            await self.client.aclose()
            logger.info("Bot stopped")

    async def run_forever(self) -> None:
        if not self.client or not self.bot:
            await self.start()
        assert self.client and self.bot

        async def _handle_event(event: Any) -> None:
            # Schedule event handling with bounded concurrency so one slow handler
            # does not block the long-poll loop.
            async def _run() -> None:
                async with self._semaphore:
                    assert self.bot
                    await self.bot.on_event(event)

            task = asyncio.create_task(_run())
            self._tasks.add(task)

            def _cleanup(t: asyncio.Task[None]) -> None:
                self._tasks.discard(t)
                if t.cancelled():
                    return
                exc = t.exception()
                if exc:
                    logger.exception("Unhandled error in bot event task: {}", exc)

            task.add_done_callback(_cleanup)

        logger.info(
            "Starting event loop with max_concurrency={} and event_types={}",
            self._max_concurrency,
            self.event_types,
        )
        await self.client.call_on_each_event(_handle_event, self.event_types, self.narrow)


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
