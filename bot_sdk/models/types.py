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

class Channel(BaseModel):
    stream_id: int
    name: str
    description: Optional[str] = None
    rendered_description: Optional[str] = None
    invite_only: Optional[bool] = None
    is_web_public: Optional[bool] = None
    history_public_to_subscribers: Optional[bool] = None
    stream_post_policy: Optional[int] = None
    message_retention_days: Optional[int] = None
    is_announcement_only: Optional[bool] = None
    first_message_id: Optional[int] = None
    creation_date: Optional[int] = None
    can_remove_subscribers_group: Optional[int] = None
    date_created: Optional[int] = None  # some APIs return date_created
    stream_weekly_traffic: Optional[int] = None

    model_config = ConfigDict(extra="allow")


class GroupSettingValue(BaseModel):
    """A group-setting value that can be either a group ID or an object with direct members/subgroups."""
    direct_members: Optional[List[int]] = None
    direct_subgroups: Optional[List[int]] = None

    model_config = ConfigDict(extra="allow")


class UserGroup(BaseModel):
    """Represents a user group in Zulip organization."""
    id: int
    name: str
    description: str
    members: List[int]
    direct_subgroup_ids: List[int]
    is_system_group: bool
    creator_id: Optional[int] = None
    date_created: Optional[int] = None
    can_add_members_group: Optional[Union[int, GroupSettingValue]] = None
    can_join_group: Optional[Union[int, GroupSettingValue]] = None
    can_leave_group: Optional[Union[int, GroupSettingValue]] = None
    can_manage_group: Optional[Union[int, GroupSettingValue]] = None
    can_mention_group: Optional[Union[int, GroupSettingValue]] = None
    can_remove_members_group: Optional[Union[int, GroupSettingValue]] = None
    deactivated: Optional[bool] = None

    model_config = ConfigDict(extra="allow")


__all__ = ["Message", "Event", "PrivateRecipient", "ProfileFieldValue", "User", "Channel", "GroupSettingValue", "UserGroup"]