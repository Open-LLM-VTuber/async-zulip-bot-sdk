import asyncio

from loguru import logger

from bot_sdk import (
    BaseBot,
    BotRunner,
    CommandArgument,
    CommandSpec,
    Message,
    UpdatePresenceRequest,
    CommandInvocation,
    setup_logging,
)

class Translator(BaseBot):

    command_prefixes = ("!",)

    def __init__(self, client):
        super().__init__(client)
        self.command_parser.register_spec(
            CommandSpec(
                name="echo",
                description="Echo back provided text",
                args=[CommandArgument("text", str, required=True, multiple=True)],
                handler=self._handle_echo,
            )
        )

    async def on_start(self):
        logger.info(f"{self.__class__.__name__} started with user_id: {self._user_id}")
        await self.client.update_presence(
            UpdatePresenceRequest(
                status="active",
            )
        )
        logger.info("Set presence to active")
        subs = await self.client.get_subscriptions()
        self._subscribed_streams = subs.subscriptions
        for stream in self._subscribed_streams:
            logger.info(f"Subscribed stream: {stream.stream_id} - {stream.name}")

    async def _handle_echo(self, invocation: CommandInvocation, message: Message, bot: BaseBot):
        text_parts = invocation.args.get("text") or []
        payload = " ".join(text_parts) if isinstance(text_parts, list) else str(text_parts)
        await self.send_reply(message, payload)
    
    async def on_message(self, message: Message):
        logger.debug("Sending echo reply")
        await self.send_reply(message, f"Echo: {message.content}")


def main():
    setup_logging("DEBUG")
    runner = BotRunner(
        lambda client: Translator(client),
        client_kwargs={"config_file": "zuliprc"},
        event_types=["message"],
    )

    async def _run():
        async with runner:
            await runner.run_forever()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
