from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Sequence

from .models import Message


class CommandError(Exception):
    """Base command error."""


class UnknownCommandError(CommandError):
    pass


class InvalidArgumentsError(CommandError):
    def __init__(self, command: str, message: str) -> None:
        self.command = command
        super().__init__(message)


ArgType = str | int | float | bool


@dataclass
class CommandArgument:
    name: str
    type: type = str
    required: bool = True
    description: str = ""
    multiple: bool = False  # capture the remainder of args


@dataclass
class CommandSpec:
    name: str
    description: str = ""
    args: List[CommandArgument] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    allow_extra: bool = False
    handler: Optional[Callable[["CommandInvocation", Any, Any], Awaitable[None] | None]] = None
    show_in_help: bool = True


@dataclass
class CommandInvocation:
    name: str
    args: Dict[str, Any]
    tokens: List[str]
    spec: CommandSpec


class CommandParser:
    """Parses messages into command invocations using prefixes or @-mentions."""

    def __init__(
        self,
        prefixes: Sequence[str] = ("/", "!"),
        *,
        enable_mentions: bool = True,
        mention_aliases: Optional[Iterable[str]] = None,
        specs: Optional[Iterable[CommandSpec]] = None,
        auto_help: bool = True,
    ) -> None:
        self.prefixes = tuple(prefixes)
        self.enable_mentions = enable_mentions
        self.mention_aliases: List[str] = []
        if mention_aliases:
            self.set_mentions(mention_aliases)
        self.specs: Dict[str, CommandSpec] = {}
        self.alias_index: Dict[str, str] = {}
        if specs:
            for spec in specs:
                self.register_spec(spec)
        self.auto_help = auto_help
        if self.auto_help and "help" not in self.specs:
            self.register_spec(
                CommandSpec(
                    name="help",
                    description="Show available commands",
                    aliases=["?"],
                    handler=self._handle_help,
                )
            )

    def register_spec(self, spec: CommandSpec) -> None:
        self.specs[spec.name] = spec
        for alias in spec.aliases:
            self.alias_index[alias] = spec.name

    def set_mentions(self, aliases: Iterable[str]) -> None:
        self.mention_aliases = [alias.lower() for alias in aliases if alias]

    def add_identity_aliases(
        self,
        *,
        full_name: Optional[str] = None,
        email: Optional[str] = None,
        extra: Optional[Iterable[str]] = None,
    ) -> None:
        aliases: List[str] = []
        if full_name:
            aliases.extend([f"@**{full_name}**", f"@{full_name}"])
        if email:
            aliases.append(f"@{email}")
        if extra:
            aliases.extend(extra)
        self.mention_aliases.extend([a.lower() for a in aliases if a])

    def parse_message(self, message: Message) -> Optional[CommandInvocation]:
        text = (message.content or "").strip()
        if not text:
            return None
        stripped = self._strip_prefix_or_mention(text)
        if stripped is None:
            return None
        return self.parse_text(stripped)

    def parse_text(self, text: str) -> CommandInvocation:
        tokens = text.split()
        if not tokens:
            raise CommandError("Empty command")
        name_token = tokens[0].lower()
        command_name = self.alias_index.get(name_token, name_token)
        spec = self.specs.get(command_name)
        if spec is None:
            raise UnknownCommandError(f"Unknown command: {command_name}")
        parsed_args = self._parse_args(tokens[1:], spec)
        return CommandInvocation(name=spec.name, args=parsed_args, tokens=tokens, spec=spec)

    async def dispatch(self, invocation: CommandInvocation, *, message: Any, bot: Any) -> None:
        handler = invocation.spec.handler
        if handler is None:
            raise CommandError(f"No handler registered for command: {invocation.name}")
        result = handler(invocation, message, bot)
        if hasattr(result, "__await__"):
            await result

    def _strip_prefix_or_mention(self, text: str) -> Optional[str]:
        for prefix in self.prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()

        if self.enable_mentions and self.mention_aliases:
            lowered = text.lower()
            for alias in self.mention_aliases:
                if lowered.startswith(alias):
                    return text[len(alias):].lstrip(" :,-")
        return None

    def _parse_args(self, args_tokens: List[str], spec: CommandSpec) -> Dict[str, Any]:
        parsed: Dict[str, Any] = {}
        idx = 0
        for arg_spec in spec.args:
            if arg_spec.multiple:
                remaining = args_tokens[idx:]
                parsed[arg_spec.name] = [self._convert_value(token, arg_spec) for token in remaining]
                idx = len(args_tokens)
                break

            if idx >= len(args_tokens):
                if arg_spec.required:
                    raise InvalidArgumentsError(spec.name, f"Missing argument: {arg_spec.name}")
                parsed[arg_spec.name] = None
                continue

            parsed[arg_spec.name] = self._convert_value(args_tokens[idx], arg_spec)
            idx += 1

        if not spec.allow_extra and idx < len(args_tokens):
            raise InvalidArgumentsError(spec.name, "Too many arguments")
        return parsed

    def _convert_value(self, value: str, arg_spec: CommandArgument) -> ArgType:
        target = arg_spec.type
        try:
            if target is bool:
                return self._to_bool(value)
            return target(value)
        except Exception as exc:  # pragma: no cover - simple conversion guard
            raise InvalidArgumentsError(arg_spec.name, f"Invalid value for {arg_spec.name}: {value}") from exc

    @staticmethod
    def _to_bool(value: str) -> bool:
        lowered = value.lower()
        if lowered in {"true", "1", "yes", "y", "on"}:
            return True
        if lowered in {"false", "0", "no", "n", "off"}:
            return False
        raise ValueError(value)

    def generate_help(self) -> str:
        prefix = self.prefixes[0] if self.prefixes else ""
        lines: List[str] = []
        for spec in self.specs.values():
            if not spec.show_in_help:
                continue
            parts: List[str] = [f"{prefix}{spec.name}"]
            for arg in spec.args:
                label = arg.name
                if arg.multiple:
                    label += "..."
                if not arg.required:
                    label = f"[{label}]"
                else:
                    label = f"<{label}>"
                parts.append(label)
            summary = " ".join(parts)
            if spec.description:
                summary = f"{summary} — {spec.description}"
            lines.append(summary)
        return "\n".join(lines) if lines else "No commands registered."

    async def _handle_help(self, invocation: CommandInvocation, message: Any, bot: Any) -> None:
        # Default help handler: reply with generated help text.
        if hasattr(bot, "send_reply"):
            await bot.send_reply(message, self.generate_help())
        else:  # pragma: no cover - safety fallback
            raise CommandError("Help handler cannot reply without bot.send_reply")


__all__ = [
    "CommandParser",
    "CommandSpec",
    "CommandArgument",
    "CommandInvocation",
    "CommandError",
    "UnknownCommandError",
    "InvalidArgumentsError",
]
