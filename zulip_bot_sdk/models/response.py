from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict

from .types import Event, ProfileFieldValue, User


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


__all__ = [
    "RegisterResponse",
    "EventsResponse",
    "SendMessageResponse",
    "UserProfileResponse",
]
