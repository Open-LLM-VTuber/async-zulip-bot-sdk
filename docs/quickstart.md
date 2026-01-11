# Quick Start

This guide will help you quickly create and run your first Zulip bot.

## Prerequisites

- Python 3.8 or higher
- A Zulip account and API key

## Installation

```bash
pip install async-zulip-bot-sdk
```

## Configure Zulip Credentials

Create a `~/.zuliprc` file:

```ini
[api]
email=your-bot@example.com
key=your-api-key
site=https://your-zulip-server.com
```

## Create Your First Bot

### Option 1: Using the Interactive Console (Manages Multiple Bots)

The SDK includes a `main.py` entry point that launches a rich interactive console. This is the recommended way to develop and run bots, as it supports hot reloads and managing multiple bots.

> Breaking change: Bot configuration is now read from each bot's `bot.yaml`. Class-level attributes (e.g., `command_prefixes`, `enable_orm`) are ignored.

1. **Run the Manager**:
   ```bash
   python main.py
   ```
   
   The console supports:
   
   - **Command History**: `Up`/`Down` arrows.
   - **Log Scrolling**: `PageUp`/`PageDown`.
   - **Hot Reloading**: `reload <bot_name>` command.

### Option 2: Basic Echo Bot Script

Create `my_bot.py`:

```python
from bot_sdk import BaseBot, Message, run_bot

class EchoBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        """Echo received messages"""
        await self.send_reply(message, f"You said: {message.content}")

if __name__ == "__main__":
    run_bot(EchoBot)
```

Run:

```bash
python my_bot.py
```

### 2. Bot with Commands

```python
from bot_sdk import BaseBot, Message, CommandSpec, CommandArgument

class CommandBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        
        # Register commands
        self.command_parser.register_spec(
            CommandSpec(
                name="greet",
                description="Greet someone",
                args=[
                    CommandArgument(
                        name="name",
                        type=str,
                        required=True,
                        description="Name to greet"
                    )
                ],
                handler=self.handle_greet
            )
        )
    
    async def handle_greet(self, invocation, message, bot):
        """Handle greet command"""
        name = invocation.args["name"]
        await self.send_reply(message, f"Hello, {name}! 👋")
    
    async def on_message(self, message: Message) -> None:
        """Handle non-command messages"""
        await self.send_reply(message, "Use /help to see available commands")

if __name__ == "__main__":
    run_bot(CommandBot)
```

## Next Steps

- Check [BaseBot API](base_bot.md) to learn more about bot features
- Read [Command System](commands.md) to learn how to build complex commands
- Explore [AsyncClient API](async_client.md) to learn about all available Zulip APIs

## FAQ

### How to test the bot?

Test your bot on a test server or in a private channel.

### Bot not responding?

1. Check if `.zuliprc` configuration is correct
2. Confirm bot account has permission to access relevant channels
3. Check log output for error messages

### How to handle errors?

```python
from bot_sdk import BaseBot, Message
from loguru import logger

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        try:
            # Your logic
            await self.send_reply(message, "Processed successfully")
        except Exception as e:
            logger.error(f"Failed to process message: {e}")
            await self.send_reply(message, "Sorry, an error occurred!")
```
