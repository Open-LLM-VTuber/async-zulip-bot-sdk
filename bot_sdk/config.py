from __future__ import annotations

from typing import Any, List, Optional

from ruamel.yaml import YAML
from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    name: str
    module: Optional[str] = None
    class_name: Optional[str] = None
    enabled: bool = True
    config: dict[str, Any] = Field(default_factory=dict)


class AppConfig(BaseModel):
    zuliprc: str = "zuliprc"
    bots: List[BotConfig] = Field(default_factory=list)


def load_config(path: str) -> AppConfig:
    yaml = YAML(typ="safe")
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.load(f) or {}
    return AppConfig.model_validate(data)


__all__ = ["AppConfig", "BotConfig", "load_config"]
