from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal


class StreamMessageRequest(BaseModel):
    type: Literal["stream"] = "stream"
    to: int | str | List[int] | List[str]
    topic: str
    content: str

    model_config = ConfigDict(extra="allow")


class PrivateMessageRequest(BaseModel):
    type: Literal["private"] = "private"
    to: List[int] | List[str]
    content: str

    model_config = ConfigDict(extra="allow")


__all__ = ["StreamMessageRequest", "PrivateMessageRequest"]
