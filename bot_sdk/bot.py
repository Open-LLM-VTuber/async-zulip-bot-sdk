from __future__ import annotations

import abc
import importlib
import inspect
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, AsyncIterator, Optional, Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .async_zulip import AsyncClient
from .commands import CommandArgument, CommandInvocation, CommandParser, CommandSpec
from .config import BotLocalConfig, StorageConfig, load_bot_local_config, save_bot_local_config
from .db.database import create_engine, create_sessionmaker, make_sqlite_url, session_scope
from .models import (
    Event,
    Message,
    PrivateMessageRequest,
    StreamMessageRequest,
    UpdatePresenceRequest
)
from .permissions import PermissionPolicy
from .storage import BotStorage
from .i18n import I18n, build_i18n_for_bot

if TYPE_CHECKING:  # pragma: no cover - type-only import to avoid cycles
    from .runner import BotRunner


class BaseBot(abc.ABC):
    """Base class for bots. Override `on_message` and optional `on_event`.

    Breaking change: configuration now comes from per-bot YAML only
    (see `BotLocalConfig`). Class-level configuration attributes have
    been removed to reduce ambiguity. Customize your bot via its
    `bot.yaml` instead of subclass attributes.
    """

    def __init__(self, client: AsyncClient) -> None:
        self.client = client
        # These will be populated from bot.yaml in _load_settings
        self.command_prefixes: tuple[str, ...] = tuple()
        self.enable_mention_commands: bool = True
        self.auto_help_command: bool = True
        self.enable_storage: bool = True
        self.storage_path: Optional[str] = None
        self.storage_config: Optional[StorageConfig] = None
        self.enable_orm: bool = False
        self.orm_db_path: Optional[str] = None

        self.command_parser: Optional[CommandParser] = None
        self.storage: Optional[BotStorage] = None
        self.settings: Optional[BotLocalConfig] = None
        self.perms: Optional[PermissionPolicy] = None
        self._runner: Optional["BotRunner"] = None
        # i18n
        self.language: str = "en"
        # Ensure the attribute exists before any translation attempts,
        # even if i18n is not fully initialized yet.
        self.i18n: Optional[I18n] = None
        # ORM engine/session factory (initialized only when enable_orm is True)
        self._orm_engine: Optional[AsyncEngine] = None
        self._orm_session_factory: Optional[async_sessionmaker[AsyncSession]] = None
        logger.debug(f"Initialized bot {self.__class__.__name__}")

    def set_runner(self, runner: "BotRunner") -> None:
        """Called by BotRunner to allow commands to signal runner actions."""
        self._runner = runner

    def set_storage_config(self, storage_config: Optional[StorageConfig]) -> None:
        """Inject per-bot storage configuration from runner/config layer."""
        self.storage_config = storage_config
        
    async def post_init(self) -> None:
        """Hook for post-initialization logic. Override if needed.

        Splits initialization into clear phases:
        - load_settings: load per-bot YAML and apply overrides to class defaults
        - init_storage: prepare local persistence
        - load_identity: cache or fetch bot profile
        - set_presence: update active presence
        """
        await self._load_settings()
        await self._init_storage()
        await self._init_orm()
        await self._init_i18n()
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
        auto_cfg = self.storage_config or StorageConfig()
        self.storage = BotStorage(
            db_path=self.storage_path,
            namespace=f"bot_{bot_name}",
            auto_cache=auto_cfg.auto_cache,
            auto_flush_interval=auto_cfg.auto_flush_interval,
            auto_flush_retry=auto_cfg.auto_flush_retry,
            auto_flush_max_retries=auto_cfg.auto_flush_max_retries,
        )
        logger.info(f"Initialized storage at {self.storage_path}")
        # Initialize permissions helper
        self.perms = PermissionPolicy(self.client, self.storage)

    async def _init_orm(self) -> None:
        """Initialize ORM engine/session if enabled.

        By default, when KV storage is enabled, ORM reuses the same SQLite
        database file as BotStorage so both live in a single DB with
        coordinated WAL/locking settings.

        If storage is disabled or a separate DB is desired, bots can set
        ``orm_db_path`` explicitly. Otherwise a per-bot default path is
        derived from the module directory name.
        """

        if not self.enable_orm:
            return

        if self.orm_db_path is None:
            # Prefer sharing the KV storage file when enabled.
            if self.enable_storage and self.storage_path is not None:
                self.orm_db_path = self.storage_path
            else:
                # Derive from module directory name when possible.
                try:
                    mod = importlib.import_module(self.__class__.__module__)
                    mod_file = inspect.getfile(mod)
                    bot_dir = Path(mod_file).parent
                    db_name = bot_dir.name
                except Exception:
                    db_name = self.__class__.__name__.lower()
                self.orm_db_path = f"bot_data/{db_name}.sqlite"

        db_url = make_sqlite_url(self.orm_db_path)
        logger.info(f"Initializing ORM database for {self.__class__.__name__} at {db_url}")
        self._orm_engine = create_engine(db_url)
        self._orm_session_factory = create_sessionmaker(self._orm_engine)

    async def _init_i18n(self) -> None:
        """Initialize i18n helper for this bot.

        Uses the bot-local language from settings (``language``) and
        searches for translation files under ``<bot_dir>/i18n`` and
        ``bot_sdk/i18n``.
        """

        lang = "en"
        if self.settings and getattr(self.settings, "language", None):
            lang = self.settings.language
        self.language = lang
        try:
            self.i18n = build_i18n_for_bot(lang, self.__class__.__module__)
            logger.info(f"Initialized i18n for {self.__class__.__name__} with language '{lang}'")
        except Exception as exc:  # pragma: no cover - i18n should not block bot startup
            self.i18n = None
            logger.warning(f"Failed to initialize i18n for {self.__class__.__name__}: {exc}")

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
            self.settings = BotLocalConfig()
            self._settings_path = default_path  # type: ignore[attr-defined]
            await self.save_settings()  # Save default config
            logger.info(f"Created default bot settings at {default_path}")
        else:
            self.settings = load_bot_local_config(default_path)
            self._settings_path = default_path  # type: ignore[attr-defined]
            logger.info(f"Loaded bot settings from {default_path}")

        # Apply settings to runtime fields (YAML is the single source of truth now)
        overrides = self.settings
        self.command_prefixes = tuple(overrides.command_prefixes or [])
        if not self.command_prefixes:
            # Fallback to safe default if config left empty
            self.command_prefixes = ("!",)
        self.enable_mention_commands = bool(
            overrides.enable_mention_commands if overrides.enable_mention_commands is not None else True
        )
        self.auto_help_command = bool(
            overrides.auto_help_command if overrides.auto_help_command is not None else True
        )
        self.enable_storage = bool(
            overrides.enable_storage if overrides.enable_storage is not None else True
        )
        self.storage_path = overrides.storage_path
        self.storage_config = overrides.storage or StorageConfig()
        self.enable_orm = bool(overrides.enable_orm) if overrides.enable_orm is not None else False
        self.orm_db_path = overrides.orm_db_path

        # Recreate command parser to honor updated prefixes/mentions/help flags
        self.command_parser = CommandParser(
            prefixes=self.command_prefixes,
            enable_mentions=self.enable_mention_commands,
            auto_help=self.auto_help_command,
            translator=self.tr,
        )

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
                description=self.tr("Show your permission info"),
                handler=self._handle_whoami,
            )
        )
        # Permissions management command (restricted by min_level)
        default_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
        self.command_parser.register_spec(
            CommandSpec(
                name="perm",
                description=self.tr("Manage bot permissions"),
                args=[
                    CommandArgument("action", str, required=True, description="Action: set_owner | roles_show | roles_set | allow_stop | deny_stop"),
                    CommandArgument("arg1", str, required=False, description="First argument (user_id or role) depending on action"),
                    CommandArgument("arg2", str, required=False, description="Second argument (level) for roles_set"),
                ],
                handler=self._handle_perm,
                min_level=default_levels.get("bot_owner", 200),
            )
        )
        # Hot reload for settings and translations (admin-level by default)
        self.command_parser.register_spec(
            CommandSpec(
                name="reload",
                description=self.tr("Reload configuration and translations"),
                handler=self._handle_reload,
                min_level=default_levels.get("admin", 50),
            )
        )
        # Built-in: stop (bot shutdown)
        stop_min_level = default_levels.get("admin", 50)
        self.command_parser.register_spec(
            CommandSpec(
                name="stop",
                description=self.tr("Stop the bot"),
                handler=self._handle_stop,
                min_level=stop_min_level,
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

    def tr(self, key: str, **kwargs: Any) -> str:
        """Translate a user-facing string using the bot's i18n helper.

        Falls back to the original key when no translation is available
        or when i18n has not been initialized yet.
        """

        i18n = getattr(self, "i18n", None)
        if i18n is None:
            if kwargs:
                try:
                    return key.format(**kwargs)
                except Exception:
                    return key
            return key
        return i18n.translate(key, **kwargs)

    @property
    def orm_sessionmaker(self) -> async_sessionmaker[AsyncSession]:
        """Return the ORM session factory.

        Raises a RuntimeError if ORM is not enabled for this bot.
        """

        if not self._orm_session_factory:
            raise RuntimeError("ORM is not enabled or not initialized for this bot")
        return self._orm_session_factory

    @asynccontextmanager
    async def orm_session(self) -> AsyncIterator[AsyncSession]:
        """Async context manager yielding an ORM session.

        Example:
            async with self.orm_session() as session:
                ...
        """

        if not self._orm_session_factory:
            raise RuntimeError("ORM is not enabled or not initialized for this bot")
        async with session_scope(self._orm_session_factory) as session:
            yield session

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
            "👤 "
            + self.tr("User Info")
            + "\n"
            + f"{self.tr('User')}: {message.sender_full_name} (id={user_id})\n"
            + f"{self.tr('Roles')}: {', '.join(sorted(set(roles)))}\n"
            + f"{self.tr('Level')}: {level}"
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
                await self.send_reply(message, err(self.tr("Usage: !perm set_owner <user_id>")))
                return
            try:
                new_owner = int(arg1)
            except Exception:
                await self.send_reply(message, err(self.tr("Invalid user_id")))
                return
            if not self.settings:
                self.settings = BotLocalConfig()
            self.settings.owner_user_id = new_owner
            await self.save_settings()
            await self.send_reply(message, ok(self.tr("Bot owner set to {user_id}", user_id=new_owner)))
            return

        if action == "roles_show":
            role_levels = (self.settings.role_levels if self.settings else {"user": 1, "admin": 50, "owner": 100, "bot_owner": 200})
            lines = [f"{k}: {v}" for k, v in sorted(role_levels.items(), key=lambda kv: kv[1])]
            await self.send_reply(message, self.tr("Current role levels:\n{lines}", lines="\n".join(lines)))
            return

        if action == "roles_set":
            if not arg1 or not arg2:
                await self.send_reply(message, err(self.tr("Usage: !perm roles_set <role> <level>")))
                return
            role = str(arg1)
            try:
                level = int(arg2)
            except Exception:
                await self.send_reply(message, err(self.tr("Invalid level")))
                return
            if not self.settings:
                self.settings = BotLocalConfig()
            self.settings.role_levels[role] = level
            await self.save_settings()
            await self.send_reply(message, ok(self.tr("Role '{role}' level set to {level}", role=role, level=level)))
            return

        if action == "allow_stop":
            if not arg1:
                await self.send_reply(message, err(self.tr("Usage: !perm allow_stop <user_id>")))
                return
            try:
                uid = int(arg1)
            except Exception:
                await self.send_reply(message, err(self.tr("Invalid user_id")))
                return
            acl = []
            if self.storage:
                acl = await self.storage.get("acl.stop", [])
                if uid not in acl:
                    acl.append(uid)
                    await self.storage.put("acl.stop", acl)
                    await self.send_reply(message, ok(self.tr("User {user_id} allowed to stop bot", user_id=uid)))
                else:
                    await self.send_reply(message, ok(self.tr("User {user_id} is already allowed to stop bot", user_id=uid)))
            return

        if action == "deny_stop":
            if not arg1:
                await self.send_reply(message, err(self.tr("Usage: !perm deny_stop <user_id>")))
                return
            try:
                uid = int(arg1)
            except Exception:
                await self.send_reply(message, err(self.tr("Invalid user_id")))
                return
            acl = []
            if self.storage:
                acl = await self.storage.get("acl.stop", [])
                acl = [x for x in acl if x != uid]
                await self.storage.put("acl.stop", acl)
            await self.send_reply(message, ok(self.tr("User {user_id} denied to stop bot", user_id=uid)))
            return

        await self.send_reply(message, err(self.tr("Unknown action. Use: set_owner | roles_show | roles_set | allow_stop | deny_stop")))

    async def _handle_reload(self, invocation: CommandInvocation, message: Message, bot: BaseBot) -> None:
        """Reload bot settings (bot.yaml) and i18n files without restart."""
        # Reload settings from disk if we know where they live.
        try:
            settings_path = getattr(self, "_settings_path", None)
        except Exception:
            settings_path = None

        try:
            if settings_path is not None and settings_path.exists():
                self.settings = load_bot_local_config(settings_path)
                logger.info(f"Reloaded bot settings from {settings_path}")
            else:
                logger.warning("No settings path available for reload; skipping settings reload")

            # Reinitialize i18n based on the possibly updated language.
            await self._init_i18n()
            await self.send_reply(message, f"✅ {self.tr('Configuration and translations reloaded.')}")
        except Exception as exc:
            logger.warning(f"Reload failed: {exc}")
            await self.send_reply(
                message,
                f"❌ "
                + self.tr("Failed to reload configuration: {error}", error=str(exc)),
            )

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
            await self.send_reply(message, self.tr("Permission denied: you cannot stop this bot."))
            return

        await self.send_reply(message, self.tr("🛑 Stopping the bot..."))
        if self._runner:
            self._runner.request_stop(reason=f"requested by user {requester}")
        else:
            logger.warning("Stop requested but runner reference is missing; bot may keep running")

    async def get_user_level(self, user_id: int) -> int:
        """Public helper for resolving a user's permission level.

        Used by the built-in help command to hide commands that
        require a higher level than the caller.
        """

        return await self._compute_user_level(user_id)

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
        # Dispose ORM engine if it was initialized
        if self._orm_engine is not None:
            try:
                await self._orm_engine.dispose()
            except Exception as exc:
                logger.warning(f"Failed to dispose ORM engine cleanly: {exc}")

    async def on_event(self, event: Event) -> None:
        """Main event handler. Default implementation dispatches commands and messages.
        
        Override to handle other event types or customize behavior.
        But remember to call super().on_event(event) to retain command/message handling.
        """
        if event.type == "message" and event.message is not None:
            if event.message.sender_id == self._user_id:
                logger.debug("Ignoring message from self")
                return  # Ignore messages from ourselves
            # Early permission check based on command name only, so that
            # users without sufficient level get a clear denial even if
            # their arguments are missing or malformed.
            try:
                raw_text = (event.message.content or "").strip()
                spec = self.command_parser.find_command_spec(raw_text) if raw_text else None
            except Exception:
                spec = None

            if spec is not None and getattr(spec, "min_level", None) is not None:
                try:
                    user_level = await self._compute_user_level(event.message.sender_id)
                except Exception as exc:
                    logger.warning(f"Permission pre-check failed: {exc}")
                    user_level = 0
                if user_level < spec.min_level:  # type: ignore[attr-defined]
                    await self.send_reply(event.message, self.tr("Permission denied."))
                    return
            try:
                command_invocation = self.parse_command(event.message)
            except Exception as exc:  # CommandError and others
                logger.warning(f"Command parsing failed: {exc}")
                await self.send_reply(event.message, self.tr("Command error: {error}", error=str(exc)))
                return

            if command_invocation is not None:
                try:
                    logger.debug(f"Dispatching command: {command_invocation.name} with args {command_invocation.args}")
                    spec = command_invocation.spec
                    if spec and getattr(spec, "min_level", None) is not None:
                        user_level = await self._compute_user_level(event.message.sender_id)
                        if user_level < spec.min_level:  # type: ignore[attr-defined]
                            await self.send_reply(event.message, self.tr("Permission denied."))
                            return
                    await self.command_parser.dispatch(command_invocation, message=event.message, bot=self)
                except Exception as exc:
                    logger.warning(f"Command dispatch failed: {exc}")
                    await self.send_reply(event.message, self.tr("Command error: {error}", error=str(exc)))
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
        if not self.command_parser:
            raise RuntimeError("Command parser is not initialized; ensure post_init has run")
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
