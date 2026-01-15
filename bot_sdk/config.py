from __future__ import annotations

from typing import Any, List, Optional

from ruamel.yaml import YAML
from pydantic import BaseModel, Field
from pathlib import Path


class StorageConfig(BaseModel):
    """Per-bot storage options for KV backend.

    auto_cache: enable always-on cache with periodic flush
    auto_flush_interval: seconds between flush attempts
    auto_flush_retry: retry delay after a flush failure (e.g., DB locked)
    auto_flush_max_retries: max retries per key per flush cycle
    """

    auto_cache: bool = False
    auto_flush_interval: float = 5.0
    auto_flush_retry: float = 1.0
    auto_flush_max_retries: int = 3


class BotConfig(BaseModel):
    name: str
    module: Optional[str] = None
    class_name: Optional[str] = None
    enabled: bool = True
    zuliprc: Optional[str] = None
    event_types: list[str] = Field(default_factory=lambda: ["message"])
    config: dict[str, Any] = Field(default_factory=dict)
    storage: Optional[StorageConfig] = None


class AppConfig(BaseModel):
    bots: List[BotConfig] = Field(default_factory=list)


def load_config(path: str | Path, model: type[BaseModel]) -> BaseModel:
    yaml = YAML(typ="safe")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f) or {}
    return model.model_validate(data)

def save_config(path: str | Path, config: BaseModel) -> None:
    yaml = YAML()
    yaml.default_flow_style = False
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(config.model_dump(exclude_none=True), f)


# Per-bot local configuration (stored next to the bot code by default)
class BotLocalConfig(BaseModel):
    """Per-bot settings stored in YAML.

    - owner_user_id: explicit bot owner (Zulip user_id), independent of org owners
    - role_levels: mapping of role name -> numeric level (higher is more privileged)
    - settings: extra arbitrary settings for the bot
    - language: default language/locale code for this bot (e.g. "en", "zh")

    Optional overrides (when set) take precedence over BaseBot class attributes:
    - command_prefixes, enable_mention_commands, auto_help_command
    - enable_storage, storage_path, storage (StorageConfig)
    - enable_orm, orm_db_path
    """

    owner_user_id: Optional[int] = None
    language: str = "en"
    role_levels: dict[str, int] = Field(
        default_factory=lambda: {
            "user": 1,
            "admin": 50,
            "owner": 100,
            "bot_owner": 200,
        }
    )
    settings: dict[str, Any] = Field(default_factory=dict)

    # Optional overrides for BaseBot defaults
    command_prefixes: Optional[tuple[str, ...]] = Field(default_factory=lambda: ("!",))
    enable_mention_commands: Optional[bool] = True
    auto_help_command: Optional[bool] = True
    enable_storage: Optional[bool] = True
    storage_path: Optional[str] = None
    storage: Optional[StorageConfig] = Field(default_factory=StorageConfig)
    enable_orm: Optional[bool] = False
    orm_db_path: Optional[str] = None


def load_bot_local_config(path: str | Path) -> BotLocalConfig:
    return load_config(path, BotLocalConfig)


def save_bot_local_config(path: str | Path, config: BotLocalConfig) -> None:
    save_config(path, config)


__all__ = [
    "AppConfig",
    "BotConfig",
    "StorageConfig",
    "load_config",
    "BotLocalConfig",
    "load_bot_local_config",
    "save_bot_local_config",
]
