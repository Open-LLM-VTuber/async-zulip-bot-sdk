# BotRunner API

`BotRunner` manages the lifecycle of a bot: start, run, stop.

## Class: BotRunner

```python
from bot_sdk import BotRunner
```

### Init

```python
runner = BotRunner(
    bot_factory: Callable[[AsyncClient], BaseBot],
    *,
    event_types: list[str] | None = None,
    narrow: list[list[str]] | None = None,
    client_kwargs: dict[str, Any] | None = None,
)
```

#### Parameters

- **bot_factory**: Callable that returns a `BaseBot` when given an `AsyncClient`.
- **event_types**: Event types to listen for (default `["message"]`; configurable via `event_types` in `bots.yaml`).
- **narrow**: Zulip narrow filters.
- **client_kwargs**: Arguments forwarded to `AsyncClient`.

## Methods

- **start()**: Create client, build bot, `post_init`, open session, `on_start`.
- **stop()**: Call `on_stop`, cancel long-poll, close client.
- **run_forever()**: Poll events and dispatch indefinitely.

## Context manager

```python
async with BotRunner(lambda c: MyBot(c)) as runner:
    await runner.run_forever()
```

## Helper: run_bot

```python
from bot_sdk import run_bot

run_bot(
    bot_cls: type[BaseBot],
    *,
    event_types: list[str] | None = None,
    narrow: list[list[str]] | None = None,
    client_kwargs: dict[str, Any] | None = None,
)
```

## Usage patterns

- **Simple**: `run_bot(MyBot)`.
- **Manual**: call `start()`, `run_forever()`, `stop()` with try/finally.
- **Multiple bots**: create multiple runners and `asyncio.gather` their `run_forever()` calls.
- **From config**: load YAML, dynamically import bot classes, build runners with per-bot `zuliprc`.

## Event filtering (narrow)

Examples:

```python
# Single stream
runner = BotRunner(lambda c: MyBot(c), narrow=[["stream", "general"]])

# Private messages only
runner = BotRunner(lambda c: MyBot(c), narrow=[["is", "private"]])

# Stream + topic
runner = BotRunner(
    lambda c: MyBot(c),
    narrow=[["stream", "general"], ["topic", "bot-testing"]]
)
```

## Configure client

```python
runner = BotRunner(
    lambda c: MyBot(c),
    client_kwargs={
        "config_file": "~/.zuliprc",
        "verbose": True,
        "retry_on_errors": True,
    },
)

# Or pass credentials directly
runner = BotRunner(
    lambda c: MyBot(c),
    client_kwargs={
        "email": "bot@example.com",
        "api_key": "your-api-key",
        "site": "https://zulip.example.com",
    },
)
```

## Production example

```python
import asyncio
import signal
from bot_sdk import BotRunner, BaseBot, Message
from loguru import logger

class ProductionBot(BaseBot):
    async def on_start(self):
        logger.info("Bot started")

    async def on_stop(self):
        logger.info("Bot stopping")

    async def on_message(self, message: Message):
        try:
            await self.send_reply(message, "Hello!")
        except Exception as e:
            logger.error(f"Error: {e}")

async def main():
    runner = BotRunner(lambda c: ProductionBot(c))
    async with runner:
        await runner.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
```
