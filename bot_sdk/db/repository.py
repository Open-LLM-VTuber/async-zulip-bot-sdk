from __future__ import annotations

from typing import Generic, Iterable, Optional, Sequence, TypeVar

from sqlalchemy import Select, delete, select
from sqlalchemy.ext.asyncio import AsyncSession

ModelT = TypeVar("ModelT")

__all__ = ["AsyncRepository"]


class AsyncRepository(Generic[ModelT]):
    """Lightweight base repository with common CRUD helpers.

    Subclass and set ``model`` to your ORM mapped class.
    Methods open their own unit-of-work on the provided session.
    """

    model: type[ModelT]

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, pk: object) -> Optional[ModelT]:
        return await self.session.get(self.model, pk)

    async def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance

    async def delete(self, pk: object) -> bool:
        instance = await self.get(pk)
        if instance is None:
            return False
        await self.session.delete(instance)
        await self.session.flush()
        return True

    async def list(self, *, limit: int = 100, offset: int = 0) -> Sequence[ModelT]:
        stmt: Select[ModelT] = select(self.model).limit(limit).offset(offset)
        rows = await self.session.execute(stmt)
        return rows.scalars().all()
