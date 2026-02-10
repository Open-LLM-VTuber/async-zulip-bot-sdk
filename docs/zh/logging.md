# 日志系统 API

Bot SDK 使用 [Loguru](https://github.com/Delgan/loguru) 作为日志库，并将 **系统日志** 与 **Bot 日志** 分离，通过标签和不同的 sink 进行管理。

整体设计：

- SDK 内部、控制台、HTTP 客户端等日志统一标记为 `SYSTEM`，写入 `logs/system.log`。
- 每个 Bot 会拥有自己的带标签的 logger，并可写入独立的日志文件，如 `logs/echo_bot.log`。
- 交互式控制台中的 `Logs` 面板展示所有日志的合并视图，并通过标签区分来源。

## 控制台集成

当运行交互式控制台（`async-zulip-bot` 或 `main.py`）时：

- 所有 Loguru 日志（系统 + 各 Bot）都会显示在 TUI 的 `Logs` 面板中。
- 每一行前面会带有一个标签（如 `SYSTEM`、`echo_bot`），用于区分日志来源。
- 控制台 UI（基于 Rich）会保留 ANSI 颜色，提供良好的阅读体验。
- 可以通过 `PageUp`/`PageDown`（以及在部分终端中通过鼠标滚轮）滚动查看历史日志。

## 快速开始

### 基础用法（系统日志）

```python
from bot_sdk import setup_logging

# 设置系统级日志（推荐在程序入口调用）
setup_logging(level="INFO", json_logs=False)
```

### 在 Bot 中使用（推荐用 self.logger）

```python
from bot_sdk import BaseBot, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message):
        # 使用注入的 bot 专属 logger，带有 Bot 名称标签
        self.logger.info("Received message from {}", message.sender_full_name)
        self.logger.debug("Message content: {}", message.content)
        
        try:
            await self.send_reply(message, "Hello!")
            self.logger.success("Reply sent successfully")
        except Exception as e:
            self.logger.error("Failed to send reply: {}", e)
            self.logger.exception("Full traceback:")
```

## setup_logging()

```python
from bot_sdk import setup_logging

setup_logging(
    level: str = "INFO",
    json_logs: bool = False,
) -> None
```

配置系统日志。

### 参数

- **level** (`str`): 日志级别（默认 `"INFO"`）
- **json_logs** (`bool`): 是否使用 JSON 行格式输出（便于日志收集/分析），默认关闭时使用人类友好的彩色文本格式。


### 日志级别

- `TRACE`: 最详细的日志
- `DEBUG`: 调试信息
- `INFO`: 一般信息（默认）
- `SUCCESS`: 成功消息
- `WARNING`: 警告信息
- `ERROR`: 错误信息
- `CRITICAL`: 严重错误


### 示例

```python
from bot_sdk import setup_logging
from loguru import logger

setup_logging(level="DEBUG")
logger.info("SDK 初始化完成")
```

## 日志方法

### logger.debug()

记录调试信息。

```python
from loguru import logger

logger.debug("This is a debug message")
logger.debug(f"User ID: {user_id}, Status: {status}")
```

### logger.info()

记录一般信息。

```python
logger.info("Bot started successfully")
logger.info(f"Processing message {message.id}")
```

### logger.success()

记录成功消息（绿色显示）。

```python
logger.success("Command executed successfully")
logger.success(f"Sent reply to {user_name}")
```

### logger.warning()

记录警告信息。

```python
logger.warning("Rate limit approaching")
logger.warning(f"Unknown command: {command}")
```

### logger.error()

记录错误信息。

```python
logger.error("Failed to connect to database")
logger.error(f"Invalid configuration: {error}")
```

### logger.exception()

记录异常（包含堆栈跟踪）。

```python
try:
    # 一些操作
    risky_operation()
except Exception as e:
    logger.exception("An error occurred")
```

### logger.critical()

记录严重错误。

```python
logger.critical("Database connection lost")
logger.critical("Critical system failure")
```

## 完整示例

### 基础 Bot 日志

```python
from bot_sdk import BaseBot, Message, run_bot, setup_logging
from loguru import logger

# 配置日志
setup_logging(level="INFO")

class LoggingBot(BaseBot):
    async def post_init(self):
        await super().post_init()
        logger.info(f"Bot {self.__class__.__name__} initialized")
        logger.debug(f"Bot user ID: {self._user_id}")
    
    async def on_start(self):
        logger.info("Bot starting...")
        # 初始化资源
        logger.success("Bot started successfully")
    
    async def on_stop(self):
        logger.info("Bot stopping...")
        # 清理资源
        logger.success("Bot stopped successfully")
    
    async def on_message(self, message: Message):
        logger.info(f"Message from {message.sender_full_name}: {message.content[:50]}")
        
        try:
            await self.send_reply(message, "Got it!")
            logger.success(f"Replied to message {message.id}")
        except Exception as e:
            logger.error(f"Failed to reply: {e}")

if __name__ == "__main__":
    run_bot(LoggingBot)
```

### 详细日志 Bot

```python
from bot_sdk import BaseBot, Message, run_bot, setup_logging
from loguru import logger
import time

# 配置详细日志
setup_logging(level="DEBUG")

class DetailedBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.message_count = 0
        logger.debug("Bot instance created")
    
    async def on_message(self, message: Message):
        start_time = time.time()
        self.message_count += 1
        
        logger.debug(f"Processing message {message.id}")
        logger.debug(f"Sender: {message.sender_email}")
        logger.debug(f"Type: {message.type}")
        
        if message.type == "stream":
            logger.debug(f"Stream: {message.stream_id}, Topic: {message.topic}")
        
        try:
            # 处理消息
            await self.send_reply(message, f"Message #{self.message_count}")
            
            elapsed = time.time() - start_time
            logger.info(f"Processed message {message.id} in {elapsed:.3f}s")
            logger.success(f"Total messages: {self.message_count}")
            
        except Exception as e:
            logger.error(f"Error processing message {message.id}: {e}")
            logger.exception("Full traceback:")

if __name__ == "__main__":
    run_bot(DetailedBot)
```

### Bot 专属日志文件

多数情况下 SDK 会自动为每个 Bot 创建对应的文件 sink，无需手动配置：

- `SYSTEM` 日志写入：`logs/system.log`
- Bot 日志写入：`logs/<bot_name>.log`（例如 `logs/echo_bot.log`）

如果你需要在独立脚本中手动获取 bot logger，可以使用：

```python
from bot_sdk import get_bot_logger

logger = get_bot_logger("echo_bot", level="INFO")
logger.info("EchoBot starting...")
```

### 结构化日志

```python
from bot_sdk import BaseBot, Message, run_bot, setup_logging
from loguru import logger

setup_logging(level="INFO")

class StructuredBot(BaseBot):
    async def on_message(self, message: Message):
        # 结构化日志记录
        logger.bind(
            message_id=message.id,
            sender=message.sender_email,
            type=message.type
        ).info("Processing message")
        
        try:
            await self.send_reply(message, "OK")
            
            logger.bind(
                message_id=message.id,
                action="reply",
                status="success"
            ).success("Reply sent")
            
        except Exception as e:
            logger.bind(
                message_id=message.id,
                action="reply",
                status="error",
                error=str(e)
            ).error("Reply failed")

if __name__ == "__main__":
    run_bot(StructuredBot)
```

## 高级配置

### 多个日志输出

```python
from loguru import logger

# 移除默认处理器
logger.remove()

# 控制台输出（INFO 及以上）
logger.add(
    lambda msg: print(msg, end=""),
    level="INFO",
    colorize=True,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>"
)

# 文件输出（DEBUG 及以上）
logger.add(
    "debug.log",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
    rotation="10 MB"
)

# 错误日志单独文件
logger.add(
    "errors.log",
    level="ERROR",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    rotation="1 day",
    retention="30 days"
)
```

### 按环境配置

```python
import os
from loguru import logger

env = os.getenv("BOT_ENV", "dev")

if env == "prod":
    # 生产环境：只记录到文件，INFO 级别
    logger.remove()
    logger.add(
        "bot.log",
        level="INFO",
        rotation="1 day",
        retention="30 days"
    )
else:
    # 开发环境：控制台输出，DEBUG 级别
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        level="DEBUG",
        colorize=True
    )
```

### 自定义日志格式

```python
from loguru import logger

# 简洁格式
logger.add(
    lambda msg: print(msg, end=""),
    format="[{time:HH:mm:ss}] {level: <8} {message}",
    colorize=True
)

# 详细格式
logger.add(
    "detailed.log",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# JSON 格式
import json
logger.add(
    "bot.json",
    format=lambda record: json.dumps({
        "timestamp": record["time"].isoformat(),
        "level": record["level"].name,
        "message": record["message"],
        "extra": record.get("extra", {})
    }) + "\n",
    level="INFO"
)
```

### 过滤日志

```python
from loguru import logger

def filter_sensitive(record):
    """过滤敏感信息"""
    message = record["message"]
    # 过滤密码、token 等
    if "password" in message.lower() or "token" in message.lower():
        return False
    return True

logger.add(
    "bot.log",
    filter=filter_sensitive,
    level="INFO"
)
```

## 最佳实践

### 1. 合理的日志级别

```python
from bot_sdk import BaseBot, Message
from loguru import logger

class BestPracticeBot(BaseBot):
    async def on_message(self, message: Message):
        # DEBUG: 调试信息
        logger.debug(f"Raw message data: {message}")
        
        # INFO: 正常操作
        logger.info(f"Processing message from {message.sender_full_name}")
        
        # SUCCESS: 操作成功
        if await self.process_message(message):
            logger.success("Message processed successfully")
        
        # WARNING: 值得注意但不是错误
        if len(message.content) > 1000:
            logger.warning("Message exceeds recommended length")
        
        # ERROR: 错误但程序可继续
        try:
            await self.send_reply(message, "OK")
        except Exception as e:
            logger.error(f"Failed to send reply: {e}")
        
        # CRITICAL: 严重错误，可能需要人工介入
        if not self.client.session:
            logger.critical("Lost connection to Zulip server")
```

### 2. 上下文信息

```python
from loguru import logger

# 添加上下文
with logger.contextualize(user_id=123, session_id="abc"):
    logger.info("User logged in")
    # 日志会包含 user_id 和 session_id

# 使用 bind
user_logger = logger.bind(user="alice@example.com")
user_logger.info("Started processing")
user_logger.info("Finished processing")
```

### 3. 异常处理

```python
from loguru import logger

try:
    risky_operation()
except ValueError as e:
    # 记录错误但不包含堆栈
    logger.error(f"Invalid value: {e}")
except Exception as e:
    # 记录完整的异常信息
    logger.exception("Unexpected error occurred")
```

### 4. 性能考虑

```python
from loguru import logger

# 避免在循环中大量日志
for i in range(10000):
    # 不好：太多日志
    # logger.debug(f"Processing item {i}")
    
    # 好：只记录关键点
    if i % 1000 == 0:
        logger.debug(f"Processed {i} items")

# 使用级别检查避免不必要的字符串格式化
if logger.level("DEBUG").no >= logger._core.min_level:
    expensive_debug_info = generate_debug_info()
    logger.debug(f"Debug info: {expensive_debug_info}")
```

### 5. 生产环境配置

```python
import os
from loguru import logger
from bot_sdk import setup_logging

# 根据环境配置
if os.getenv("BOT_ENV") == "prod":
    logger.remove()
    
    # 主日志文件
    logger.add(
        "/var/log/bot/bot.log",
        level="INFO",
        rotation="1 day",
        retention="30 days",
        compression="gz",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}"
    )
    
    # 错误日志
    logger.add(
        "/var/log/bot/errors.log",
        level="ERROR",
        rotation="1 day",
        retention="90 days"
    )
else:
    # 开发环境使用默认设置
    setup_logging(level="DEBUG")
```

## 常见问题

### 如何禁用日志？

```python
from loguru import logger

logger.remove()  # 移除所有处理器
logger.disable("bot_sdk")  # 禁用特定模块
```

### 如何重定向到标准输出？

```python
import sys
from loguru import logger

logger.remove()
logger.add(sys.stdout, level="INFO")
```

### 如何在日志中包含更多信息？

```python
logger.add(
    "bot.log",
    format="{time} | {level} | {file}:{line} | {function} | {message}",
    level="DEBUG"
)
```
