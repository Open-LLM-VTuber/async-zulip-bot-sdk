# Command System API

The SDK provides a flexible command parsing and dispatch system.

## CommandParser

Parses commands from messages by prefix or @-mention.

### Class: CommandParser

```python
from bot_sdk import CommandParser
```

#### Init

```python
parser = CommandParser(
    prefixes=("/", "!"),
    *,
    enable_mentions: bool = True,
    mention_aliases: Iterable[str] | None = None,
    specs: Iterable[CommandSpec] | None = None,
    auto_help: bool = True,
    translator: Callable[[str], str] | None = None,
)
```

**Parameters**

- **prefixes**: Command prefixes.
- **enable_mentions**: Use @-mentions as triggers.
- **mention_aliases**: Extra mention aliases.
- **specs**: Initial command specs.
- **auto_help**: Auto add `help` command.
- **translator**: Optional function for translating static help strings (e.g., `lambda s: bot.tr(s)`). Used to localize command descriptions, help text labels, and error messages.

**Example**

```python
parser = CommandParser(prefixes=("/", "!", "#"), enable_mentions=True)
```

### Methods

- **register_spec(spec)**: Register a `CommandSpec`.
- **parse_message(message)** → `CommandInvocation | None`.
- **parse_text(text)** → `CommandInvocation` (raises on errors; usage and error messages are localized if a translator is provided).
- **dispatch(invocation, message, bot)**: Call handler (awaits if coroutine).
- **find_command_spec(text)** → `CommandSpec | None`: Lightweight lookup of which command would be invoked by raw text, without parsing arguments or raising errors. Used for early permission checks.
- **generate_help(user_level=None)** → str: Auto build help overview.
  - If `user_level` is provided, commands with `min_level > user_level` are hidden from the output.
  - All descriptions and labels are translated via the translator function if provided.
- **Built-in help command**: Enabled by default. Usage:
    - `!help` — list all commands (filtered by caller's permission level)
    - `!help <command>` — show detailed usage, argument descriptions, aliases, min_level (if set)
- **add_identity_aliases(full_name=None, email=None, extra=None)**: Add mention aliases for the bot identity.

## CommandSpec

Defines a command.

```python
from bot_sdk import CommandSpec

CommandSpec(
    name: str,
    description: str = "",
    args: list[CommandArgument] = [],
    aliases: list[str] = [],
    allow_extra: bool = False,
    handler: Callable | None = None,
    show_in_help: bool = True,
    min_level: int | None = None,
)
```

### Fields

- **name**: Command name.
- **description**: Short description.
- **args**: List of `CommandArgument`.
- **aliases**: Alternate names.
- **allow_extra**: Allow extra tokens.
- **handler**: Callable `(invocation, message, bot)`.
- **show_in_help**: Show in generated help.
- **min_level**: Optional minimum permission level; enforced by `BaseBot` before dispatch.

### Examples

- **Simple**: `ping` → `Pong!`
- **With args**: `calculate a b`
- **With aliases**: `status` aliased to `s`, `info`, `stat`
- **Variadic**: `echo words...` with `multiple=True`
- **Optional arg**: `greet [name]`

## CommandArgument

Defines an argument.

```python
CommandArgument(
    name: str,
    type: type = str,
    required: bool = True,
    description: str = "",
    multiple: bool = False,
)
```

- **name**: Argument name.
- **type**: `str | int | float | bool`.
- **required**: Is required.
- **description**: Help text.
- **multiple**: Capture remaining tokens as list.

Argument `description` is surfaced in `!help <command>` detailed output.

Boolean parsing accepts: `true/1/yes/y/on` and `false/0/no/n/off`.

## CommandInvocation

Result of parsing.

```python
@dataclass
class CommandInvocation:
    name: str
    args: dict[str, Any]
    tokens: list[str]
    spec: CommandSpec
```

## Exceptions

- `CommandError`
- `UnknownCommandError`
- `InvalidArgumentsError` (message includes Usage and error text for quick fixes; both are localized if a translator was provided)

## Internationalization (i18n)

When a `translator` function is provided to `CommandParser.__init__`, the following strings are localized:

- Command descriptions in help output
- Help UI labels ("Description", "Aliases", "Min level", "Args:", "required", "optional", "multiple")
- Error messages:
  - "Missing argument: {name}"
  - "Too many arguments"
  - "Usage: {usage}"
  - "Invalid value for {name}: {value}"
  - "Unknown command: {name}"
  - "You do not have permission to use command: {name}"

This allows the entire command system to respond in the user's language.

## Full example

```python
from bot_sdk import BaseBot, Message, CommandSpec, CommandArgument, CommandInvocation, run_bot

class CalculatorBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.command_parser.register_spec(
            CommandSpec(
                name="add",
                description="Add two numbers",
                aliases=["plus", "+"],
                args=[
                    CommandArgument(name="a", type=float, required=True),
                    CommandArgument(name="b", type=float, required=True),
                ],
                handler=self.handle_add,
            )
        )
        self.command_parser.register_spec(
            CommandSpec(
                name="multiply",
                description="Multiply two numbers",
                aliases=["mul", "*"],
                args=[
                    CommandArgument(name="a", type=float, required=True),
                    CommandArgument(name="b", type=float, required=True),
                ],
                handler=self.handle_multiply,
            )
        )
        self.command_parser.register_spec(
            CommandSpec(
                name="power",
                description="a^b",
                aliases=["pow", "**"],
                args=[
                    CommandArgument(name="base", type=float, required=True),
                    CommandArgument(name="exponent", type=float, required=True),
                ],
                handler=self.handle_power,
            )
        )

    async def handle_add(self, inv: CommandInvocation, message, bot):
        await self.send_reply(message, f"{inv.args['a']} + {inv.args['b']} = {inv.args['a'] + inv.args['b']}")

    async def handle_multiply(self, inv: CommandInvocation, message, bot):
        await self.send_reply(message, f"{inv.args['a']} × {inv.args['b']} = {inv.args['a'] * inv.args['b']}")

    async def handle_power(self, inv: CommandInvocation, message, bot):
        await self.send_reply(message, f"{inv.args['base']} ^ {inv.args['exponent']} = {inv.args['base'] ** inv.args['exponent']}")

    async def on_message(self, message: Message) -> None:
        await self.send_reply(message, "I am a calculator bot. Use /help.")

if __name__ == "__main__":
    run_bot(CalculatorBot)
```

## Best practices

- Clear command names; add short aliases.
- Add helpful descriptions.
- Validate arguments inside handlers and return user-friendly errors.
- Keep variadic arguments (`multiple=True`) for free-form text.
- Use `generate_help()` to show available commands.
