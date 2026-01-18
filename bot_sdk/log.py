from __future__ import annotations

import json
import sys
from pathlib import Path

from loguru import logger
from loguru._logger import Logger

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_FOLDER = Path(__file__).resolve().parent.parent / "logs"
DEFAULT_EXTRA = {"bot_name": "SYSTEM"}

CONSOLE_FORMAT = (
    "<magenta>{extra[bot_name]}</magenta> | "
    "<green>{time:" + TIME_FORMAT + "}</green> | "
    "[<level>{level}</level>] | "
    "<cyan>{name}:{line}</cyan> | "
    "<level>{message}</level>"
)

FILE_FORMAT = (
    "{extra[bot_name]} | "
    "{time:" + TIME_FORMAT + "} | "
    "[{level}] | "
    "{name}:{line} | "
    "{message}"
)


def _json_formatter(record: dict) -> str:
    payload = {
        "bot": record["extra"].get("bot_name", "UNKNOWN"),
        "level": record["level"].name,
        "time": record["time"].strftime(TIME_FORMAT),
        "name": record["name"],
        "line": record["line"],
        "message": record.get("message", ""),
        "extra": record.get("extra", {}),
    }
    return json.dumps(payload, ensure_ascii=True)


def _ensure_log_dir() -> None:
    LOG_FOLDER.mkdir(parents=True, exist_ok=True)


def _coerce_compression(compression: bool | str | None) -> str | None:
    if compression is True:
        return "zip"
    if compression is False:
        return None
    return compression


def setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
    backtrace: bool = False,
    rotation: str | None = "12:00",
    retention: str | None = "1 week",
    compression: bool | str | None = True,
) -> None:
    """Configure loguru sinks for system logs.

    System logs go to stdout and to ``logs/system.log`` with a SYSTEM tag.
    """

    _ensure_log_dir()
    level = level.upper()
    logger.remove()
    logger.configure(extra=DEFAULT_EXTRA)

    format_str = CONSOLE_FORMAT
    colorize = True
    file_format = FILE_FORMAT
    if json_logs:
        format_str = _json_formatter
        file_format = _json_formatter
        colorize = False

    system_logger = logger.bind(bot_name="SYSTEM")
    system_filter = lambda record: record.get("extra", {}).get("bot_name") == "SYSTEM"

    system_logger.add(
        sys.stdout,
        level=level,
        format=format_str,
        backtrace=backtrace,
        diagnose=False,
        enqueue=True,
        colorize=colorize,
    )
    system_logger.add(
        LOG_FOLDER / "system.log",
        level=level,
        format=file_format,
        enqueue=True,
        rotation=rotation,
        retention=retention,
        compression=_coerce_compression(compression),
        colorize=False,
        filter=system_filter,
    )


def get_bot_logger(
    bot_name: str | None = None,
    level: str = "INFO",
    rotation: str | None = "12:00",
    retention: str | None = "1 week",
    compression: bool | str | None = True,
    backtrace: bool = False,
) -> Logger:
    """Return a logger bound to a specific bot name.

    Adds a per-bot file sink under ``logs/<bot>.log`` and prefixes all
    messages with the bot tag. Console output is handled by ``setup_logging``.
    """

    _ensure_log_dir()
    level = level.upper()
    bot_label = bot_name or "UNKNOWN_BOT"
    filename = f"{bot_label}.log" if bot_name else "bots.log"

    bot_logger = logger.bind(bot_name=bot_label)
    bot_filter = lambda record: record.get("extra", {}).get("bot_name") == bot_label
    bot_logger.add(
        LOG_FOLDER / filename,
        level=level,
        format=FILE_FORMAT,
        enqueue=True,
        rotation=rotation,
        retention=retention,
        compression=_coerce_compression(compression),
        backtrace=backtrace,
        colorize=False,
        filter=bot_filter,
    )
    return bot_logger


__all__ = ["setup_logging", "logger", "get_bot_logger", "LoggerType"]
