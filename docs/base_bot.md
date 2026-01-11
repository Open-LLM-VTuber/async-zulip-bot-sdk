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
- `perm`: manage permissions (bot owner, role levels, allow/deny stop); requires `min_level=200` (bot_owner).
- `reload`: reload bot.yaml settings and i18n translations without restart; requires `min_level=50` (admin).
- `stop`: request a graceful BotRunner shutdown (permission-checked); requires `min_level=50` (admin).

Permission enforcement: if a `CommandSpec` has `min_level`, BaseBot checks it before dispatch. Early permission denial is returned before argument parsing, so users see "Permission denied" rather than "Missing argument".

Built-in commands use i18n, so descriptions and success/error messages are localized based on the bot's configured language.

## Instance attributes
- **client**: The `AsyncClient` instance.
- **command_parser**: The `CommandParser` instance.
- **language**: Current language code (e.g., `"en"`, `"zh"`). Loaded from bot settings and used by i18n.
- **i18n**: Optional `I18n` instance for translating user-facing strings. Initialized during `post_init()`.
- **settings**: The `BotLocalConfig` instance (per-bot YAML configuration).

## Lifecycle hooks

- **post_init()**: Runs after creation. Steps:
  1. Initialize storage (KV backend)
  2. Initialize ORM engine (if enabled)
  3. Load per-bot settings from `bot.yaml`
  4. Initialize i18n (language and translations)
  5. Fetch and cache bot profile
  6. Set presence to "active"
  7. Register built-in and custom commands
  
- **on_start()**: Runs after startup (before entering the event loop).
- **on_stop()**: Runs before shutdown. Default: persist settings, dispose ORM engine.

## Event handling

- **on_event(event)**: Default handler. Parses commands, enforces `min_level` if present, then dispatches; otherwise calls `on_message()`.
- **on_message(message)**: **Must implement**. Handle non-command messages.
- **on_command(command, message)**: Legacy hook; prefer per-command handlers.

## Commands

- **parse_command(message)** → `CommandInvocation | None`: Parse message as command.
- **command_parser.dispatch(...)**: Dispatch to a registered handler.
- **tr(key, **kwargs)** → str: Translate a user-facing string using the bot's i18n system. Falls back to the key itself if i18n is not initialized or a translation is not found. Use this in custom command handlers and messages to enable multi-language support.

## Internationalization (i18n)

BaseBot automatically initializes an i18n system during `post_init()`:

- **language** is read from `bot.yaml` (field `language`, default `"en"`)
- Translations are loaded from:
  - `<bot_module_dir>/i18n/{language}.json` (bot-specific overrides)
  - `bot_sdk/i18n/{language}.json` (SDK defaults; fallback to English)
- Built-in commands (whoami, perm, stop, reload) use `self.tr()` for all user-visible strings
- Custom commands should also use `self.tr()` for multi-language support

**Example**:

```python
class MyBot(BaseBot):
    def register_commands(self):
        self.command_parser.register_spec(
            CommandSpec(
                name="greet",
                description=self.tr("Greet the user"),  # Translatable at registration time
                handler=self.handle_greet,
            )
        )
    
    async def handle_greet(self, inv, message, bot):
        # User-facing strings are translated
        await self.send_reply(message, self.tr("Hello, {name}!", name=message.sender_full_name))
```

See [docs/i18n.md](i18n.md) (if available) for detailed i18n setup and per-bot translation files.

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
