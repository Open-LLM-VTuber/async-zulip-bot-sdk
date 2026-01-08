from __future__ import annotations

import abc
from loguru import logger

from .async_zulip import AsyncClient
from .commands import CommandInvocation, CommandParser
from .models import (
    Event,
    Message,
    PrivateMessageRequest,
    StreamMessageRequest,
    UpdatePresenceRequest
)


class BaseBot(abc.ABC):
    """Base class for bots. Override `on_message` and optional `on_event`."""

    # Prefix characters that mark a command (e.g., "/help" or "!ping").
    command_prefixes = ("/", "!")
    # Whether to treat leading @-mentions as commands.
    enable_mention_commands = True
    # Whether to auto-register the built-in help command.
    auto_help_command = True

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.command_parser = CommandParser(
            prefixes=self.command_prefixes,
            enable_mentions=self.enable_mention_commands,
            auto_help=self.auto_help_command,
        )
        logger.debug(f"Initialized bot {self.__class__.__name__}")
        
    async def post_init(self) -> None:
        """Hook for post-initialization logic. Override if needed."""
        
        logger.debug("Fetching bot profile for command parser identity aliases")
        profile = await self.client.get_profile()
        self._user_id = profile.user_id
        self._user_name = profile.full_name
        self.command_parser.add_identity_aliases(full_name=self._user_name, email=getattr(profile, "email", None))
        logger.info(f"{self.__class__.__name__} started with user_id: {self._user_id}")
        
        await self.client.update_presence(
            UpdatePresenceRequest(
                status="active",
            )
        )
        logger.info("Set presence to active")

    async def on_start(self) -> None:
        """Hook for startup logic. Override if needed."""
        return None

    async def on_stop(self) -> None:
        """Hook for cleanup logic. Override if needed."""
        return None

    async def on_event(self, event: Event) -> None:
        if event.type == "message" and event.message is not None:
            logger.debug(f"Received message: {event.message}")
            if event.message.sender_id == self._user_id:
                logger.debug("Ignoring message from self")
                return  # Ignore messages from ourselves
            try:
                command_invocation = self.parse_command(event.message)
            except Exception as exc:  # CommandError and others
                logger.warning(f"Command parsing failed: {exc}")
                await self.send_reply(event.message, f"Command error: {exc}")
                return

            if command_invocation is not None:
                try:
                    await self.command_parser.dispatch(command_invocation, message=event.message, bot=self)
                except Exception as exc:
                    logger.warning(f"Command dispatch failed: {exc}")
                    await self.send_reply(event.message, f"Command error: {exc}")
            else:
                await self.on_message(event.message)

    @abc.abstractmethod
    async def on_message(self, message: Message) -> None:
        ...

    # Legacy hook retained for backwards compatibility; prefer per-command handlers.
    async def on_command(self, command: CommandInvocation, message: Message) -> None:
        return None

    def parse_command(self, message: Message) -> CommandInvocation | None:
        return self.command_parser.parse_message(message)

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
