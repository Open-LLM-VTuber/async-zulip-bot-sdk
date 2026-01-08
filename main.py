import asyncio

from loguru import logger
from zulip_bot_sdk import BaseBot, BotRunner, setup_logging, UpdatePresenceRequest


class Translator(BaseBot):
    async def on_start(self):
        response = await self.client.get_profile()
        self._user_id = response.user_id
        logger.info(f"{self.__class__.__name__} started with user_id: {self._user_id}")
        await self.client.update_presence(
            UpdatePresenceRequest(
                status="active",
            )
        )
        logger.info("Set presence to active")
        self._subscribed_streams = await self.client.get_subscriptions()
        for stream in self._subscribed_streams.subscriptions:
            logger.info(f"Subscribed stream: {stream.stream_id} - {stream.name}")
    
    async def on_message(self, message):
        if message.sender_id == self._user_id:
            return  # Ignore messages from ourselves
        await self.send_reply(message, f"Echo: {message.content}")
        


def main():
    setup_logging("DEBUG")
    runner = BotRunner(lambda client: Translator(client), client_kwargs={"config_file": "zuliprc"})

    async def _run():
        async with runner:
            await runner.run_forever()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
