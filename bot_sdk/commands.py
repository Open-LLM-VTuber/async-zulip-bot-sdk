from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Protocol, Sequence

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

_TRUE_SET = frozenset(("true", "1", "yes", "y", "on"))
_FALSE_SET = frozenset(("false", "0", "no", "n", "off"))


class SupportsSendReply(Protocol):
    async def send_reply(self, message: Any, content: str) -> Any:
        ...


class Validator(Protocol):
    """Callable validator that may coerce or reject a value."""

    def __call__(self, value: Any) -> Any:
        ...

    def help_hint(self) -> Optional[str]:  # optional, but recommended
        ...


class OptionValidator:
    """Ensure a value is one of the allowed options (useful for enums).

    By default the match is case-sensitive. Set ``case_insensitive`` to allow
    case-insensitive string comparison while still returning the original
    value.
    """

    def __init__(self, options: Iterable[Any], *, case_insensitive: bool = False) -> None:
        opts = list(options)
        if not opts:
            raise ValueError("options must not be empty")
        self.options = opts
        self.case_insensitive = case_insensitive
        if case_insensitive:
            self._normalized_map = {self._normalize(opt): opt for opt in opts}
        else:
            self._allowed = set(opts)

    def __call__(self, value: Any) -> Any:
        if self.case_insensitive and isinstance(value, str):
            normalized = self._normalize(value)
            if normalized in self._normalized_map:
                return self._normalized_map[normalized]
            self._raise_error(value)

        if not self.case_insensitive:
            if value in self._allowed:
                return value
            self._raise_error(value)

        # If case-insensitive but the value is not a string, fall back to direct membership.
        if value in self.options:
            return value
        self._raise_error(value)

    def _raise_error(self, value: Any) -> None:
        choices = ", ".join(str(opt) for opt in self.options)
        raise ValueError(f"Value must be one of: {choices} (got {value})")

    @staticmethod
    def _normalize(value: Any) -> str:
        return str(value).lower()

    def help_hint(self) -> str:
        choices = ", ".join(str(opt) for opt in self.options)
        suffix = " (case-insensitive)" if self.case_insensitive else ""
        return f"options: {choices}{suffix}"


@dataclass
class CommandArgument:
    name: str
    type: type = str
    required: bool = True
    description: str = ""
    multiple: bool = False  # capture the remainder of args
    validator: Optional[Validator] = None


@dataclass
class CommandSpec:
    name: str
    description: str = ""
    args: List[CommandArgument] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    allow_extra: bool = False
    handler: Optional[Callable[["CommandInvocation", Any, SupportsSendReply], Awaitable[None] | None]] = None
    show_in_help: bool = True
    # Minimum permission level required to execute this command (optional)
    min_level: Optional[int] = None


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
        translator: Optional[Callable[[str], str]] = None,
    ) -> None:
        self.prefixes = tuple(prefixes)
        self.enable_mentions = enable_mentions
        # Optional translator for built-in help strings; typically
        # this is BaseBot.tr or a similar function. It must accept
        # a single string key and return the translated string.
        self._translator: Optional[Callable[[str], str]] = translator
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
                    # Store the English key here and translate lazily
                    # when rendering help, so that i18n initialization
                    # order does not affect the final text.
                    description="Show available commands",
                    aliases=["?"],
                    args=[CommandArgument("command", str, required=False, description="Command name for detailed help")],
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

    def find_command_spec(self, text: str) -> Optional[CommandSpec]:
        """Return the CommandSpec for a raw message text, if any.

        This is a lightweight helper for callers that only need to know
        *which* command would be invoked (e.g., for permission checks)
        without fully parsing arguments or raising errors for unknown
        commands. It respects the same prefixes and @-mention rules as
        :meth:`parse_message`.
        """

        stripped = self._strip_prefix_or_mention(text)
        if stripped is None:
            return None
        tokens = stripped.split()
        if not tokens:
            return None
        name_token = tokens[0].lower()
        command_name = self.alias_index.get(name_token, name_token)
        return self.specs.get(command_name)

    async def dispatch(self, invocation: CommandInvocation, *, message: Any, bot: SupportsSendReply) -> None:
        handler = invocation.spec.handler
        if handler is None:
            raise CommandError(f"No handler registered for command: {invocation.name}")
        result = handler(invocation, message, bot)
        if hasattr(result, "__await__"):
            await result

    def _strip_prefix_or_mention(self, text: str) -> Optional[str]:
        # Fast path: prefix match
        for prefix in self.prefixes:
            if text.startswith(prefix):
                return text[len(prefix):].strip()

        # Mention-based trigger
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
                    usage = self._format_usage(spec)
                    msg = self._tr("Missing argument: {name}").format(name=arg_spec.name)
                    usage_line = self._tr("Usage: {usage}").format(usage=usage)
                    raise InvalidArgumentsError(spec.name, f"{msg}\n{usage_line}")
                parsed[arg_spec.name] = None
                continue

            parsed[arg_spec.name] = self._convert_value(args_tokens[idx], arg_spec)
            idx += 1

        if not spec.allow_extra and idx < len(args_tokens):
            usage = self._format_usage(spec)
            msg = self._tr("Too many arguments")
            usage_line = self._tr("Usage: {usage}").format(usage=usage)
            raise InvalidArgumentsError(spec.name, f"{msg}\n{usage_line}")
        return parsed

    def _convert_value(self, value: str, arg_spec: CommandArgument) -> ArgType:
        target = arg_spec.type
        try:
            converted: ArgType
            if target is bool:
                converted = self._to_bool(value)
            else:
                converted = target(value)

            if arg_spec.validator is not None:
                return arg_spec.validator(converted)
            return converted
        except InvalidArgumentsError:
            raise
        except Exception as exc:  # pragma: no cover - simple conversion guard
            template = self._tr("Invalid value for {name}: {value}")
            message = template.format(name=arg_spec.name, value=value)
            raise InvalidArgumentsError(arg_spec.name, message) from exc

    @staticmethod
    def _to_bool(value: str) -> bool:
        lowered = value.lower()
        if lowered in _TRUE_SET:
            return True
        if lowered in _FALSE_SET:
            return False
        raise ValueError(value)

    def _tr(self, text: str) -> str:
        """Translate a static help text if a translator was provided.

        This keeps CommandParser decoupled from any particular i18n
        system while still allowing SDK users (like BaseBot) to
        provide a translation function. Failures are quietly ignored
        so they don't pollute logs on startup or in edge cases.
        """

        if self._translator is None:
            return text
        try:
            return self._translator(text)
        except Exception:  # pragma: no cover - defensive fallback only
            return text

    def generate_help(self, *, user_level: Optional[int] = None) -> str:
        lines: List[str] = []
        for spec in self.specs.values():
            if not spec.show_in_help:
                continue
            # If a user level is provided and the command requires a higher
            # level, hide it from the help output to keep things simple.
            if user_level is not None and spec.min_level is not None and spec.min_level > user_level:
                continue
            summary = self._format_usage(spec)
            if spec.description:
                summary = f"{summary} — {self._tr(spec.description)}"
            lines.append(summary)
        return "\n".join(lines) if lines else "No commands registered."

    async def _handle_help(self, invocation: CommandInvocation, message: Any, bot: SupportsSendReply) -> None:
        # Default help handler: reply with generated help text.
        # Try to obtain the caller's permission level if the bot exposes it.
        user_level: Optional[int] = None
        sender_id = getattr(message, "sender_id", None)
        if sender_id is not None:
            level_getter = getattr(bot, "get_user_level", None)
            if callable(level_getter):
                try:
                    maybe_result = level_getter(sender_id)
                    if hasattr(maybe_result, "__await__"):
                        user_level = await maybe_result  # type: ignore[assignment]
                    else:
                        user_level = int(maybe_result)  # type: ignore[arg-type]
                except Exception:  # pragma: no cover - help should degrade gracefully
                    user_level = None

        target = invocation.args.get("command")
        if not target:
            await bot.send_reply(message, self.generate_help(user_level=user_level))
            return

        target_name = str(target).lower()
        spec_name = self.alias_index.get(target_name, target_name)
        spec = self.specs.get(spec_name)
        if not spec:
            # Try to use bot-level i18n if available.
            tr = getattr(bot, "tr", None)
            if callable(tr):
                await bot.send_reply(message, tr("Unknown command: {name}", name=str(target)))
            else:
                await bot.send_reply(message, f"Unknown command: {target}")
            return

        # If we know the user's level and the command requires a higher level,
        # do not reveal full details.
        if user_level is not None and spec.min_level is not None and user_level < spec.min_level:
            tr = getattr(bot, "tr", None)
            if callable(tr):
                await bot.send_reply(message, tr("You do not have permission to use command: {name}", name=spec.name))
            else:
                await bot.send_reply(message, f"You do not have permission to use command: {spec.name}")
            return

        detail = self._format_spec_detail(spec)
        await bot.send_reply(message, detail)

    def _format_usage(self, spec: CommandSpec) -> str:
        prefix = self.prefixes[0] if self.prefixes else ""
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
        return " ".join(parts)

    def _format_spec_detail(self, spec: CommandSpec) -> str:
        lines: List[str] = []
        lines.append(self._format_usage(spec))
        if spec.description:
            lines.append(f"{self._tr('Description')}: {self._tr(spec.description)}")
        if spec.aliases:
            lines.append(f"{self._tr('Aliases')}: {', '.join(spec.aliases)}")
        if spec.min_level is not None:
            lines.append(f"{self._tr('Min level')}: {spec.min_level}")
        if spec.args:
            lines.append(self._tr("Args:"))
            for arg in spec.args:
                requirement = self._tr("required") if arg.required else self._tr("optional")
                multi = f" ({self._tr('multiple')})" if arg.multiple else ""
                desc = f" - {arg.name}: {requirement}{multi}"
                validator_hint = self._format_validator_hint(arg.validator)
                if arg.description:
                    desc += f" — {arg.description}"
                if validator_hint:
                    desc += f" [{validator_hint}]"
                lines.append(desc)
        return "\n".join(lines)

    @staticmethod
    def _format_validator_hint(validator: Optional[Validator]) -> str:
        if validator is None:
            return ""
        hint_fn = getattr(validator, "help_hint", None)
        if callable(hint_fn):
            try:
                hint = hint_fn()
                return str(hint) if hint else ""
            except Exception:  # pragma: no cover - help rendering should not break help
                return ""
        # This is a developer-facing hint, not end-user text, so we
        # intentionally keep it simple and non-localized.
        return f"validated by {validator.__class__.__name__}"


__all__ = [
    "CommandParser",
    "CommandSpec",
    "CommandArgument",
    "CommandInvocation",
    "CommandError",
    "UnknownCommandError",
    "InvalidArgumentsError",
    "Validator",
    "OptionValidator",
]
