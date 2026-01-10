from __future__ import annotations

from typing import Any, List, Optional

from ruamel.yaml import YAML
from pydantic import BaseModel, Field
from pathlib import Path


class BotConfig(BaseModel):
    name: str
    module: Optional[str] = None
    class_name: Optional[str] = None
    enabled: bool = True
    zuliprc: Optional[str] = None
    event_types: list[str] = Field(default_factory=lambda: ["message"])
    config: dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseModel):
    bots: List[BotConfig] = Field(default_factory=list)


def load_config(path: str | Path, model: type[BaseModel]) -> BaseModel:
    yaml = YAML(typ="safe")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f) or {}
    return model.model_validate(data)


# Per-bot local configuration (stored next to the bot code by default)
class BotLocalConfig(BaseModel):
    """Per-bot settings stored in YAML.

    - owner_user_id: explicit bot owner (Zulip user_id), independent of org owners
    - role_levels: mapping of role name -> numeric level (higher is more privileged)
    - settings: extra arbitrary settings for the bot
    """

    owner_user_id: Optional[int] = None
    role_levels: dict[str, int] = Field(
        default_factory=lambda: {
            "user": 1,
            "admin": 50,
            "owner": 100,
            "bot_owner": 200,
        }
    )
    settings: dict[str, Any] = Field(default_factory=dict)


def load_bot_local_config(path: str | Path) -> BotLocalConfig:
    yaml = YAML(typ="safe")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f) or {}
    return BotLocalConfig.model_validate(data)


def save_bot_local_config(path: str | Path, config: BotLocalConfig) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(exclude_none=True), f)


__all__ = [
    "AppConfig",
    "BotConfig",
    "load_config",
    "BotLocalConfig",
    "load_bot_local_config",
    "save_bot_local_config",
]
