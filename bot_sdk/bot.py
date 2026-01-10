from __future__ import annotations

import abc
from typing import Optional, TYPE_CHECKING
import importlib
import inspect
from pathlib import Path
from loguru import logger

from .async_zulip import AsyncClient
from .commands import CommandInvocation, CommandParser, CommandSpec, CommandArgument
from .storage import BotStorage
from .permissions import PermissionPolicy
from .config import BotLocalConfig, load_bot_local_config, save_bot_local_config
from .models import (
    Event,
    Message,
    PrivateMessageRequest,
    StreamMessageRequest,
    UpdatePresenceRequest
)

if TYPE_CHECKING:  # pragma: no cover - type-only import to avoid cycles
    from .runner import BotRunner


class BaseBot(abc.ABC):
    """Base class for bots. Override `on_message` and optional `on_event`."""

    # Prefix characters that mark a command (e.g., "/help" or "!ping").
    # As Zulip reserves "/" for system commands, "!" or other characters are often a better choice.
    command_prefixes = ("!",)
    # Whether to treat leading @-mentions as commands.
    enable_mention_commands = True
    # Whether to auto-register the built-in help command.
    auto_help_command = True
    # Storage configuration
    enable_storage = True
    storage_path: Optional[str] = None  # Defaults to "bot_data/{bot_name}.db"

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        self.command_parser = CommandParser(
            prefixes=self.command_prefixes,
            enable_mentions=self.enable_mention_commands,
            auto_help=self.auto_help_command,
        )
        self.storage: Optional[BotStorage] = None
        self.settings: Optional[BotLocalConfig] = None
        self.perms: Optional[PermissionPolicy] = None
        self._runner: Optional["BotRunner"] = None
        logger.debug(f"Initialized bot {self.__class__.__name__}")

    def set_runner(self, runner: "BotRunner") -> None:
        """Called by BotRunner to allow commands to signal runner actions."""
        self._runner = runner
        
    async def post_init(self) -> None:
        """Hook for post-initialization logic. Override if needed.

        Splits initialization into clear phases:
        - init_storage: prepare local persistence
        - load_identity: cache or fetch bot profile
        - set_presence: update active presence
        """
        await self._init_storage()
        await self._load_settings()
        await self._load_identity()
        await self._set_presence()
        await self._register_commands()

    async def _init_storage(self) -> None:
        """Initialize storage so later steps can use cached data."""
        bot_name = self.__class__.__name__.lower()
        if not self.enable_storage:
            return
        if self.storage_path is None:
            self.storage_path = f"bot_data/{bot_name}.db"
        self.storage = BotStorage(
            db_path=self.storage_path,
            namespace=f"bot_{bot_name}"
        )
        logger.info(f"Initialized storage at {self.storage_path}")
        # Initialize permissions helper
        self.perms = PermissionPolicy(self.client, self.storage)

    async def _load_settings(self) -> None:
        """Load per-bot settings YAML next to the bot module by default."""
        # Default config path: <bot_module_dir>/bot.yaml
        try:
            mod = importlib.import_module(self.__class__.__module__)
            mod_file = inspect.getfile(mod)
            default_path = Path(mod_file).parent / "bot.yaml"
        except Exception:
            logger.warning("Failed to determine bot module path, using ./bot.yaml for settings")
            default_path = Path("bot.yaml")
        # Load settings
        if not default_path.exists():
            logger.info(f"No bot settings file found at {default_path}, using defaults.")
            self.settings = BotLocalConfig(owner_user_id=-1)
            self._settings_path = default_path  # type: ignore[attr-defined]
            await self.save_settings()  # Save default config
            logger.info(f"Created default bot settings at {default_path}")
            return
        self.settings = load_bot_local_config(default_path)
        self._settings_path = default_path  # type: ignore[attr-defined]
        logger.info(f"Loaded bot settings from {default_path}")

    async def _load_identity(self) -> None:
        """Load bot identity from cache or fetch from server once."""
        email: Optional[str] = None
        profile_data: Optional[dict] = None
        if self.storage:
            profile_data = await self.storage.get("__profile__")
        if profile_data:
            logger.debug("Loaded bot profile from storage cache")
            email = profile_data.get("email")
        else:
            logger.debug("Fetching bot profile for command parser identity aliases")
            profile = await self.client.get_profile()
            profile_data = {
                "user_id": profile.user_id,
                "full_name": profile.full_name,
                "email": getattr(profile, "email", None),
            }
            if self.storage:
                await self.storage.put("__profile__", profile_data)
            email = profile_data.get("email")
        assert profile_data is not None
        self._user_id = profile_data["user_id"]
        self._user_name = profile_data["full_name"]
        self.command_parser.add_identity_aliases(full_name=self._user_name, email=email)
        logger.info(f"{self.__class__.__name__} started with user_id: {self._user_id}")

    async def _set_presence(self) -> None:
        """Set active presence on startup."""
        await self.client.update_presence(UpdatePresenceRequest(status="active"))
        logger.info("Set presence to active")

    async def _register_commands(self) -> None:
        """Register built-in and bot-specific commands.

        Override `register_commands` in subclasses to add custom commands.
        """
        # Built-in: whoami (permissions introspection)
        self.command_parser.register_spec(
            CommandSpec(
                name="whoami",
                description="Show your permission info",
                handler=self._handle_whoami,
            )
        )
        # Permissions management command (restricted by min_level)
        default_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
        self.command_parser.register_spec(
            CommandSpec(
                name="perm",
                description="Manage bot permissions",
                args=[
                    CommandArgument("action", str, required=True, description="Action: set_owner | roles_show | roles_set | allow_stop | deny_stop"),
                    CommandArgument("arg1", str, required=False, description="First argument (user_id or role) depending on action"),
                    CommandArgument("arg2", str, required=False, description="Second argument (level) for roles_set"),
                ],
                handler=self._handle_perm,
                min_level=default_levels.get("bot_owner", 200),
            )
        )
        # Built-in: stop (bot shutdown)
        self.command_parser.register_spec(
            CommandSpec(
                name="stop",
                description="Stop the bot",
                handler=self._handle_stop,
            )
        )
        # Hook for subclasses
        self.register_commands()

    def register_commands(self) -> None:
        """Hook for subclasses to register CommandSpec entries."""
        return None

    async def save_settings(self) -> None:
        """Persist current settings back to its YAML file."""
        if not hasattr(self, "_settings_path") or not self.settings:
            return
        try:
            save_bot_local_config(self._settings_path, self.settings)
        except Exception:
            logger.warning("Failed to save bot settings")

    async def _handle_whoami(self, invocation: CommandInvocation, message: Message, bot: BaseBot) -> None:
        """Show permission-related info for the caller."""
        user_id = message.sender_id
        # Determine level by config priorities
        role_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
        level = role_levels.get("user", 1)
        roles: list[str] = ["user"]
        # Bot owner
        if self.settings and self.settings.owner_user_id and user_id == self.settings.owner_user_id:
            level = max(level, role_levels.get("bot_owner", 200))
            roles.append("bot_owner")
        # Org admin/owner
        try:
            if self.perms and await self.perms.is_owner(user_id):
                level = max(level, role_levels.get("owner", 100))
                roles.append("org_owner")
            elif self.perms and await self.perms.is_admin(user_id):
                level = max(level, role_levels.get("admin", 50))
                roles.append("org_admin")
        except Exception:
            pass
        text = (
            f"👤 {message.sender_full_name} (id={user_id})\n"
            f"Roles: {', '.join(sorted(set(roles)))}\n"
            f"Level: {level}"
        )
        await self.send_reply(message, text)

    async def _handle_perm(self, invocation: CommandInvocation, message: Message, bot: BaseBot) -> None:
        action = (invocation.args.get("action") or "").lower()
        arg1 = invocation.args.get("arg1")
        arg2 = invocation.args.get("arg2")

        def ok(msg: str) -> str:
            return f"✅ {msg}"

        def err(msg: str) -> str:
            return f"❌ {msg}"

        if action == "set_owner":
            if not arg1:
                await self.send_reply(message, err("Usage: !perm set_owner <user_id>"))
                return
            try:
                new_owner = int(arg1)
            except Exception:
                await self.send_reply(message, err("Invalid user_id"))
                return
            if not self.settings:
                self.settings = BotLocalConfig()
            self.settings.owner_user_id = new_owner
            await self.save_settings()
            await self.send_reply(message, ok(f"Bot owner set to {new_owner}"))
            return

        if action == "roles_show":
            role_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
            lines = [f"{k}: {v}" for k, v in sorted(role_levels.items(), key=lambda kv: kv[1])]
            await self.send_reply(message, "Current role levels:\n" + "\n".join(lines))
            return

        if action == "roles_set":
            if not arg1 or not arg2:
                await self.send_reply(message, err("Usage: !perm roles_set <role> <level>"))
                return
            role = str(arg1)
            try:
                level = int(arg2)
            except Exception:
                await self.send_reply(message, err("Invalid level"))
                return
            if not self.settings:
                self.settings = BotLocalConfig()
            self.settings.role_levels[role] = level
            await self.save_settings()
            await self.send_reply(message, ok(f"Role '{role}' level set to {level}"))
            return

        if action == "allow_stop":
            if not arg1:
                await self.send_reply(message, err("Usage: !perm allow_stop <user_id>"))
                return
            try:
                uid = int(arg1)
            except Exception:
                await self.send_reply(message, err("Invalid user_id"))
                return
            acl = []
            if self.storage:
                acl = await self.storage.get("acl.stop", [])
                if uid not in acl:
                    acl.append(uid)
                    await self.storage.put("acl.stop", acl)
            await self.send_reply(message, ok(f"User {uid} allowed to stop bot"))
            return

        if action == "deny_stop":
            if not arg1:
                await self.send_reply(message, err("Usage: !perm deny_stop <user_id>"))
                return
            try:
                uid = int(arg1)
            except Exception:
                await self.send_reply(message, err("Invalid user_id"))
                return
            acl = []
            if self.storage:
                acl = await self.storage.get("acl.stop", [])
                acl = [x for x in acl if x != uid]
                await self.storage.put("acl.stop", acl)
            await self.send_reply(message, ok(f"User {uid} denied to stop bot"))
            return

        await self.send_reply(message, err("Unknown action. Use: set_owner | roles_show | roles_set | allow_stop | deny_stop"))

    async def _handle_stop(self, invocation: CommandInvocation, message: Message, bot: BaseBot) -> None:
        """Stop the bot if the caller is authorized."""
        requester = message.sender_id
        # Compute unified permission level (handles bot_owner, org owner/admin) and fallback ACL.
        role_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
        stop_min = role_levels.get("admin", 50)  # admins/owners/bot_owner all meet or exceed this
        try:
            user_level = await self._compute_user_level(requester)
        except Exception as exc:
            logger.warning(f"Stop permission level check failed: {exc}")
            user_level = 0

        acl_allowed = False
        if self.storage:
            try:
                acl = await self.storage.get("acl.stop", [])
                acl_allowed = requester in set(acl)
            except Exception:
                acl_allowed = False

        if user_level < stop_min and not acl_allowed:
            await self.send_reply(message, "❌ Permission denied: you cannot stop this bot.")
            return

        await self.send_reply(message, "🛑 Stopping the bot...")
        if self._runner:
            self._runner.request_stop(reason=f"requested by user {requester}")
        else:
            logger.warning("Stop requested but runner reference is missing; bot may keep running")

    async def _compute_user_level(self, user_id: int) -> int:
        role_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
        level = role_levels.get("user", 1)
        if self.settings and self.settings.owner_user_id and user_id == self.settings.owner_user_id:
            level = max(level, role_levels.get("bot_owner", 200))
        try:
            if self.perms and await self.perms.is_owner(user_id):
                level = max(level, role_levels.get("owner", 100))
            elif self.perms and await self.perms.is_admin(user_id):
                level = max(level, role_levels.get("admin", 50))
        except Exception:
            pass
        return level

    async def on_start(self) -> None:
        """Hook for startup logic. Override if needed."""
        return None

    async def on_stop(self) -> None:
        """Hook for cleanup logic. Override if needed."""
        logger.info("Bot stopping, performing cleanup...")
        await self.save_settings()

    async def on_event(self, event: Event) -> None:
        """Main event handler. Default implementation dispatches commands and messages.
        
        Override to handle other event types or customize behavior.
        But remember to call super().on_event(event) to retain command/message handling.
        """
        if event.type == "message" and event.message is not None:
            if event.message.sender_id == self._user_id:
                logger.debug("Ignoring message from self")
                return  # Ignore messages from ourselves
            try:
                command_invocation = self.parse_command(event.message)
            except Exception as exc:  # CommandError and others
                logger.warning(f"Command parsing failed: {exc}")
                await self.send_reply(event.message, f"Command error: {exc}")
                return

            if command_invocation is not None:
                try:
                    logger.debug(f"Dispatching command: {command_invocation.name} with args {command_invocation.args}")
                    spec = command_invocation.spec
                    if spec and getattr(spec, "min_level", None) is not None:
                        user_level = await self._compute_user_level(event.message.sender_id)
                        if user_level < spec.min_level:  # type: ignore[attr-defined]
                            await self.send_reply(event.message, "❌ Permission denied.")
                            return
                    await self.command_parser.dispatch(command_invocation, message=event.message, bot=self)
                except Exception as exc:
                    logger.warning(f"Command dispatch failed: {exc}")
                    await self.send_reply(event.message, f"Command error: {exc}")
            else:
                logger.debug(f"Received message: {event.message}")
                await self.on_message(event.message)

    @abc.abstractmethod
    async def on_message(self, message: Message) -> None:
        ...

    # Legacy hook retained for backwards compatibility; prefer per-command handlers.
    async def on_command(self, command: CommandInvocation, message: Message) -> None:
        return None

    def parse_command(self, message: Message) -> CommandInvocation | None:
        return self.command_parser.parse_message(message)

    async def send_reply(self, original: Message, content: str) -> None:
        """Utility to reply to a message (stream or private)."""
        if original.type == "private":
            recipients_raw = original.display_recipient or []
            if isinstance(recipients_raw, str):
                # should not happen for private, but tolerate
                to = []
            else:
                to = [r.id for r in recipients_raw if getattr(r, "id", None) is not None]
            payload = PrivateMessageRequest(to=to, content=content)
        else:
            topic = original.topic_or_subject or "general"
            if original.stream_id is None:
                raise ValueError("stream_id missing on stream message")
            payload = StreamMessageRequest(to=original.stream_id, topic=topic, content=content)

        await self.client.send_message(payload.model_dump(exclude_none=True))


__all__ = ["BaseBot"]
