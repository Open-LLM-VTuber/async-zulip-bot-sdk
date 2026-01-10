import asyncio
import importlib
import inspect
from contextlib import AsyncExitStack
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, List, Optional

from loguru import logger

from bot_sdk import BaseBot, BotRunner, setup_logging
from bot_sdk.config import AppConfig, load_config


@dataclass
class BotSpec:
    factory: Callable[[Any], BaseBot]
    zuliprc: str
    event_types: List[str]


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
        BotRunner(spec.factory, client_kwargs={"config_file": spec.zuliprc}, event_types=spec.event_types)
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


def main() -> None:
    setup_logging("DEBUG")
    config_path = Path("bots.yaml")
    if not config_path.exists():
        raise FileNotFoundError("bots.yaml not found; please create it to list bots to launch")
    app_config = load_config(str(config_path), AppConfig)
    bot_specs = discover_bot_factories(app_config)
    asyncio.run(run_all_bots(bot_specs))


if __name__ == "__main__":
    main()