import asyncio

from loguru import logger
from zulip_bot_sdk import BaseBot, BotRunner, setup_logging, Message


class EchoBot(BaseBot):
    async def on_start(self):
        response = await self.client.get_profile()
        self._user_id = response.user_id
        logger.info("EchoBot started as user: {}", self._user_id)
    
    async def on_message(self, message):
        if message.sender_id == self._user_id:
            return  # Ignore messages from ourselves
        await self.send_reply(message, f"Echo: {message.content}")


def main():
    setup_logging("DEBUG")
    runner = BotRunner(lambda client: EchoBot(client), client_kwargs={"config_file": "zuliprc"})

    async def _run():
        async with runner:
            await runner.run_forever()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
