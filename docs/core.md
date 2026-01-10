# Core Components

The core components of Bot SDK provide all the basic functionality needed to build Zulip bots.

## Overview

Bot SDK contains the following core components:

1. **[AsyncClient](async_client.md)** - Async Zulip API Client
2. **[BaseBot](base_bot.md)** - Bot base class providing event handling framework
3. **[BotRunner](bot_runner.md)** - Bot lifecycle manager

## Architecture

```
┌─────────────────────────────────────────────┐
│              Your Bot                        │
│         (extends BaseBot)                    │
│                                              │
│  - on_message()                              │
│  - Command handlers                          │
│  - Custom logic                              │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│            BaseBot                           │
│                                              │
│  - Event dispatching                         │
│  - Command parsing                           │
│  - Message replies                           │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│          AsyncClient                         │
│                                              │
│  - HTTP requests                             │
│  - Event polling                             │
│  - API wrapping                              │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Zulip Server                         │
└──────────────────────────────────────────────┘
```

## Component Relationships

### AsyncClient

Low-level HTTP client, responsible for:
- Communicating with Zulip server
- Handling authentication
- Managing long-polling connections
- Providing wrappers for all Zulip APIs

**Use cases**:
- Need to call Zulip API directly
- Building non-standard bot behavior
- Testing and debugging

**Example**:
```python
from bot_sdk import AsyncClient

async with AsyncClient() as client:
    profile = await client.get_profile()
    print(profile.full_name)
```

### BaseBot

Mid-level abstraction, responsible for:
- Receiving and dispatching events
- Parsing commands
- Providing convenient reply methods
- Managing bot state

**Use cases**:
- Building standard message handling bots
- Need command system
- Need event-driven architecture

**Example**:
```python
from bot_sdk import BaseBot, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message):
        await self.send_reply(message, "Hello!")
```

### BotRunner

Top-level manager, responsible for:
- Starting and stopping bots
- Managing lifecycle
- Handling event loop
- Supporting multiple bots

**Use cases**:
- Production deployment
- Need graceful shutdown
- Running multiple bots
- Complex startup logic

**Example**:
```python
from bot_sdk import BotRunner

async with BotRunner(lambda c: MyBot(c)) as runner:
    await runner.run_forever()
```

## Quick Start

### Simplest Bot

```python
from bot_sdk import BaseBot, Message, run_bot

class SimpleBot(BaseBot):
    async def on_message(self, message: Message):
        await self.send_reply(message, "Echo: " + message.content)

if __name__ == "__main__":
    run_bot(SimpleBot)
```

### Bot with Commands

```python
from bot_sdk import BaseBot, Message, CommandSpec, CommandArgument

class CommandBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.command_parser.register_spec(
            CommandSpec(
                name="hello",
                description="Say hello",
                handler=self.handle_hello
            )
        )
    
    async def handle_hello(self, invocation, message, bot):
        await self.send_reply(message, "Hello, World!")
    
    async def on_message(self, message: Message):
        await self.send_reply(message, "Use /help for commands")
```

## Learn More

- [AsyncClient Detailed Documentation](async_client.md)
- [BaseBot Detailed Documentation](base_bot.md)
- [BotRunner Detailed Documentation](bot_runner.md)
- [Command System](commands.md)
- [Data Models](models.md)
