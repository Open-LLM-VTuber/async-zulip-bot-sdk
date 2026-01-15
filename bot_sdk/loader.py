from __future__ import annotations

import importlib
import inspect
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, List, Optional

from loguru import logger

from . import BaseBot
from .config import AppConfig, StorageConfig


@dataclass
class BotSpec:
    name: str
    factory: Callable[[Any], BaseBot]
    zuliprc: str
    event_types: List[str]
    storage: Optional[StorageConfig]


def discover_bot_factories(
    config: AppConfig,
    bots_dir: str = "bots",
    *,
    reload_modules: bool = False,
) -> List[BotSpec]:
    specs: List[BotSpec] = []
    base_path = Path(bots_dir)
    if not base_path.exists():
        logger.warning(f"Bots directory not found: {bots_dir}")
        return specs

    # Ensure the project root containing the bots directory is importable.
    # When running via an installed console_script, sys.path[0] points to the
    # environment's Scripts/ directory, not the user's project. Adding the
    # parent of `bots_dir` makes modules like "bots.my_bot" importable when
    # the user runs `async-zulip-bot` from their project root.
    project_root = str(base_path.resolve().parent)
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    for bot_cfg in config.bots:
        if not bot_cfg.enabled:
            continue
        module_name = bot_cfg.module or f"{bots_dir.replace('/', '.').replace('\\', '.')}" + f".{bot_cfg.name}"
        try:
            if reload_modules and module_name in sys.modules:
                module = importlib.reload(sys.modules[module_name])
            else:
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
                name=bot_cfg.name,
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


__all__ = ["BotSpec", "discover_bot_factories", "_extract_factory"]
