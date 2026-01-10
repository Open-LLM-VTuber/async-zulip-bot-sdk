from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, ConfigDict


class DataModel(BaseModel):
    """Base Pydantic model for SDK-side data structures.

    - Disallows unknown fields by default
    - Ready to be extended by bot developers for their own data schemas
    """

    model_config = ConfigDict(extra="forbid")


class Timestamped(DataModel):
    created_at: datetime | None = None
    updated_at: datetime | None = None


__all__ = ["DataModel", "Timestamped"]
