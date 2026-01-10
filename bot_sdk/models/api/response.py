from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from .types import Channel, Event, User, UserGroup


class RegisterResponse(BaseModel):
    queue_id: str
    last_event_id: int
    result: str
    msg: str = ""

    model_config = ConfigDict(extra="allow")


class EventsResponse(BaseModel):
    result: str
    msg: str = ""
    events: List[Event] = []

    model_config = ConfigDict(extra="allow")


class SendMessageResponse(BaseModel):
    result: str
    msg: str = ""
    id: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class UserProfileResponse(User):
    result: str
    msg: str = ""

    model_config = ConfigDict(extra="allow", populate_by_name=True)


class SubscriptionsResponse(BaseModel):
    result: str
    msg: str = ""
    subscriptions: List[Channel] = []

    model_config = ConfigDict(extra="allow")


class ChannelResponse(BaseModel):
    result: str
    msg: str = ""
    stream: Channel

    model_config = ConfigDict(extra="allow")


class GetUserGroupsResponse(BaseModel):
    result: str
    msg: str = ""
    user_groups: List[UserGroup] = []

    model_config = ConfigDict(extra="allow")


__all__ = [
    "RegisterResponse",
    "EventsResponse",
    "SendMessageResponse",
    "UserProfileResponse",
    "SubscriptionsResponse",
    "ChannelResponse",
    "GetUserGroupsResponse",
]
