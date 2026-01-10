from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

__all__ = [
    "Base",
    "make_sqlite_url",
    "create_engine",
    "create_sessionmaker",
    "session_scope",
]


class Base(DeclarativeBase):
    """Declarative base for ORM models."""


def make_sqlite_url(db_path: str | Path) -> str:
    """Build an async SQLite URL using aiosqlite driver."""
    path = Path(db_path).expanduser().resolve()
    return f"sqlite+aiosqlite:///{path.as_posix()}"


def create_engine(url: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine.

    Defaults are tuned for SQLite; adjust pool settings if swapping drivers.
    """
    return create_async_engine(url, echo=echo, future=True)


def create_sessionmaker(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    """Return an async sessionmaker bound to the given engine."""
    return async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def session_scope(session_factory: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    """Async context manager that yields a session and commits/rolls back safely."""
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()
