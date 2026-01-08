from __future__ import annotations

import sys

from loguru import logger


def setup_logging(level: str = "INFO", json_logs: bool = False, backtrace: bool = False) -> None:
    """Configure loguru sinks for stdout.

    Called once at process start. Level accepts standard loguru strings (INFO, DEBUG...).
    """

    logger.remove()
    timefmt = "%Y-%m-%d %H:%M:%S"
    fmt = "<green>{time:"+ timefmt +"}</green> |[<level>{level}</level>]| <cyan>{name} | line: {line}</cyan> | <level>{message}</level>"
    if json_logs:
        fmt = "{level}\t{time}\t{message}\t{extra}"
    logger.add(sys.stdout, level=level.upper(), format=fmt, backtrace=backtrace, diagnose=False)


__all__ = ["setup_logging", "logger"]
