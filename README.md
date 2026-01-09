<div align="center">

# 🤖 Async Zulip Bot SDK

**Async, type-safe Zulip bot development framework**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](README.md) | [中文](README.zh-CN.md)

---

</div>


### 📦 Installation

1. Clone the repository

```bash
git clone https://github.com/Open-LLM-VTuber/async-zulip-bot-sdk.git
cd async-zulip-bot-sdk
```

2. Install in a virtual environment (recommended)

```bash
# Using uv (recommended)
uv venv
uv pip install -e .

# Or using venv + pip
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -e .
```

### 🚀 Quick Start

#### 1. Configure Zulip Credentials

Download your `zuliprc` file:

You can create or regenerate your API Key in `Settings - Personal - Account & privacy`, enter your password, and select `Download zuliprc`. Place each bot's file under its own folder, e.g. `bots/echo_bot/zuliprc`.

#### 2. Configure bots.yaml

Create a `bots.yaml` file at the root of project, you can refer to `bots.yaml.example` for details.
Define which bots to launch and where to find them:

```yaml
bots:
  - name: echo_bot
    module: bots.echo_bot
    class_name: BOT_CLASS
    enabled: true
    # Optional override; defaults to bots/<name>/zuliprc
    # zuliprc: bots/echo_bot/zuliprc
    config: {}  # optional per-bot config passed to factory (second arg)
```

#### 3. Create Your First Bot

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

BOT_CLASS = MyBot
```

Remember to save this code in a `__init__.py` file under the directory your configured in `bots.yaml`.
In this example, you would save it as `bots/echo_bot/__init__.py`.

#### 4. Run Your Bots

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

---

## 📚 Documentation

Comprehensive API documentation is available:

- **File Docs**: [/docs/en](/docs/en/)

Documentation includes:
- 📖 Quick Start Guide
- 🔧 API Reference (AsyncClient, BaseBot, BotRunner)
- 💬 Command System
- 📊 Data Models
- ⚙️ Configuration Management
- 📝 Logging

---

### 🤝 Contributing

Contributions are welcome! Feel free to submit Pull Requests.

**Contributing Documentation**: We welcome documentation contributions in both Chinese and English.

### 🙏 Credits & Notices

- Portions of [bot_sdk/async_zulip.py](bot_sdk/async_zulip.py) are adapted from the Zulip upstream client at https://github.com/zulip/python-zulip-api/blob/main/zulip/zulip/__init__.py.
- The upstream project is licensed under Apache-2.0; the original license notice is preserved in the source, and the full text is included as [Apache2.0.LICENSE](Apache2.0.LICENSE).
- Huge thanks to the Zulip team for their great work and open-source contributions.

### 📄 License

MIT License - see [LICENSE](LICENSE) file for details

---

<div align="center">

Made with ❤️ for the Open-LLM-VTuber Zulip team

</div>