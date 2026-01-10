# BaseBot API

`BaseBot` is the base class for all Zulip bots. It handles message dispatch, command parsing, and replies.

## Class: BaseBot

```python
from bot_sdk import BaseBot
```

### Inherit and implement

```python
from bot_sdk import BaseBot, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        await self.send_reply(message, "Received!")
```

## Class attributes
- **command_prefixes**: Default (`"/", "!"`). Prefixes that trigger commands.
- **enable_mention_commands**: Treat @-mentions as commands (default `True`).
- **auto_help_command**: Auto-register built-in help command (default `True`).

Built-ins registered by default:
- `whoami`: show caller roles/level.
- `perm`: manage permissions (bot owner, role levels, allow/deny stop).
- `stop`: request a graceful BotRunner shutdown (permission-checked).

Permission enforcement: if a `CommandSpec` has `min_level`, BaseBot checks it before dispatch; `perm/stop` include built-in limits.

## Instance attributes
- **client**: The `AsyncClient` instance.
- **command_parser**: The `CommandParser` instance.

## Lifecycle hooks

- **post_init()**: Runs after creation. Default: fetch profile, add identity aliases, set presence to "active".
- **on_start()**: Runs after startup.
- **on_stop()**: Runs before shutdown.

## Event handling

- **on_event(event)**: Default handler. Parses commands, enforces `min_level` if present, then dispatches; otherwise calls `on_message()`.
- **on_message(message)**: **Must implement**. Handle non-command messages.
- **on_command(command, message)**: Legacy hook; prefer per-command handlers.

## Commands

- **parse_command(message)** → `CommandInvocation | None`: Parse message as command.
- **command_parser.dispatch(...)**: Dispatch to a registered handler.

## Reply helper

- **send_reply(original, content)**: Reply to stream or private message automatically.

## Examples

### Simple bot

```python
from bot_sdk import BaseBot, Message, run_bot

class SimpleBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        await self.send_reply(message, f"Echo: {message.content}")

if __name__ == "__main__":
    run_bot(SimpleBot)
```

### Command bot

```python
from bot_sdk import BaseBot, Message, CommandSpec, CommandArgument

class TodoBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.todos = []
        self.command_parser.register_spec(
            CommandSpec(
                name="add",
                description="Add todo",
                args=[CommandArgument(name="task", type=str, multiple=True)],
                handler=self.handle_add,
            )
        )
        self.command_parser.register_spec(
            CommandSpec(name="list", description="List todos", handler=self.handle_list)
        )
        self.command_parser.register_spec(
            CommandSpec(
                name="done",
                description="Mark done",
                args=[CommandArgument(name="index", type=int, required=True)],
                handler=self.handle_done,
            )
        )

    async def handle_add(self, invocation, message, bot):
        task = " ".join(invocation.args["task"])
        self.todos.append(task)
        await self.send_reply(message, f"✅ Added: {task}")

    async def handle_list(self, invocation, message, bot):
        if not self.todos:
            await self.send_reply(message, "No todos")
            return
        lines = [f"{i+1}. {task}" for i, task in enumerate(self.todos)]
        await self.send_reply(message, "\n".join(lines))

    async def handle_done(self, invocation, message, bot):
        idx = invocation.args["index"] - 1
        if 0 <= idx < len(self.todos):
            task = self.todos.pop(idx)
            await self.send_reply(message, f"✅ Done: {task}")
        else:
            await self.send_reply(message, "❌ Invalid index")

    async def on_message(self, message: Message) -> None:
        await self.send_reply(message, "Use /help to see commands")
```

## Best practices

- Call `super()` when overriding lifecycle hooks.
- Catch exceptions inside `on_message` / handlers and report user-friendly errors.
- Store state on the bot instance.
- Use commands for complex flows.
- Log important events with `loguru`.
