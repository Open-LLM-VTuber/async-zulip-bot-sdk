from __future__ import annotations

import argparse
import asyncio
from contextlib import AsyncExitStack
from pathlib import Path
from typing import Iterable, List, Optional

from loguru import logger

from . import BotRunner, setup_logging
from .config import AppConfig, load_config
from .console import run_console
from .db.cli import make_bot_migrations, run_bot_migrations
from .loader import BotSpec, discover_bot_factories


async def run_all_bots(bot_specs: Iterable[BotSpec]) -> None:
    runners = [
        BotRunner(
            spec.factory,
            client_kwargs={"config_file": spec.zuliprc},
            event_types=spec.event_types,
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


def _run_bots(config_path: str = "bots.yaml", verbose: bool = False) -> None:
    setup_logging("DEBUG" if verbose else "INFO")
    path_obj: Path = Path(config_path)
    if not path_obj.exists():
        raise FileNotFoundError(f"{path_obj} not found; please create it to list bots to launch")
    app_config = load_config(str(path_obj), AppConfig)
    bot_specs = discover_bot_factories(app_config)
    asyncio.run(run_all_bots(bot_specs))


def _run_console_mode(config_path: str = "bots.yaml", verbose: bool = False) -> None:
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)
    asyncio.run(run_console(config_path, log_level=log_level))


def _parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Async Zulip bot runner and migration helper")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["console", "run", "makemigrations", "migrate"],
        default="console",
        help="Command to execute: interactive console (default), run all bots, generate migrations, or apply migrations",
    )
    parser.add_argument("--bot", help="Bot name (for makemigrations)")
    parser.add_argument("--message", "-m", help="Migration message (for makemigrations)")
    parser.add_argument("--revision", default="head", help="Target revision for migrate (default: head)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging output")
    parser.add_argument(
        "--config",
        default="bots.yaml",
        help="Path to bots.yaml configuration file (default: bots.yaml)",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> None:
    args = _parse_args(argv)

    if args.command == "console":
        _run_console_mode(args.config, args.verbose)
        return

    if args.command == "run":
        _run_bots(args.config, args.verbose)
        return

    if args.command == "makemigrations":
        setup_logging("DEBUG" if args.verbose else "INFO")
        if not args.bot:
            raise SystemExit("makemigrations requires --bot BOT_NAME")
        make_bot_migrations(args.bot, args.message)
        return

    if args.command == "migrate":
        setup_logging("DEBUG" if args.verbose else "INFO")
        if not args.bot:
            raise SystemExit("migrate requires --bot BOT_NAME")
        run_bot_migrations(args.bot, args.revision)
        return


if __name__ == "__main__":  # pragma: no cover
    main()
