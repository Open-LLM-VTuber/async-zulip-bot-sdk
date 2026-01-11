import importlib
import inspect
import os
from pathlib import Path
from typing import Any, Optional

from alembic import command
from alembic.config import Config
from loguru import logger

from bot_sdk import BaseBot
from bot_sdk.config import AppConfig, load_config
from bot_sdk.db.database import make_sqlite_url
from bot_sdk.loader import _extract_factory


def _ensure_migration_templates(migrations_dir: Path) -> None:
    """Ensure Alembic env.py and script.py.mako exist in the target migrations dir."""

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


def ensure_bot_orm_enabled(bot_name: str, bots_dir: str = "bots") -> Optional[type[BaseBot]]:
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


def resolve_bot_db_path(bot_type: type[BaseBot]) -> Path:
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


def make_bot_migrations(bot_name: str, message: Optional[str] = None) -> None:
    """Create or update Alembic migrations for a specific bot.

    This uses the global alembic.ini as a template but points
    script_location to ``bots/<bot_name>/migrations`` so that each
    bot keeps its own migration history.
    """
    
    # Ensure setup_logging logic is handled by caller (main or console) or defaults exist.
    # We won't call setup_logging here to avoid overriding caller's config.

    bot_type = ensure_bot_orm_enabled(bot_name)

    bots_dir = Path("bots")
    bot_dir = bots_dir / bot_name
    if not bot_dir.exists():
        raise FileNotFoundError(f"Bot directory not found: {bot_dir}")

    migrations_dir = bot_dir / "migrations"
    versions_dir = migrations_dir / "versions"

    migrations_dir.mkdir(parents=True, exist_ok=True)
    versions_dir.mkdir(parents=True, exist_ok=True)

    # Seed env.py and script.py.mako from the SDK-level templates if they don't exist yet.
    _ensure_migration_templates(migrations_dir)

    # Use the same DB path that the bot would use at runtime so
    # ORM and KV storage share a single SQLite file by default.
    if bot_type is not None:
        db_path = resolve_bot_db_path(bot_type)
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


def run_bot_migrations(bot_name: str, revision: str = "head") -> None:
    """Apply Alembic migrations for a specific bot.

    Uses the same per-bot migrations directory and database URL
    convention as ``make_bot_migrations``.
    """

    bot_type = ensure_bot_orm_enabled(bot_name)

    bots_dir = Path("bots")
    bot_dir = bots_dir / bot_name
    if not bot_dir.exists():
        raise FileNotFoundError(f"Bot directory not found: {bot_dir}")

    migrations_dir = bot_dir / "migrations"
    if not migrations_dir.exists():
        raise FileNotFoundError(f"Migrations directory not found for bot {bot_name}: {migrations_dir}")

    # Ensure env.py and script.py.mako exist (required by Alembic script environment)
    _ensure_migration_templates(migrations_dir)

    if bot_type is not None:
        db_path = resolve_bot_db_path(bot_type)
    else:
        db_path = Path("bot_data") / f"{bot_name}.sqlite"

    os.environ.setdefault("DATABASE_URL", make_sqlite_url(db_path))

    cfg = Config("alembic.ini")
    cfg.set_main_option("script_location", migrations_dir.as_posix())

    logger.info(f"Applying Alembic migrations for bot '{bot_name}' to revision '{revision}'")
    command.upgrade(cfg, revision)
