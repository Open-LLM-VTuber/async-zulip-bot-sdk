from __future__ import annotations

import asyncio
import importlib
import os
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from bot_sdk.db.database import Base, make_sqlite_url

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def _load_bot_models() -> None:
    """Best-effort import of bot-local ORM models.

    Convention:
    - Per-bot Alembic scripts live in ``bots/<bot_name>/migrations``
    - ORM models for that bot live in ``bots/<bot_name>/models.py``

    When this env.py is copied into a bot's migrations directory,
    this helper will detect the ``bots/<bot_name>`` layout from
    ``__file__`` and import ``bots.<bot_name>.models`` so that any
    models subclassing ``bot_sdk.db.database.Base`` are registered
    on ``Base.metadata`` for Alembic's autogenerate.
    """

    env_path = Path(__file__).resolve()

    # Expect .../bots/<bot_name>/migrations/env.py
    try:
        if env_path.parent.name != "migrations":
            return
        bot_dir = env_path.parent.parent
        if bot_dir.parent.name != "bots":
            return
        bot_name = bot_dir.name
        module_name = f"bots.{bot_name}.models"
        importlib.import_module(module_name)
    except Exception:
        # Never break migrations just because models cannot be loaded;
        # bots that do not use ORM can safely ignore this.
        return


_load_bot_models()

# Metadata for autogenerate
# Add ORM models to Base to include them in migrations

_target_metadata = Base.metadata


def get_url() -> str:
    env_url = os.getenv("DATABASE_URL")
    if env_url:
        return env_url
    default_path = Path("bot_data/db.sqlite").resolve()
    return make_sqlite_url(default_path)


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=_target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=_target_metadata)

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = get_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    async def run() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(run())


def run_migrations() -> None:
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        run_migrations_online()


run_migrations()
