# Bot Storage

Lightweight SQLite-backed storage with a dict-like interface, inspired by the official Zulip bot SDK.

## Features

- ✅ Dict-style interface: `get()`, `put()`, `contains()`, etc.
- ✅ Auto-initialization: no manual database/table setup
- ✅ Caching: `cached()` context manager to cut down DB I/O
- ✅ JSON serialization: Python objects handled automatically
- ✅ Namespace isolation: multiple bots can share one DB file safely
- ✅ Fully async: built on `aiosqlite`, non-blocking for the event loop

## Quickstart

### Basic usage

In a `BaseBot` subclass, `self.storage` is ready to use:

```python
from bot_sdk import BaseBot
from bot_sdk.models import Message

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        # Directly access storage
        count = await self.storage.get("counter", 0)
        count += 1
        await self.storage.put("counter", count)

        await self.send_reply(message, f"Count: {count}")
```

### Using the cache (recommended)

For multiple reads/writes, `cached()` can dramatically reduce DB access:

```python
async def on_message(self, message: Message) -> None:
    # Use the cache context manager
    async with self.storage.cached(["counter", "users"]) as cache:
        # These operations hit the in-memory cache only
        counter = cache.get("counter", 0)
        users = cache.get("users", [])

        counter += 1
        users.append(message.sender_id)

        cache.put("counter", counter)
        cache.put("users", users)
        # Changes flush to the DB when exiting
```

## API Reference

### BotStorage

#### Methods

##### `async put(key: str, value: Any) -> None`

Store a key-value pair. Values are JSON-serialized automatically.

```python
await storage.put("name", "Alice")
await storage.put("settings", {"theme": "dark", "lang": "en"})
await storage.put("count", 42)
```

##### `async get(key: str, default=None) -> Any`

Get the value for a key, or return `default` if missing.

```python
name = await storage.get("name")  # "Alice"
score = await storage.get("score", 0)  # 0 if not exists
settings = await storage.get("settings")  # dict
```

##### `async contains(key: str) -> bool`

Check whether a key exists.

```python
if await storage.contains("user_id"):
    user_id = await storage.get("user_id")
```

##### `async delete(key: str) -> bool`

Delete a key and return whether the deletion succeeded.

```python
deleted = await storage.delete("temp_data")
```

##### `async keys() -> List[str]`

List all keys under the current namespace.

```python
all_keys = await storage.keys()
print(f"Stored keys: {all_keys}")
```

##### `async clear() -> None`

Clear all data under the current namespace.

```python
await storage.clear()  # Dangerous!
```

##### `cached(keys: List[str] = None)`

Return a caching context manager.

```python
async with storage.cached(["key1", "key2"]) as cache:
    # Use cache instead of storage
    val1 = cache.get("key1", 0)
    cache.put("key1", val1 + 1)
```

### CachedStorage

Used inside `storage.cached()`.

#### Methods

##### `put(key: str, value: Any) -> None`

Store into the cache (note: **not async**).

```python
cache.put("key", "value")
```

##### `get(key: str, default=None) -> Any`

Read from the cache (note: **not async**).

```python
value = cache.get("key", "default_value")
```

##### `contains(key: str) -> bool`

Check if the cache has the key (cache only, no DB lookup).

```python
if cache.contains("key"):
    value = cache.get("key")
```

##### `async flush_one(key: str) -> None`

Immediately persist a single cached key to the DB.

```python
cache.put("important", data)
await cache.flush_one("important")  # Persist now
```

##### `async flush() -> None`

Persist all cached changes.

```python
await cache.flush()  # Usually called automatically by the context manager
```

## Configuration

> ⚠️ Since v1.0.0, storage-related flags such as `enable_storage` and `storage_path` are loaded from each bot's `bot.yaml` (`BotLocalConfig`). Class-level attributes are ignored.

### Custom storage path (bot.yaml)

```yaml
# bots/my_bot/bot.yaml
enable_storage: true
storage_path: "data/my_bot.db"  # Custom KV database path
```

### Disable storage (bot.yaml)

```yaml
# bots/my_bot/bot.yaml
enable_storage: false  # Turn off storage entirely
```

### Custom serialization

```python
import pickle

async def on_start(self):
    # Use pickle instead of JSON
    self.storage.set_marshal(
        marshal_fn=lambda obj: pickle.dumps(obj).hex(),
        demarshal_fn=lambda s: pickle.loads(bytes.fromhex(s))
    )
```

### Always-on auto cache (bots.yaml)

Configure per-bot storage behavior in `bots.yaml` via `storage`:

```yaml
bots:
    - name: dev_bot
        module: bots.dev_bot
        class_name: TranslatorBot
        storage:
            auto_cache: true
            auto_flush_interval: 5.0
            auto_flush_retry: 1.0
            auto_flush_max_retries: 3
```

- Auto-cache keeps a memory cache alive and flushes periodically.
- Flush retries are useful when the same SQLite file is shared with ORM writes; flush will back off when the DB is busy.
- BotStorage sets SQLite WAL + `synchronous=NORMAL` + `busy_timeout=3000` by default to reduce lock contention.

## Usage patterns

### Counter

```python
async with self.storage.cached(["counter"]) as cache:
    count = cache.get("counter", 0)
    cache.put("counter", count + 1)
```

### User state tracking

```python
async with self.storage.cached(["users"]) as cache:
    users = cache.get("users", {})
    users[message.sender_id] = {
        "name": message.sender_full_name,
        "last_seen": time.time()
    }
    cache.put("users", users)
```

### Config management

```python
# Read
config = await self.storage.get("config", {
    "lang": "en",
    "timezone": "UTC"
})

# Update
config["lang"] = "en"
await self.storage.put("config", config)
```

### Ephemeral cache

```python
# Store data with a TTL (you manage expiry yourself)
cache_data = await self.storage.get("cache", {})
cache_data["key"] = {
    "value": "data",
    "expires": time.time() + 3600
}
await self.storage.put("cache", cache_data)
```

## Performance tips

1. **Prefer the cache context**: For batch ops, `cached()` can collapse multiple DB hits into just two (initial load + final flush).
2. **Prefetch critical keys**: Pass the keys you need to `cached()` to avoid cache misses.
3. **Avoid huge objects**: SQLite fits small/medium data; put large blobs on the filesystem instead.
4. **Clean up periodically**: Consider `delete()` for old records when appropriate.

## Example: full poll bot

```python
from bot_sdk import BaseBot
from bot_sdk.models import Message

class PollBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        content = message.content.strip()

        if content.startswith("/poll "):
            # Create a poll
            question = content[6:].strip()
            async with self.storage.cached(["current_poll"]) as cache:
                cache.put("current_poll", {
                    "question": question,
                    "votes": {"yes": 0, "no": 0}
                })
            await self.send_reply(message, f"\ud83d\udcca Poll: {question}\n/yes or /no to vote!")

        elif content == "/yes" or content == "/no":
            # Vote
            async with self.storage.cached(["current_poll", "voters"]) as cache:
                poll = cache.get("current_poll")
                if not poll:
                    await self.send_reply(message, "No active poll!")
                    return

                voters = cache.get("voters", [])
                if message.sender_id in voters:
                    await self.send_reply(message, "You already voted!")
                    return

                option = "yes" if content == "/yes" else "no"
                poll["votes"][option] += 1
                voters.append(message.sender_id)

                cache.put("current_poll", poll)
                cache.put("voters", voters)

            await self.send_reply(message, f"\u2705 Voted {option}!")

        elif content == "/results":
            # Show results
            poll = await self.storage.get("current_poll")
            if not poll:
                await self.send_reply(message, "No active poll!")
                return

            results = f"""
\ud83d\udcca **{poll['question']}**

\ud83d\udc4d Yes: {poll['votes']['yes']}
\ud83d\udc4e No: {poll['votes']['no']}
            """.strip()
            await self.send_reply(message, results)
```

## Notes

- Storage is namespaced by bot user ID
- `CachedStorage.get()` and `put()` are synchronous inside the cache context
- `contains()` inside the cache context checks cache only (no DB hit)
- DB files default to the `bot_data/` directory
- All values are JSON-serialized automatically; keep values JSON-friendly
- If you use ORM tables, keep their migrations per bot (separate Alembic dirs); reserve SDK-level migrations for shared tables only.

## Related docs

- [BaseBot API](base_bot.md)
- [Command system](commands.md)
- [Quickstart](quickstart.md)
