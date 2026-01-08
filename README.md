<div align="center">

# 🤖 Zulip Bot SDK

**Async, type-safe Zulip bot development framework**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](README.md) | [中文](README.zh-CN.md)

---

</div>


### 📦 Installation

1. Clone the repository

```bash
git clone https://github.com/Open-LLM-VTuber/zulip-bots
cd zulip-bots
```

2. Install in a virtual environment (recommended)

```bash
# Using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .
```

### 🚀 Quick Start

#### 1. Configure Zulip Credentials

Download your `zuliprc` file:

You can create or regenerate your API Key in `Settings - Personal - Account & privacy`, enter your password, and select `Download zuliprc`. Place the file in your project directory.

#### 2. Create Your First Bot

```python
import asyncio

from bot_sdk import (
    BaseBot,
    BotRunner,
    Message,
    CommandSpec,
    CommandArgument,
    setup_logging
)

class MyBot(BaseBot):
    command_prefixes = ("!", "/")  # Command prefixes
    
    def __init__(self, client):
        super().__init__(client)
        # Register commands
        self.command_parser.register_spec(
            CommandSpec(
                name="echo",
                description="Echo back the provided text",
                args=[CommandArgument("text", str, required=True, multiple=True)],
                handler=self.handle_echo,
            )
        )
    
    async def on_start(self):
        """Called when bot starts"""
        print(f"Bot started! User ID: {self._user_id}")
    
    async def handle_echo(self, invocation, message, bot):
        """Handle echo command"""
        text = " ".join(invocation.args.get("text", []))
        await self.send_reply(message, f"Echo: {text}")
    
    async def on_message(self, message: Message):
        """Handle non-command messages"""
        await self.send_reply(message, "Try !help to see available commands!")

def main():
    setup_logging("INFO")
    runner = BotRunner(
        lambda client: MyBot(client),
        client_kwargs={"config_file": "zuliprc"}
    )
    
    async def run():
        async with runner:
            await runner.run_forever()
    
    asyncio.run(run())

if __name__ == "__main__":
    main()
```

#### 3. Run Your Bot

```bash
python main.py
```

### 📚 Core Concepts

#### AsyncClient

Fully async Zulip API client mirroring the official `zulip.Client` interface:

```python
from bot_sdk import AsyncClient

async with AsyncClient(config_file="zuliprc") as client:
    # Get user profile
    profile = await client.get_profile()
    
    # Send messages
    await client.send_message({
        "type": "stream",
        "to": "general",
        "topic": "Hello",
        "content": "Hello, world!"
    })
    
    # Get subscriptions
    subs = await client.get_subscriptions()
```

#### Command System

Type-safe command definitions with automatic validation:

```python
from bot_sdk import CommandSpec, CommandArgument

# Define commands with arguments
self.command_parser.register_spec(
    CommandSpec(
        name="greet",
        description="Greet a user",
        args=[
            CommandArgument("name", str, required=True),
            CommandArgument("times", int, required=False),
        ],
        handler=self.handle_greet,
    )
)

async def handle_greet(self, invocation, message, bot):
    name = invocation.args["name"]
    times = invocation.args.get("times", 1)
    greeting = f"Hello, {name}! " * times
    await self.send_reply(message, greeting)
```

**Auto-generated help:**

Use `!help` or `!?` to automatically show all registered commands and arguments.

#### Lifecycle Hooks

```python
class MyBot(BaseBot):
    async def on_start(self):
        """Called when bot starts"""
        pass
    
    async def on_stop(self):
        """Called when bot stops"""
        pass
    
    async def on_message(self, message: Message):
        """Called for non-command messages"""
        pass
```

### 🔧 Advanced Usage

#### Custom Command Prefixes and Mention Detection

```python
class MyBot(BaseBot):
    command_prefixes = ("!", "/", ".")
    enable_mention_commands = True  # Enable @bot to trigger commands
```

#### Typed Message Models

```python
from bot_sdk import Message, StreamMessageRequest

async def on_message(self, message: Message):
    # Full type hints
    sender = message.sender_full_name
    content = message.content
    
    # Send typed messages
    await self.client.send_message(
        StreamMessageRequest(
            to=message.stream_id,
            topic="Reply",
            content="Typed reply!"
        )
    )
```

#### Error Handling

```python
from bot_sdk import CommandError, UnknownCommandError, InvalidArgumentsError

# Command parsing and dispatch automatically handle errors
# and send friendly error messages to users
```

### 📖 API Reference

#### BaseBot

- `command_prefixes: tuple[str, ...]` — Command prefixes (default: `("!",)`)
- `enable_mention_commands: bool` — Enable @mention triggers (default: `True`)
- `auto_help_command: bool` — Auto-register help command (default: `True`)
- `async on_start()` — Startup hook
- `async on_stop()` — Shutdown hook
- `async on_message(message)` — Message handler hook
- `async send_reply(message, content)` — Reply utility method

#### CommandSpec

- `name: str` — Command name
- `description: str` — Command description
- `args: List[CommandArgument]` — Argument definitions
- `aliases: List[str]` — Command aliases
- `handler: Callable` — Handler function
- `show_in_help: bool` — Show in help (default: `True`)

#### CommandArgument

- `name: str` — Argument name
- `type: type` — Argument type (`str`, `int`, `float`, `bool`)
- `required: bool` — Whether required (default: `True`)
- `description: str` — Argument description
- `multiple: bool` — Capture remaining args (default: `False`)

### 🤝 Contributing

Contributions are welcome! Feel free to submit Pull Requests.

### 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

<div align="center">

Made with ❤️ for the Open-LLM-VTuber Zulip team

</div>