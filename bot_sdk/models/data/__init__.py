from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DataModel(BaseModel):
    """Base Pydantic model for SDK-side data structures.

    - Disallows unknown fields by default
    - Validates assignment to keep objects consistent
    - Ready to be extended by bot developers for their own data schemas
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Timestamped(DataModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class IDModel(DataModel):
    """Provides a string identifier field.

    Using str keeps compatibility with UUID/text IDs; override or extend as needed.
    """

    id: str


class SoftDelete(DataModel):
    """Tracks soft-deletion state and time."""

    deleted: bool = False
    deleted_at: datetime | None = None


__all__ = ["DataModel", "Timestamped", "IDModel", "SoftDelete"]
