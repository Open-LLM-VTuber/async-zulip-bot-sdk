import argparse
import asyncio
import importlib
import inspect
import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

from alembic import command
from alembic.config import Config
from loguru import logger

from bot_sdk import BaseBot, BotRunner, setup_logging
from bot_sdk.config import AppConfig, StorageConfig, load_config
from bot_sdk.db.database import make_sqlite_url


@dataclass
class BotSpec:
    factory: Callable[[Any], BaseBot]
    zuliprc: str
    event_types: List[str]
    storage: Optional[StorageConfig]


def discover_bot_factories(config: AppConfig, bots_dir: str = "bots") -> List[BotSpec]:
    specs: List[BotSpec] = []
    base_path = Path(bots_dir)
    if not base_path.exists():
        logger.warning(f"Bots directory not found: {bots_dir}")
        return specs

    for bot_cfg in config.bots:
        if not bot_cfg.enabled:
            continue
        module_name = bot_cfg.module or f"{bots_dir.replace('/', '.').replace('\\', '.')}" + f".{bot_cfg.name}"
        try:
            module = importlib.import_module(module_name)
        except ModuleNotFoundError as exc:
            logger.error(f"Bot module not found for {bot_cfg.name}: {module_name}")
            raise exc

        factory = _extract_factory(module, bot_cfg.class_name)
        if factory is None:
            raise RuntimeError(f"No bot factory/class found in module {module_name}")
        zuliprc_path = Path(bot_cfg.zuliprc or base_path / bot_cfg.name / "zuliprc")
        if not zuliprc_path.exists():
            raise FileNotFoundError(f"zuliprc not found for bot {bot_cfg.name}: {zuliprc_path}")
        specs.append(
            BotSpec(
                factory=_bind_factory(factory, bot_cfg.config),
                zuliprc=str(zuliprc_path),
                event_types=bot_cfg.event_types,
                storage=bot_cfg.storage,
            )
        )
    return specs


def _bind_factory(factory: Callable[..., BaseBot], bot_config: dict[str, Any]) -> Callable[[Any], BaseBot]:
    def wrapper(client: Any) -> BaseBot:
        try:
            return factory(client, bot_config)
        except TypeError:
            return factory(client)

    return wrapper


def _extract_factory(module, class_name: Optional[str] = None) -> Optional[Callable[[Any], BaseBot]]:
    if callable(getattr(module, "create_bot", None)):
        return module.create_bot
    if class_name:
        candidate = getattr(module, class_name, None)
        if inspect.isclass(candidate) and issubclass(candidate, BaseBot):
            return candidate
    candidate = getattr(module, "BOT_CLASS", None) or getattr(module, "Bot", None)
    if inspect.isclass(candidate) and issubclass(candidate, BaseBot):
        return candidate
    for attr in module.__dict__.values():
        if inspect.isclass(attr) and issubclass(attr, BaseBot) and attr is not BaseBot:
            return attr
    return None


async def run_all_bots(bot_specs: Iterable[BotSpec]) -> None:
    runners = [
        BotRunner(
            spec.factory,
            client_kwargs={"config_file": spec.zuliprc},
            event_types=spec.event_types,
            storage_config=spec.storage,
        )
        for spec in bot_specs
    ]

    if not runners:
        logger.warning("No bots discovered; exiting")
        return

    async with AsyncExitStack() as stack:
        started: List[BotRunner] = []
        for runner in runners:
            await stack.enter_async_context(runner)
            started.append(runner)

        tasks = [asyncio.create_task(r.run_forever()) for r in started]
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            raise
        finally:
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)


def _ensure_bot_orm_enabled(bot_name: str, bots_dir: str = "bots") -> Optional[type[BaseBot]]:
    """Validate that the target bot exists and has ORM enabled.

    Returns the resolved BaseBot subclass when available so callers can
    derive DB paths consistent with runtime behavior. If the bot type
    cannot be resolved, returns None but does not block migrations.
    """

    config_path = Path("bots.yaml")
    if not config_path.exists():
        raise FileNotFoundError("bots.yaml not found; cannot resolve bot configuration")

    app_config = load_config(str(config_path), AppConfig)
    bot_cfg = next((b for b in app_config.bots if b.name == bot_name and b.enabled), None)
    if bot_cfg is None:
        raise SystemExit(f"Bot '{bot_name}' not found or disabled in bots.yaml")

    module_name = bot_cfg.module or f"{bots_dir.replace('/', '.').replace('\\', '.')}" + f".{bot_cfg.name}"
    module = importlib.import_module(module_name)

    bot_type: Optional[type[BaseBot]] = None

    if bot_cfg.class_name:
        candidate = getattr(module, bot_cfg.class_name, None)
        if inspect.isclass(candidate) and issubclass(candidate, BaseBot):
            bot_type = candidate

    if bot_type is None:
        candidate = getattr(module, "BOT_CLASS", None)
        if inspect.isclass(candidate) and issubclass(candidate, BaseBot):
            bot_type = candidate

    if bot_type is None:
        # Best-effort fallback to generic factory resolution.
        factory = _extract_factory(module, bot_cfg.class_name)
        if inspect.isclass(factory) and issubclass(factory, BaseBot):
            bot_type = factory

    if bot_type is None:
        logger.warning(
            "Could not resolve a BaseBot subclass for '%s'; skipping ORM enable check",
            bot_name,
        )
        return None

    if not getattr(bot_type, "enable_orm", False):
        raise SystemExit(
            f"Bot '{bot_name}' has enable_orm = False; ORM migrations are disabled for this bot"
        )

    return bot_type


def _resolve_bot_db_path(bot_type: type[BaseBot]) -> Path:
    """Resolve the SQLite DB path for a bot, mirroring BaseBot defaults.

    Priority:
    1. Explicit orm_db_path on the bot class
    2. Explicit storage_path on the bot class
    3. Default KV path: bot_data/<ClassName.lower()>.db
    """

    orm_db_path = getattr(bot_type, "orm_db_path", None)
    if orm_db_path:
        return Path(orm_db_path)

    storage_path = getattr(bot_type, "storage_path", None)
    if storage_path:
        return Path(storage_path)

    return Path("bot_data") / f"{bot_type.__name__.lower()}.db"


def _run_bots() -> None:
    setup_logging("DEBUG")
    config_path = Path("bots.yaml")
    if not config_path.exists():
        raise FileNotFoundError("bots.yaml not found; please create it to list bots to launch")
    app_config = load_config(str(config_path), AppConfig)
    bot_specs = discover_bot_factories(app_config)
    asyncio.run(run_all_bots(bot_specs))


def _make_migrations(bot_name: str, message: Optional[str] = None) -> None:
    """Create or update Alembic migrations for a specific bot.

    This uses the global alembic.ini as a template but points
    script_location to ``bots/<bot_name>/migrations`` so that each
    bot keeps its own migration history.
    """

    setup_logging("INFO")

    bot_type = _ensure_bot_orm_enabled(bot_name)

    bots_dir = Path("bots")
    bot_dir = bots_dir / bot_name
    if not bot_dir.exists():
        raise FileNotFoundError(f"Bot directory not found: {bot_dir}")

    migrations_dir = bot_dir / "migrations"
    versions_dir = migrations_dir / "versions"

    migrations_dir.mkdir(parents=True, exist_ok=True)
    versions_dir.mkdir(parents=True, exist_ok=True)

    # Seed env.py and script.py.mako from the SDK-level templates if they don't exist yet.
    # Bot authors can then import their ORM models inside that env.py
    # so Alembic's autogenerate can pick them up.
    template_env = Path("bot_sdk") / "db" / "migrations" / "env.py"
    target_env = migrations_dir / "env.py"
    if not target_env.exists():
        if not template_env.exists():
            raise FileNotFoundError(f"Alembic template env.py not found at {template_env}")
        target_env.write_text(template_env.read_text(encoding="utf-8"), encoding="utf-8")

    template_script = Path("bot_sdk") / "db" / "migrations" / "script.py.mako"
    target_script = migrations_dir / "script.py.mako"
    if not target_script.exists() and template_script.exists():
        target_script.write_text(template_script.read_text(encoding="utf-8"), encoding="utf-8")

    # Use the same DB path that the bot would use at runtime so
    # ORM and KV storage share a single SQLite file by default.
    if bot_type is not None:
        db_path = _resolve_bot_db_path(bot_type)
    else:
        # Fallback for unusual bots where we couldn't resolve the type.
        db_path = Path("bot_data") / f"{bot_name}.sqlite"

    os.environ.setdefault("DATABASE_URL", make_sqlite_url(db_path))

    cfg = Config("alembic.ini")
    # Point Alembic to the bot-specific migrations directory.
    cfg.set_main_option("script_location", migrations_dir.as_posix())

    revision_kwargs: dict[str, Any] = {"autogenerate": True}
    if message:
        revision_kwargs["message"] = message

    logger.info(f"Creating Alembic revision for bot '{bot_name}' in {migrations_dir}")
    command.revision(cfg, **revision_kwargs)


def _migrate(bot_name: str, revision: str = "head") -> None:
    """Apply Alembic migrations for a specific bot.

    Uses the same per-bot migrations directory and database URL
    convention as ``_make_migrations``.
    """

    setup_logging("INFO")

    bot_type = _ensure_bot_orm_enabled(bot_name)

    bots_dir = Path("bots")
    bot_dir = bots_dir / bot_name
    if not bot_dir.exists():
        raise FileNotFoundError(f"Bot directory not found: {bot_dir}")

    migrations_dir = bot_dir / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found for bot {bot_name}: {migrations_dir}")

    # Ensure env.py and script.py.mako exist (required by Alembic script environment)
    template_env = Path("bot_sdk") / "db" / "migrations" / "env.py"
    target_env = migrations_dir / "env.py"
    if not target_env.exists():
        if not template_env.exists():
            raise FileNotFoundError(f"Alembic template env.py not found at {template_env}")
        target_env.write_text(template_env.read_text(encoding="utf-8"), encoding="utf-8")

    template_script = Path("bot_sdk") / "db" / "migrations" / "script.py.mako"
    target_script = migrations_dir / "script.py.mako"
    if not target_script.exists() and template_script.exists():
        target_script.write_text(template_script.read_text(encoding="utf-8"), encoding="utf-8")

    if bot_type is not None:
        db_path = _resolve_bot_db_path(bot_type)
    else:
        db_path = Path("bot_data") / f"{bot_name}.sqlite"

    os.environ.setdefault("DATABASE_URL", make_sqlite_url(db_path))

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", migrations_dir.as_posix())

    logger.info(f"Applying Alembic migrations for bot '{bot_name}' to revision '{revision}'")
    command.upgrade(cfg, revision)


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async Zulip bot runner and migration helper")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["run", "makemigrations", "migrate"],
        default="run",
        help="Command to execute: run bots (default), generate migrations, or apply migrations for a bot",
    )
    parser.add_argument("--bot", help="Bot name (for makemigrations)")
    parser.add_argument("-m", "--message", help="Migration message (for makemigrations)")
    parser.add_argument("--revision", default="head", help="Target revision for migrate (default: head)")
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    if args.command == "run":
        _run_bots()
        return

    if args.command == "makemigrations":
        if not args.bot:
            raise SystemExit("makemigrations requires --bot BOT_NAME")
        _make_migrations(args.bot, args.message)
        return

    if args.command == "migrate":
        if not args.bot:
            raise SystemExit("migrate requires --bot BOT_NAME")
        _migrate(args.bot, args.revision)
        return


if __name__ == "__main__":
    main()