from __future__ import annotations

from typing import List

from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal, Optional


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
    
    
class UpdatePresenceRequest(BaseModel):
    status: Literal["active", "idle"]
    new_user_input: Optional[bool] = None
    ping_only: Optional[bool] = None
    last_update_id: Optional[int] = None
    history_limit_days: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class GetUserGroupsRequest(BaseModel):
    include_deactivated_groups: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


__all__ = ["StreamMessageRequest", "PrivateMessageRequest", "UpdatePresenceRequest", "GetUserGroupsRequest"]