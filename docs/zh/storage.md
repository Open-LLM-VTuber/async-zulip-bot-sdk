# Bot Storage

轻量级 SQLite 存储，提供类似字典的接口，灵感来自 Zulip 官方 bot SDK。

## 特性

- ✅ **字典式接口**：`get()`, `put()`, `contains()` 等方法
- ✅ **自动初始化**：无需手动创建数据库或表
- ✅ **缓存机制**：通过 `cached()` 上下文管理器减少数据库 I/O
- ✅ **JSON 序列化**：自动处理 Python 对象的序列化
- ✅ **命名空间隔离**：多个 bot 可共享同一数据库文件
- ✅ **完全异步**：基于 `aiosqlite`，不会阻塞事件循环

## 快速开始

### 基础用法

在 `BaseBot` 子类中，`self.storage` 自动可用：

```python
from bot_sdk import BaseBot
from bot_sdk.models import Message

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        # 直接访问存储
        count = await self.storage.get("counter", 0)
        count += 1
        await self.storage.put("counter", count)
        
        await self.send_reply(message, f"Count: {count}")
```

### 使用缓存（推荐）

对于需要多次读写的场景，使用 `cached()` 可以显著减少数据库访问：

```python
async def on_message(self, message: Message) -> None:
    # 使用缓存上下文管理器
    async with self.storage.cached(["counter", "users"]) as cache:
        # 这些操作只访问内存缓存
        counter = cache.get("counter", 0)
        users = cache.get("users", [])
        
        counter += 1
        users.append(message.sender_id)
        
        cache.put("counter", counter)
        cache.put("users", users)
        # 退出时自动批量写入数据库
```

## API 参考

### BotStorage

#### 方法

##### `async put(key: str, value: Any) -> None`

存储键值对。值会被自动 JSON 序列化。

```python
await storage.put("name", "Alice")
await storage.put("settings", {"theme": "dark", "lang": "zh"})
await storage.put("count", 42)
```

##### `async get(key: str, default=None) -> Any`

获取键对应的值，如果不存在返回 `default`。

```python
name = await storage.get("name")  # "Alice"
score = await storage.get("score", 0)  # 0 if not exists
settings = await storage.get("settings")  # dict
```

##### `async contains(key: str) -> bool`

检查键是否存在。

```python
if await storage.contains("user_id"):
    user_id = await storage.get("user_id")
```

##### `async delete(key: str) -> bool`

删除键，返回是否删除成功。

```python
deleted = await storage.delete("temp_data")
```

##### `async keys() -> List[str]`

获取当前命名空间下的所有键。

```python
all_keys = await storage.keys()
print(f"Stored keys: {all_keys}")
```

##### `async clear() -> None`

清空当前命名空间的所有数据。

```python
await storage.clear()  # 危险操作！
```

##### `cached(keys: List[str] = None)`

返回缓存上下文管理器。

```python
async with storage.cached(["key1", "key2"]) as cache:
    # 使用 cache 代替 storage
    val1 = cache.get("key1", 0)
    cache.put("key1", val1 + 1)
```

### CachedStorage

在 `storage.cached()` 上下文中使用。

#### 方法

##### `put(key: str, value: Any) -> None`

存储到缓存（注意：**不是异步方法**）。

```python
cache.put("key", "value")
```

##### `get(key: str, default=None) -> Any`

从缓存读取（注意：**不是异步方法**）。

```python
value = cache.get("key", "default_value")
```

##### `contains(key: str) -> bool`

检查缓存中是否有该键（仅检查缓存，不查数据库）。

```python
if cache.contains("key"):
    value = cache.get("key")
```

##### `async flush_one(key: str) -> None`

立即将某个键的更改写入数据库。

```python
cache.put("important", data)
await cache.flush_one("important")  # 立即持久化
```

##### `async flush() -> None`

将所有更改写入数据库。

```python
await cache.flush()  # 通常由上下文管理器自动调用
```

## 配置

> ⚠️ 自 v1.0.0 起，与存储相关的配置（如 `enable_storage`、`storage_path`）从每个 Bot 目录下的 `bot.yaml`（`BotLocalConfig`）读取，类属性不再生效。

### 自定义存储路径（bot.yaml）

```yaml
# bots/my_bot/bot.yaml
enable_storage: true
storage_path: "data/my_bot.db"  # 自定义 KV 数据库存放路径
```

### 禁用存储（bot.yaml）

```yaml
# bots/my_bot/bot.yaml
enable_storage: false  # 禁用存储功能
```

### 自定义序列化

```python
import pickle

async def on_start(self):
    # 使用 pickle 而不是 JSON
    self.storage.set_marshal(
        marshal_fn=lambda obj: pickle.dumps(obj).hex(),
        demarshal_fn=lambda s: pickle.loads(bytes.fromhex(s))
    )
```

### 常驻自动缓存（通过 bots.yaml 配置）

在 `bots.yaml` 为每个 bot 配置存储行为：

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

- auto_cache 会保持内存缓存常驻，按间隔定期 flush。
- flush 失败（SQLite 被 ORM 占用）会按重试间隔回退。
- BotStorage 默认启用 WAL、`synchronous=NORMAL`、`busy_timeout=3000`，减轻锁竞争。

## 使用模式

### 计数器

```python
async with self.storage.cached(["counter"]) as cache:
    count = cache.get("counter", 0)
    cache.put("counter", count + 1)
```

### 用户状态跟踪

```python
async with self.storage.cached(["users"]) as cache:
    users = cache.get("users", {})
    users[message.sender_id] = {
        "name": message.sender_full_name,
        "last_seen": time.time()
    }
    cache.put("users", users)
```

### 配置管理

```python
# 读取
config = await self.storage.get("config", {
    "lang": "en",
    "timezone": "UTC"
})

# 更新
config["lang"] = "zh"
await self.storage.put("config", config)
```

### 临时缓存

```python
# 存储带 TTL 的数据（需要自己管理过期）
cache_data = await self.storage.get("cache", {})
cache_data["key"] = {
    "value": "data",
    "expires": time.time() + 3600
}
await self.storage.put("cache", cache_data)
```

## 性能建议

1. **优先使用缓存上下文**：对于批量操作，使用 `cached()` 可以将多次数据库访问合并为 2 次（初始读取 + 最终写入）

2. **预取关键数据**：在 `cached()` 中指定需要的键，避免缓存未命中

3. **避免存储大对象**：SQLite 适合中小型数据，大文件应存到文件系统

4. **定期清理**：对于历史数据，考虑定期 `delete()` 旧记录

## 示例：完整的投票 Bot

```python
from bot_sdk import BaseBot
from bot_sdk.models import Message

class PollBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        content = message.content.strip()
        
        if content.startswith("/poll "):
            # 创建投票
            question = content[6:].strip()
            async with self.storage.cached(["current_poll"]) as cache:
                cache.put("current_poll", {
                    "question": question,
                    "votes": {"yes": 0, "no": 0}
                })
            await self.send_reply(message, f"📊 Poll: {question}\n/yes or /no to vote!")
        
        elif content == "/yes" or content == "/no":
            # 投票
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
            
            await self.send_reply(message, f"✅ Voted {option}!")
        
        elif content == "/results":
            # 显示结果
            poll = await self.storage.get("current_poll")
            if not poll:
                await self.send_reply(message, "No active poll!")
                return
            
            results = f"""
📊 **{poll['question']}**

👍 Yes: {poll['votes']['yes']}
👎 No: {poll['votes']['no']}
            """.strip()
            await self.send_reply(message, results)
```

## 注意事项

- 存储是按 bot 用户 ID 命名空间隔离的
- `CachedStorage.get()` 和 `put()` 是同步方法（在缓存上下文中）
- `contains()` 在缓存上下文中只检查缓存，不查数据库
- 数据库文件默认存储在 `bot_data/` 目录
- 所有数据自动 JSON 序列化，确保值是 JSON 兼容的
- 如果需要 ORM 表，建议每个 bot 自己维护 Alembic 迁移目录，SDK 级迁移仅保留共享表。

## 相关文档

- [BaseBot API](base_bot.md)
- [命令系统](commands.md)
- [快速开始](quickstart.md)
