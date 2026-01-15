<div align="center">

# 🤖 Async Zulip Bot SDK

**Async, type-safe Zulip bot development framework**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/Open-LLM-VTuber/async-zulip-bot-sdk)](https://github.com/Open-LLM-VTuber/async-zulip-bot-sdk/releases)

[English](README.md) | [中文](README.zh-CN.md)

---

</div>

### ✨ Features

- 🚀 **Async-First** — Built on `httpx.AsyncClient` for high-performance async operations, fully compatible with official `zulip.Client` interface
- 📝 **Type-Safe** — Complete type hints and automatic validation with Pydantic v2 models
- 🎯 **Command System** — Powerful built-in command parser with type checking, argument validation, and auto-generated help
- 💾 **Flexible Storage** — Choose between lightweight JSON storage or full SQLAlchemy ORM with Alembic migrations
- 🌐 **Internationalization** — Built-in i18n support with JSON-based translation files
- 🔧 **YAML Configuration** — Single source of truth for bot settings in `bot.yaml`
- 🖥️ **Interactive Console** — Beautiful Rich-based TUI for managing multiple bots with live logs and command history
- 📦 **Production-Ready** — Long-polling event loop, automatic reconnection, and error recovery built-in

### 📦 Installation

From version **v0.2.0** and later, the SDK is published to **PyPI** via an
automated GitHub Actions workflow whenever a GitHub release is created.

#### Option 1: Install from PyPI (recommended for users)

```bash
# Using uv (recommended)
uv pip install async-zulip-bot-sdk

# Or using pip directly
pip install async-zulip-bot-sdk
```

#### Option 2: Install from source (for development)

```bash
git clone https://github.com/Open-LLM-VTuber/async-zulip-bot-sdk.git
cd async-zulip-bot-sdk

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

> ⚠️ Breaking change (since v1.0.0): bot configuration now lives in each bot's `bot.yaml`. Class-level attributes (e.g., `command_prefixes`, `enable_storage`, `enable_orm`) are ignored.
> Set prefixes/mention/help/storage/ORM options in the bot's YAML instead of subclass attributes.

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

#### 3. Configure per-bot settings (bot.yaml)

Create `bots/echo_bot/bot.yaml` to set prefixes/mentions/help/storage/ORM:

```yaml
command_prefixes:
- "!"
enable_mention_commands: true
auto_help_command: true
enable_storage: true
# storage_path: bot_data/echo_bot.db
enable_orm: false
# orm_db_path: bot_data/echo_bot.sqlite
language: en
```

#### 4. Create Your First Bot

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
    def __init__(self, client):
        super().__init__(client)
        # Register commands (prefixes come from bot.yaml)
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

#### 5. Run Your Bots

You can use this SDK in **your own project directory** (not necessarily this repo). A typical layout looks like:

```text
my-zulip-bots/
    bots.yaml
    bots/
        echo_bot/
            __init__.py
            bot.yaml
            zuliprc
```

**Interactive Console**

The SDK comes with a built-in interactive console for managing bots, featuring a TUI (Text User Interface) powered by `rich`.

**Run the console (recommended)**:
```bash
# Activate your virtual environment first
# .venv\Scripts\activate  # Windows
# source .venv/bin/activate  # macOS/Linux

async-zulip-bot               # runs in the current project directory
```

This command looks for `bots.yaml` and the `bots/` package in the **current working directory**, so run it from your own project root.

**Features:**
- **Rich TUI**: Beautiful, split-screen layout for logs, status, and input.
- **Command History**: Use `Up`/`Down` arrows to navigate previous commands.
- **Log Scrolling**: Use `PageUp`/`PageDown` to scroll through logs.
- **Bot Management**: Run, stop, and reload bots dynamically.
- **Tab Completion**: Press `Tab` to auto-complete commands and bot names.


After entering the interactive console, use the `run` command to start your bot:

```
bot-console> run echo_bot
```

Remember to use tab completion for faster typing!

For more commands, type `help` in the console.

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

Configuration for prefixes and mention commands is now read from `bot.yaml` (per-bot YAML config). Class-level attributes are ignored.

```yaml
command_prefixes:
- "!"
- "/" # Not recommended as '/' is zulip official command prefix
enable_mention_commands: true  # Enable @bot to trigger commands
auto_help_command: true        # Auto-register built-in help command
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

- **Online Docs** (hosted): https://docs.llmvtuber.com/async-zulip-bot-sdk/
- **Source Docs** (in this repo): see the `docs/` directory (build with `mkdocs serve`)

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