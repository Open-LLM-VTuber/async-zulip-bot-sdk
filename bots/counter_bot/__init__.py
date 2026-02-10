"""
Counter bot - demonstrates storage usage with dict-like interface.

Commands:
    !count - Increment counter and show current count
    !reset - Reset counter to zero
    !stats - Show detailed statistics
"""

from bot_sdk import BaseBot, CommandInvocation, CommandSpec, Message


class CounterBot(BaseBot):
    """A simple bot that counts messages using persistent storage."""

    def register_commands(self) -> None:
        self.command_parser.register_spec(
            CommandSpec(
                name="count",
                description="Increment counter and show current count",
                handler=self._handle_count,
            )
        )

        self.command_parser.register_spec(
            CommandSpec(
                name="reset",
                description="Reset counter to zero",
                handler=self._handle_reset,
            )
        )

        self.command_parser.register_spec(
            CommandSpec(
                name="stats",
                description="Show detailed statistics",
                handler=self._handle_stats,
            )
        )

    async def _handle_count(
        self, invocation: CommandInvocation, message: Message, bot: BaseBot
    ) -> None:
        """Increment and display counter using cached storage."""
        if not self.storage:
            await self.send_reply(message, "❌ Storage is not enabled!")
            return

        # Use cached storage to minimize database round-trips
        async with self.storage.cached(["counter", "total_messages"]) as cache:
            counter = cache.get("counter", 0)
            total = cache.get("total_messages", 0)

            counter += 1
            total += 1

            cache.put("counter", counter)
            cache.put("total_messages", total)
            # Changes are automatically flushed on exit

        await self.send_reply(
            message, f"🔢 Count: **{counter}** (Total messages: {total})"
        )

    async def _handle_reset(
        self, invocation: CommandInvocation, message: Message, bot: BaseBot
    ) -> None:
        """Reset counter to zero."""
        if not self.storage:
            await self.send_reply(message, "❌ Storage is not enabled!")
            return

        await self.storage.put("counter", 0)
        await self.send_reply(message, "✅ Counter reset to 0")

    async def _handle_stats(
        self, invocation: CommandInvocation, message: Message, bot: BaseBot
    ) -> None:
        """Show detailed statistics."""
        if not self.storage:
            await self.send_reply(message, "❌ Storage is not enabled!")
            return

        async with self.storage.cached(["counter", "total_messages"]) as cache:
            counter = cache.get("counter", 0)
            total = cache.get("total_messages", 0)

        all_keys = await self.storage.keys()

        stats = (
            "📊 **Statistics**\n\n"
            f"Current counter: **{counter}**\n"
            f"Total messages: **{total}**\n"
            f"Available keys: {', '.join(all_keys) or 'none'}"
        )

        await self.send_reply(message, stats)

    async def on_message(self, message: Message) -> None:
        """Handle non-command messages."""
        # Only respond to simple text, commands are handled automatically
        self.logger.debug(f"CounterBot received message: {message.content[:50]}")


# Factory function for main.py to discover
def create_bot(client, logger):
    return CounterBot(client, logger)


BOT_CLASS = CounterBot


__all__ = ["CounterBot", "BOT_CLASS", "create_bot"]
