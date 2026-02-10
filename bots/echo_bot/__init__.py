from bot_sdk import BaseBot, CommandArgument, CommandInvocation, CommandSpec, Message


class EchoBot(BaseBot):
    def register_commands(self) -> None:
        self.command_parser.register_spec(
            CommandSpec(
                name="echo",
                description="Echo back provided text",
                args=[CommandArgument("text", str, required=True, multiple=True)],
                handler=self._handle_echo,
            )
        )

    async def _handle_echo(
        self, invocation: CommandInvocation, message: Message, bot: BaseBot
    ):
        text_parts = invocation.args.get("text") or []
        payload = (
            " ".join(text_parts) if isinstance(text_parts, list) else str(text_parts)
        )
        await self.send_reply(message, payload)

    async def on_message(self, message: Message):
        self.logger.debug("Sending echo reply")
        await self.send_reply(message, f"Echo: {message.content}")


BOT_CLASS = EchoBot


__all__ = ["EchoBot", "BOT_CLASS"]
