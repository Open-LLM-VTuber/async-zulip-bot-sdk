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
        self._stop_event = asyncio.Event()
        self._longpoll_task: Optional[asyncio.Task[None]] = None

    async def __aenter__(self) -> "BotRunner":
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        await self.stop()

    async def start(self) -> None:
        self.client = AsyncClient(**self.client_kwargs)
        self.bot = self.bot_factory(self.client)
        # Give the bot a back-reference so commands can trigger runner-level actions (e.g., stop).
        if hasattr(self.bot, "set_runner"):
            self.bot.set_runner(self)
        await self.bot.post_init()
        logger.info("Bot started with event types {}", self.event_types)
        await self.client.ensure_session()
        await self.bot.on_start()

    async def stop(self) -> None:
        # Stop accepting new work and drain in-flight event tasks.
        self._stop_event.set()
        if self._longpoll_task:
            self._longpoll_task.cancel()
            await asyncio.gather(self._longpoll_task, return_exceptions=True)
            self._longpoll_task = None
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
        self._stop_event.clear()

        async def _handle_event(event: Any) -> None:
            # Schedule event handling with bounded concurrency so one slow handler
            # does not block the long-poll loop.
            async def _run() -> None:
                async with self._semaphore:
                    assert self.bot
                    if self._stop_event.is_set():
                        return
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
        self._longpoll_task = asyncio.create_task(
            self.client.call_on_each_event(_handle_event, self.event_types, self.narrow, stop_event=self._stop_event)
        )
        stop_waiter = asyncio.create_task(self._stop_event.wait())

        try:
            done, pending = await asyncio.wait({self._longpoll_task, stop_waiter}, return_when=asyncio.FIRST_COMPLETED)
            if stop_waiter in done:
                logger.info("Stop requested; cancelling event stream")
                if self._longpoll_task:
                    self._longpoll_task.cancel()
            elif self._longpoll_task in done:
                # Event loop finished unexpectedly; propagate or cleanly exit.
                exc = self._longpoll_task.exception() if self._longpoll_task else None
                if exc:
                    raise exc
                logger.warning("Event stream completed unexpectedly; shutting down")
                self._stop_event.set()
        finally:
            if self._longpoll_task:
                await asyncio.gather(self._longpoll_task, return_exceptions=True)
                self._longpoll_task = None
            stop_waiter.cancel()
            await asyncio.gather(stop_waiter, return_exceptions=True)

    def request_stop(self, *, reason: Optional[str] = None) -> None:
        """Signal the long-running loop to stop and cancel long-polls."""
        if self._stop_event.is_set():
            return
        if reason:
            logger.info("Stop requested: {}", reason)
        self._stop_event.set()
        if self._longpoll_task:
            self._longpoll_task.cancel()


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
