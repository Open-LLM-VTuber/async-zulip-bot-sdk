# Logging

SDK logging utilities for system and bots.

The SDK uses [Loguru](https://github.com/Delgan/loguru) for logging and separates **system** logs from **bot** logs using tags and different sinks.

At a high level:

- System logs (SDK internals, console, HTTP client, etc.) are tagged as `SYSTEM` and written to `logs/system.log`.
- Each bot gets its own tagged logger and optional per-bot log file like `logs/echo_bot.log`.
- The interactive console shows a merged, colored view of all logs in the `Logs` panel.

## System logger setup

```python
from bot_sdk import setup_logging

# Call once at process start (e.g. in main.py)
setup_logging(level="INFO", json_logs=False)
```

### Parameters

- **level**: Log level (e.g. `DEBUG`, `INFO`, `WARNING`, `ERROR`).
- **json_logs**: When `True`, use a JSON formatter (useful for log ingestion); when `False`, use a human-readable colored format.

`setup_logging()` will:

- Ensure a `logs/` directory exists next to your project.
- Configure Loguru with a `SYSTEM` tag (`extra["bot_name"] = "SYSTEM"`).
- Add sinks for:
  - `stdout` (human-readable, colored output).
  - `logs/system.log` (plain text, one line per record, filtered to `bot_name == "SYSTEM"`).

## Bot loggers

Bots use their own tagged loggers so you can distinguish messages per bot and write to per-bot log files.

```python
from bot_sdk import get_bot_logger

bot_logger = get_bot_logger("echo_bot", level="INFO")

bot_logger.info("EchoBot starting up")
bot_logger.debug("Some internal state: {}", {"foo": 1})
```

### Behavior

- All bot loggers share the same global Loguru instance, but are bound with `extra["bot_name"] = <bot_name>`.
- Every bot can have its own file sink:
  - `logs/<bot_name>.log` when a name is provided (e.g. `logs/echo_bot.log`).
  - `logs/bots.log` as a shared fallback when no name is given.
- Console output still shows system and bot logs together, but with a visible tag prefix so you can see which bot produced which line.

In most cases you **don't need to call `get_bot_logger` manually**:

- When using `BaseBot` via the SDK (e.g. `BotRunner` or the interactive console), the framework creates a bot-specific logger and injects it into your bot instance.
- Inside a bot you can simply use `self.logger`:

```python
from bot_sdk import BaseBot, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message):
        self.logger.info("Received message from {}", message.sender_full_name)
        await self.send_reply(message, "Hello!")
```

## Console integration

When running the interactive console (`async-zulip-bot` / `main.py`):

- The `Logs` panel shows a live view of all Loguru output (system + all bots).
- Each line is prefixed with a tag (e.g. `SYSTEM`, `echo_bot`) so you can see log origin at a glance.
- Rich preserves ANSI colors and formatting for readability.
- PageUp/PageDown (and mouse wheel when supported) scroll through the log history; bot management commands are entered at the bottom prompt.

## Minimal examples

### Simple script with system logs

```python
from bot_sdk import setup_logging
from loguru import logger

if __name__ == "__main__":
    setup_logging(level="DEBUG")
    logger.info("SDK starting...")
    # Your startup logic here
```

### Bot using injected logger

```python
from bot_sdk import BaseBot, Message

class LoggingBot(BaseBot):
    async def on_start(self) -> None:
        self.logger.info("{} started", self.__class__.__name__)

    async def on_message(self, message: Message) -> None:
        self.logger.debug("Incoming message: {}", message.content[:50])
        await self.send_reply(message, "Got it!")
```

