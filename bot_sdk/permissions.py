from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from loguru import logger

from .async_zulip import AsyncClient
from .models import GetUserGroupsRequest, GetUserGroupsResponse, UserGroup
from .storage import BotStorage


SYSTEM_OWNER_GROUP = "role:owners"
SYSTEM_ADMIN_GROUP = "role:administrators"


@dataclass
class GroupCache:
    ts: float
    groups: List[UserGroup]


class PermissionPolicy:
    """
    Simple permissions helper backed by Zulip user groups with local caching.

    Default rules:
    - Owners and Administrators are privileged users
    - Custom ACLs can be stored under keys like "acl.stop" in storage
    """

    def __init__(self, client: AsyncClient, storage: Optional[BotStorage]) -> None:
        self.client = client
        self.storage = storage
        self._cache_ttl = 300.0  # seconds

    async def _load_groups(self) -> List[UserGroup]:
        """Load user groups from cache or Zulip API."""
        if self.storage:
            cache: Optional[Dict[str, Any]] = await self.storage.get("__user_groups__")
            if cache and (time.time() - float(cache.get("ts", 0))) < self._cache_ttl:
                try:
                    groups = [UserGroup.model_validate(g) for g in cache.get("groups", [])]
                    return groups
                except Exception:
                    pass
        # Fetch fresh groups
        try:
            resp: GetUserGroupsResponse = await self.client.get_user_groups(
                GetUserGroupsRequest(include_deactivated_groups=False)
            )
            groups = resp.user_groups or []
        except Exception as e:
            logger.warning(f"Failed to fetch user groups: {e}")
            groups = []
        if self.storage:
            await self.storage.put(
                "__user_groups__",
                {"ts": time.time(), "groups": [g.model_dump(exclude_none=True) for g in groups]},
            )
        return groups

    async def _members_of(self, group_name: str) -> Set[int]:
        groups = await self._load_groups()
        for g in groups:
            if g.name == group_name:
                return set(g.members or [])
        return set()

    async def is_owner(self, user_id: int) -> bool:
        return user_id in await self._members_of(SYSTEM_OWNER_GROUP)

    async def is_admin(self, user_id: int) -> bool:
        owners = await self._members_of(SYSTEM_OWNER_GROUP)
        admins = await self._members_of(SYSTEM_ADMIN_GROUP)
        return user_id in owners or user_id in admins

    async def can_stop_bot(self, user_id: int) -> bool:
        """Default policy: owners/admins can stop; extra ACL in storage key 'acl.stop'."""
        if await self.is_admin(user_id):
            return True
        if self.storage:
            acl = await self.storage.get("acl.stop", [])
            try:
                return user_id in set(acl)
            except Exception:
                return False
        return False


__all__ = ["PermissionPolicy"]
