from __future__ import annotations

import abc
from typing import Any, Dict

from .async_zulip import AsyncClient
from .models import Event, Message, PrivateMessageRequest, StreamMessageRequest


class BaseBot(abc.ABC):
    """Base class for bots. Override `on_message` and optional `on_event`."""

    def __init__(self, client: AsyncClient) -> None:
        self.client = client

    async def on_start(self) -> None:
        """Hook for startup logic. Override if needed."""
        return None

    async def on_stop(self) -> None:
        """Hook for cleanup logic. Override if needed."""
        return None

    async def on_event(self, event: Event) -> None:
        if event.type == "message" and event.message is not None:
            await self.on_message(event.message)

    @abc.abstractmethod
    async def on_message(self, message: Message) -> None:
        ...

    async def send_reply(self, original: Message, content: str) -> None:
        """Utility to reply to a message (stream or private)."""
        if original.type == "private":
            recipients_raw = original.display_recipient or []
            if isinstance(recipients_raw, str):
                # should not happen for private, but tolerate
                to = []
            else:
                to = [r.id for r in recipients_raw if getattr(r, "id", None) is not None]
            payload = PrivateMessageRequest(to=to, content=content)
        else:
            topic = original.topic_or_subject or "general"
            if original.stream_id is None:
                raise ValueError("stream_id missing on stream message")
            payload = StreamMessageRequest(to=original.stream_id, topic=topic, content=content)

        await self.client.send_message(payload.model_dump(exclude_none=True))


__all__ = ["BaseBot"]
