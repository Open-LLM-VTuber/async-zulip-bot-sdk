"""
Bot storage module with SQLite backend and dict-like interface.

Inspired by Zulip's bot_handler.storage API, providing:
- Dictionary-like get/put/contains interface
- Cached storage for minimizing database I/O
- Context manager for batch operations
- Automatic JSON marshaling/demarshaling
"""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiosqlite
from loguru import logger

_Missing = object()
_Deleted = object()


class BotStorage:
    """
    Persistent key-value storage backed by SQLite.
    
    Provides dictionary-like interface for bot state persistence.
    """

    def __init__(
        self,
        db_path: str | Path,
        namespace: str = "default",
        *,
        auto_cache: bool = False,
        auto_flush_interval: float = 5.0,
        auto_flush_retry: float = 1.0,
        auto_flush_max_retries: int = 3,
    ) -> None:
        """
        Initialize bot storage.
        
        Args:
            db_path: Path to SQLite database file
            namespace: Storage namespace to isolate different bots/contexts
        """
        self.db_path = Path(db_path)
        self.namespace = namespace
        self._initialized = False
        self._marshal = json.dumps
        self._demarshal = json.loads
        self._auto_cache = (
            _AutoCache(self, auto_flush_interval, auto_flush_retry, auto_flush_max_retries)
            if auto_cache
            else None
        )

    async def _init_db(self) -> None:
        """Initialize database schema if needed."""
        if self._initialized:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        db = await self._connect()
        try:
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS bot_storage (
                    namespace TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    PRIMARY KEY (namespace, key)
                )
                """
            )
            await db.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_namespace 
                ON bot_storage (namespace)
                """
            )
            await db.commit()
        finally:
            await db.close()

        self._initialized = True
        logger.debug(f"Initialized storage at {self.db_path} with namespace '{self.namespace}'")

    async def _connect(self) -> aiosqlite.Connection:
        """Open a connection with SQLite pragmas tuned for concurrency (WAL)."""
        db = await aiosqlite.connect(str(self.db_path))
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.execute("PRAGMA busy_timeout=3000;")  # 3s to yield to ORM transactions
        return db

    async def put(self, key: str, value: Any) -> None:
        """
        Store a value for the given key.
        
        Args:
            key: Storage key (string)
            value: Any JSON-serializable value
        """
        await self._ensure_ready()

        if self._auto_cache:
            self._auto_cache.put(key, value)
            return

        await self._put_direct(key, value)

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve value for the given key.
        
        Args:
            key: Storage key
            default: Default value if key doesn't exist
            
        Returns:
            Stored value or default
        """
        await self._ensure_ready()

        if self._auto_cache:
            cached = self._auto_cache.get(key)
            if cached is not _Missing:
                return cached if cached is not _Deleted else default

        row = await self._get_direct(key)
        if row is None:
            logger.trace(f"Storage [{self.namespace}]: get('{key}') -> default")
            return default

        if self._auto_cache:
            self._auto_cache.seed_from_db(key, row)

        return row

    async def contains(self, key: str) -> bool:
        """
        Check if key exists in storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if key exists, False otherwise
        """
        await self._ensure_ready()

        if self._auto_cache:
            cached = self._auto_cache.get(key)
            if cached is _Deleted:
                logger.trace(f"Storage [{self.namespace}]: contains('{key}') -> False (cached delete)")
                return False
            if cached is not _Missing:
                logger.trace(f"Storage [{self.namespace}]: contains('{key}') -> True (cached)")
                return True

        exists = await self._contains_direct(key)
        logger.trace(f"Storage [{self.namespace}]: contains('{key}') -> {exists}")
        return exists

    async def delete(self, key: str) -> bool:
        """
        Delete a key from storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if key was deleted, False if it didn't exist
        """
        await self._ensure_ready()

        if self._auto_cache:
            if not await self.contains(key):
                return False
            self._auto_cache.delete(key)
            return True

        deleted = await self._delete_direct(key)
        logger.trace(f"Storage [{self.namespace}]: delete('{key}') -> {deleted}")
        return deleted

    async def keys(self) -> List[str]:
        """
        Get all keys in current namespace.
        
        Returns:
            List of all keys
        """
        await self._ensure_ready()

        if self._auto_cache:
            await self._auto_cache.flush_pending()

        rows = await self._keys_direct()
        return rows

    async def clear(self) -> None:
        """Clear all data in current namespace."""
        await self._ensure_ready()

        if self._auto_cache:
            await self._auto_cache.clear()

        await self._clear_direct()
        logger.debug(f"Storage [{self.namespace}]: cleared all data")

    def set_marshal(self, marshal_fn: callable, demarshal_fn: callable) -> None:
        """
        Set custom marshaling functions for serialization.
        
        Args:
            marshal_fn: Function to serialize values (value -> str)
            demarshal_fn: Function to deserialize values (str -> value)
        """
        self._marshal = marshal_fn
        self._demarshal = demarshal_fn

    async def _ensure_ready(self) -> None:
        await self._init_db()
        if self._auto_cache:
            await self._auto_cache.ensure_started()

    async def _put_direct(self, key: str, value: Any) -> None:
        serialized = self._marshal(value)

        db = await self._connect()
        try:
            await db.execute(
                """
                INSERT INTO bot_storage (namespace, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value
                """,
                (self.namespace, key, serialized),
            )
            await db.commit()
        finally:
            await db.close()

        logger.trace(f"Storage [{self.namespace}]: put('{key}', ...)")

    async def _get_direct(self, key: str) -> Any:
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT value FROM bot_storage WHERE namespace = ? AND key = ?",
                (self.namespace, key),
            ) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()

        if row is None:
            return None

        value = self._demarshal(row[0])
        logger.trace(f"Storage [{self.namespace}]: get('{key}') -> found")
        return value

    async def _contains_direct(self, key: str) -> bool:
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT 1 FROM bot_storage WHERE namespace = ? AND key = ? LIMIT 1",
                (self.namespace, key),
            ) as cursor:
                row = await cursor.fetchone()
        finally:
            await db.close()
        return row is not None

    async def _delete_direct(self, key: str) -> bool:
        db = await self._connect()
        try:
            cursor = await db.execute(
                "DELETE FROM bot_storage WHERE namespace = ? AND key = ?",
                (self.namespace, key),
            )
            await db.commit()
            return cursor.rowcount > 0
        finally:
            await db.close()

    async def _keys_direct(self) -> List[str]:
        db = await self._connect()
        try:
            async with db.execute(
                "SELECT key FROM bot_storage WHERE namespace = ?",
                (self.namespace,),
            ) as cursor:
                rows = await cursor.fetchall()
        finally:
            await db.close()
        return [row[0] for row in rows]

    async def _clear_direct(self) -> None:
        db = await self._connect()
        try:
            await db.execute(
                "DELETE FROM bot_storage WHERE namespace = ?",
                (self.namespace,),
            )
            await db.commit()
        finally:
            await db.close()

    @asynccontextmanager
    async def cached(self, keys: Optional[List[str]] = None):
        """
        Context manager for cached storage operations.
        
        Minimizes database round-trips by:
        - Pre-fetching specified keys
        - Batching writes until flush or context exit
        
        Args:
            keys: List of keys to pre-fetch (None = don't pre-fetch)
            
        Yields:
            CachedStorage instance
            
        Example:
            async with storage.cached(["counter", "users"]) as cache:
                count = cache.get("counter", 0)
                cache.put("counter", count + 1)
                # Changes are flushed on exit
        """
        cache = CachedStorage(self, keys or [])
        await cache._prefetch()
        try:
            yield cache
        finally:
            await cache.flush()


class CachedStorage:
    """
    Cached wrapper around BotStorage for batch operations.
    
    Minimizes database I/O by caching reads and batching writes.
    """

    def __init__(self, storage: BotStorage, prefetch_keys: List[str]) -> None:
        self._storage = storage
        self._prefetch_keys = prefetch_keys
        self._cache: Dict[str, Any] = {}
        self._dirty: Set[str] = set()  # Keys that need to be written back

    async def _prefetch(self) -> None:
        """Pre-fetch specified keys from storage."""
        for key in self._prefetch_keys:
            try:
                value = await self._storage.get(key)
                if value is not None:
                    self._cache[key] = value
            except Exception as e:
                logger.warning(f"Failed to prefetch key '{key}': {e}")

    def put(self, key: str, value: Any) -> None:
        """
        Store value in cache (will be flushed later).
        
        Args:
            key: Storage key
            value: Any JSON-serializable value
        """
        self._cache[key] = value
        self._dirty.add(key)

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from cache.
        
        Note: Only returns values that are in cache. If you need a key that wasn't
        pre-fetched, you must include it in the cached() keys list.
        
        Args:
            key: Storage key
            default: Default value if key doesn't exist in cache
            
        Returns:
            Cached value or default
        """
        if key in self._cache:
            return self._cache[key]

        # Not in cache - this means the key wasn't pre-fetched
        if key not in self._prefetch_keys:
            logger.warning(
                f"Cache miss for '{key}' - key was not pre-fetched. "
                "Include it in cached() keys list for better performance."
            )
        
        return default

    def contains(self, key: str) -> bool:
        """
        Check if key exists in cache.
        
        Note: Only checks cache, not underlying storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if key is in cache
        """
        return key in self._cache

    async def flush_one(self, key: str) -> None:
        """
        Flush a single key's changes to storage.
        
        Args:
            key: Storage key to flush
        """
        if key not in self._dirty:
            return

        if key in self._cache:
            await self._storage.put(key, self._cache[key])
            self._dirty.discard(key)
            logger.trace(f"Flushed key '{key}' to storage")

    async def flush(self) -> None:
        """Flush all pending changes to storage."""
        if not self._dirty:
            return

        logger.debug(f"Flushing {len(self._dirty)} keys to storage")

        for key in list(self._dirty):
            await self.flush_one(key)


__all__ = ["BotStorage", "CachedStorage"]


_Missing = object()
_Deleted = object()


class _AutoCache:
    """Always-on cache with periodic flush to underlying storage.

    Designed to yield to ORM usage by retrying when locked.
    """

    def __init__(self, storage: BotStorage, interval: float, retry_delay: float, max_retries: int) -> None:
        self._storage = storage
        self._interval = interval
        self._retry_delay = retry_delay
        self._max_retries = max_retries
        self._cache: Dict[str, Any] = {}
        self._dirty: Set[str] = set()
        self._deleted: Set[str] = set()
        self._task: Optional[asyncio.Task] = None
        self._running = False

    async def ensure_started(self) -> None:
        if self._task and not self._task.done():
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    def put(self, key: str, value: Any) -> None:
        self._cache[key] = value
        self._dirty.add(key)
        self._deleted.discard(key)

    def delete(self, key: str) -> None:
        self._cache.pop(key, None)
        self._deleted.add(key)
        self._dirty.add(key)

    def get(self, key: str) -> Any:
        if key in self._deleted:
            return _Deleted
        if key in self._cache:
            return self._cache[key]
        return _Missing

    def seed_from_db(self, key: str, value: Any) -> None:
        # Only seed when not already dirty to avoid overwriting pending writes
        if key not in self._dirty:
            self._cache[key] = value

    async def flush_pending(self) -> None:
        if not self._dirty:
            return
        pending = list(self._dirty)
        for key in pending:
            await self._flush_one_with_retry(key)

    async def clear(self) -> None:
        self._cache.clear()
        self._dirty.clear()
        self._deleted.clear()

    async def _flush_one_with_retry(self, key: str) -> None:
        attempts = 0
        while attempts < self._max_retries:
            try:
                if key in self._deleted:
                    await self._storage._delete_direct(key)
                elif key in self._cache:
                    await self._storage._put_direct(key, self._cache[key])
                self._dirty.discard(key)
                if key in self._deleted:
                    self._deleted.discard(key)
                return
            except Exception as exc:
                attempts += 1
                if attempts >= self._max_retries:
                    logger.warning(
                        f"AutoCache failed to flush key '{key}' after {attempts} attempts: {exc}"
                    )
                    return
                await asyncio.sleep(self._retry_delay)

    async def _run(self) -> None:
        try:
            while self._running:
                await asyncio.sleep(self._interval)
                await self.flush_pending()
        except asyncio.CancelledError:
            # Flush once on cancel
            await self.flush_pending()
            raise
