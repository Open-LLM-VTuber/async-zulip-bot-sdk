from __future__ import annotations

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict
from typing_extensions import Literal


class PrivateRecipient(BaseModel):
    id: int
    email: Optional[str] = None
    full_name: Optional[str] = None
    short_name: Optional[str] = None
    type: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class Message(BaseModel):
    id: int
    type: Literal["stream", "private"]
    content: str
    sender_id: int
    sender_email: str
    sender_full_name: str
    client: Optional[str] = None
    stream_id: Optional[int] = None
    display_recipient: Optional[Union[List[PrivateRecipient], str]] = None
    subject: Optional[str] = None
    topic: Optional[str] = None

    model_config = ConfigDict(extra="allow")

    @property
    def topic_or_subject(self) -> Optional[str]:
        return self.subject or self.topic


class Event(BaseModel):
    id: int
    type: str
    message: Optional[Message] = None
    op: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class ProfileFieldValue(BaseModel):
    value: Optional[str] = None
    rendered_value: Optional[str] = None

    model_config = ConfigDict(extra="allow")


class User(BaseModel):
    email: str
    user_id: int
    full_name: Optional[str] = None
    delivery_email: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_version: Optional[int] = None
    is_admin: Optional[bool] = None
    is_owner: Optional[bool] = None
    is_guest: Optional[bool] = None
    is_bot: Optional[bool] = None
    role: Optional[int] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    date_joined: Optional[str] = None
    is_imported_stub: Optional[bool] = None
    profile_data: Optional[Dict[str, ProfileFieldValue]] = None
    max_message_id: Optional[int] = None

    model_config = ConfigDict(extra="allow")


__all__ = ["Message", "Event", "PrivateRecipient", "ProfileFieldValue", "User"]
