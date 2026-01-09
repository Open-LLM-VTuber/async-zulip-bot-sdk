"""
Bot storage module with SQLite backend and dict-like interface.

Inspired by Zulip's bot_handler.storage API, providing:
- Dictionary-like get/put/contains interface
- Cached storage for minimizing database I/O
- Context manager for batch operations
- Automatic JSON marshaling/demarshaling
"""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import aiosqlite
from loguru import logger


class BotStorage:
    """
    Persistent key-value storage backed by SQLite.
    
    Provides dictionary-like interface for bot state persistence.
    """

    def __init__(self, db_path: str | Path, namespace: str = "default") -> None:
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

    async def _init_db(self) -> None:
        """Initialize database schema if needed."""
        if self._initialized:
            return

        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        async with aiosqlite.connect(str(self.db_path)) as db:
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

        self._initialized = True
        logger.debug(f"Initialized storage at {self.db_path} with namespace '{self.namespace}'")

    async def put(self, key: str, value: Any) -> None:
        """
        Store a value for the given key.
        
        Args:
            key: Storage key (string)
            value: Any JSON-serializable value
        """
        await self._init_db()

        serialized = self._marshal(value)

        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute(
                """
                INSERT INTO bot_storage (namespace, key, value)
                VALUES (?, ?, ?)
                ON CONFLICT(namespace, key) DO UPDATE SET value = excluded.value
                """,
                (self.namespace, key, serialized),
            )
            await db.commit()

        logger.trace(f"Storage [{self.namespace}]: put('{key}', ...)")

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieve value for the given key.
        
        Args:
            key: Storage key
            default: Default value if key doesn't exist
            
        Returns:
            Stored value or default
        """
        await self._init_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(
                "SELECT value FROM bot_storage WHERE namespace = ? AND key = ?",
                (self.namespace, key),
            ) as cursor:
                row = await cursor.fetchone()

        if row is None:
            logger.trace(f"Storage [{self.namespace}]: get('{key}') -> default")
            return default

        value = self._demarshal(row[0])
        logger.trace(f"Storage [{self.namespace}]: get('{key}') -> found")
        return value

    async def contains(self, key: str) -> bool:
        """
        Check if key exists in storage.
        
        Args:
            key: Storage key
            
        Returns:
            True if key exists, False otherwise
        """
        await self._init_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(
                "SELECT 1 FROM bot_storage WHERE namespace = ? AND key = ? LIMIT 1",
                (self.namespace, key),
            ) as cursor:
                row = await cursor.fetchone()

        exists = row is not None
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
        await self._init_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            cursor = await db.execute(
                "DELETE FROM bot_storage WHERE namespace = ? AND key = ?",
                (self.namespace, key),
            )
            await db.commit()
            deleted = cursor.rowcount > 0

        logger.trace(f"Storage [{self.namespace}]: delete('{key}') -> {deleted}")
        return deleted

    async def keys(self) -> List[str]:
        """
        Get all keys in current namespace.
        
        Returns:
            List of all keys
        """
        await self._init_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            async with db.execute(
                "SELECT key FROM bot_storage WHERE namespace = ?",
                (self.namespace,),
            ) as cursor:
                rows = await cursor.fetchall()

        return [row[0] for row in rows]

    async def clear(self) -> None:
        """Clear all data in current namespace."""
        await self._init_db()

        async with aiosqlite.connect(str(self.db_path)) as db:
            await db.execute(
                "DELETE FROM bot_storage WHERE namespace = ?",
                (self.namespace,),
            )
            await db.commit()

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
