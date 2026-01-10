# Async Zulip Bot SDK API Documentation

Welcome to the API documentation for Async Zulip Bot SDK. This documentation provides detailed information about all core components of the SDK.

## Table of Contents

- [Quick Start](quickstart.md)
- [Core Components](core.md)
  - [AsyncClient](async_client.md) - Async Zulip API Client
  - [BaseBot](base_bot.md) - Bot Base Class
  - [BotRunner](bot_runner.md) - Bot Runner
- [Command System](commands.md)
  - [CommandParser](commands.md#commandparser) - Command Parser
  - [CommandSpec](commands.md#commandspec) - Command Specification
  - [CommandArgument](commands.md#commandargument) - Command Arguments
- [Data Models](models.md)
  - [Request Types](models.md#request-types)
  - [Response Types](models.md#response-types)
  - [Data Types](models.md#data-types)
- [Configuration](config.md)
- [Logging](logging.md)

## Introduction

Async Zulip Bot SDK is an asynchronous Zulip bot development framework based on Python asyncio. It provides:

- 🚀 Fully asynchronous API client
- 🤖 Easy-to-use Bot base class
- 📝 Powerful command parsing system
- 🔧 Flexible configuration management
- 📊 Type-safe data models

## Installation

```bash
pip install async-zulip-bot-sdk
```

## Quick Example

```python
from bot_sdk import BaseBot, BotRunner, AsyncClient, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        if "hello" in message.content.lower():
            await self.send_reply(message, "Hello! 👋")

if __name__ == "__main__":
    from bot_sdk import run_bot
    run_bot(MyBot)
```

## Version

Current version: 0.9.1-async

## License

This project is licensed under the MIT License.
