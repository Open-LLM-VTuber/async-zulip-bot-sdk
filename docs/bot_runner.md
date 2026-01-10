# BotRunner API

`BotRunner` 是管理 Bot 生命周期的工具类，负责启动、运行和停止 Bot。

## 类：BotRunner

```python
from bot_sdk import BotRunner
```

### 初始化

```python
runner = BotRunner(
    bot_factory: Callable[[AsyncClient], BaseBot],
    *,
    event_types: Optional[List[str]] = None,
    narrow: Optional[List[List[str]]] = None,
    client_kwargs: Optional[Dict[str, Any]] = None,
)
```

#### 参数

- **bot_factory**: 工厂函数，接收 `AsyncClient` 返回 `BaseBot` 实例
- **event_types**: 要监听的事件类型列表（默认 `["message"]`，可在 `bots.yaml` 的 `event_types` 中配置）
- **narrow**: 事件过滤条件
- **client_kwargs**: 传递给 `AsyncClient` 的参数

**示例**：

```python
from bot_sdk import BotRunner, BaseBot

# 使用 lambda
runner = BotRunner(
    lambda client: MyBot(client),
    event_types=["message", "presence"],
    client_kwargs={"config_file": "~/.zuliprc"}
)

# 使用函数
def create_bot(client):
    bot = MyBot(client)
    bot.custom_config = load_config()
    return bot

runner = BotRunner(create_bot)
```

## 方法

### start()

```python
await runner.start()
```

启动 Bot。执行以下步骤：

1. 创建 `AsyncClient`
2. 调用 bot_factory 创建 Bot
3. 调用 `bot.post_init()`
4. 建立会话连接
5. 调用 `bot.on_start()`

**示例**：

```python
runner = BotRunner(lambda c: MyBot(c))
await runner.start()
# Bot 现在已启动
```

### stop()

```python
await runner.stop()
```

停止 Bot 并清理资源。执行以下步骤：

1. 调用 `bot.on_stop()`
2. 取消长轮询任务，关闭 `AsyncClient`

**示例**：

```python
await runner.stop()
# Bot 已停止，资源已清理
```

### run_forever()

```python
await runner.run_forever()
```

持续运行 Bot，监听并处理事件。此方法会阻塞直到被中断。

**示例**：

```python
runner = BotRunner(lambda c: MyBot(c))
await runner.start()
await runner.run_forever()  # 持续运行
```

## 上下文管理器

`BotRunner` 支持异步上下文管理器协议：

```python
async with BotRunner(lambda c: MyBot(c)) as runner:
    await runner.run_forever()
# 自动清理
```

## 便捷函数

### run_bot()

```python
from bot_sdk import run_bot

run_bot(
    bot_cls: Type[BaseBot],
    *,
    event_types: Optional[List[str]] = None,
    narrow: Optional[List[List[str]]] = None,
    client_kwargs: Optional[Dict[str, Any]] = None,
) -> None
```

最简单的运行 Bot 的方式。自动处理 asyncio 事件循环。

**参数**：
- **bot_cls**: Bot 类（不是实例）
- **event_types**: 事件类型列表
- **narrow**: 过滤条件
- **client_kwargs**: 客户端参数

**示例**：

```python
from bot_sdk import run_bot, BaseBot

class MyBot(BaseBot):
    async def on_message(self, message):
        await self.send_reply(message, "Hello!")

if __name__ == "__main__":
    run_bot(MyBot)
```

## 使用模式

### 模式 1：简单运行

最简单的方式，适合单个 Bot：

```python
from bot_sdk import run_bot

if __name__ == "__main__":
    run_bot(MyBot)
```

### 模式 2：手动管理

需要更多控制时：

```python
import asyncio
from bot_sdk import BotRunner

async def main():
    runner = BotRunner(lambda c: MyBot(c))
    await runner.start()
    
    try:
        await runner.run_forever()
    except KeyboardInterrupt:
        print("正在停止...")
    finally:
        await runner.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 模式 3：上下文管理器

最佳实践，自动清理资源：

```python
import asyncio
from bot_sdk import BotRunner

async def main():
    async with BotRunner(lambda c: MyBot(c)) as runner:
        await runner.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

### 模式 4：运行多个 Bot

同时运行多个 Bot：

```python
import asyncio
from bot_sdk import BotRunner

async def main():
    # 创建多个 runner
    runners = [
        BotRunner(
            lambda c: Bot1(c),
            client_kwargs={"config_file": "bot1.zuliprc"}
        ),
        BotRunner(
            lambda c: Bot2(c),
            client_kwargs={"config_file": "bot2.zuliprc"}
        ),
    ]
    
    # 启动所有 bot
    for runner in runners:
        await runner.start()
    
    # 并行运行
    try:
        await asyncio.gather(*[r.run_forever() for r in runners])
    finally:
        # 停止所有 bot
        for runner in runners:
            await runner.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

### 模式 5：从配置文件加载

```python
import asyncio
from bot_sdk import BotRunner
from bot_sdk.config import load_config, AppConfig

# bots.yaml
"""
bots:
  - name: echo_bot
    module: my_bots
    class_name: EchoBot
    enabled: true
    zuliprc: ~/.zuliprc
    
  - name: hello_bot
    module: my_bots
    class_name: HelloBot
    enabled: false
"""

async def main():
    config = load_config("bots.yaml", AppConfig)
    runners = []
    
    for bot_config in config.bots:
        if not bot_config.enabled:
            continue
        
        # 动态导入
        module = __import__(bot_config.module)
        bot_cls = getattr(module, bot_config.class_name)
        
        runner = BotRunner(
            lambda c, cls=bot_cls: cls(c),
            client_kwargs={
                "config_file": bot_config.zuliprc or "~/.zuliprc"
            }
        )
        runners.append(runner)
        await runner.start()
    
    await asyncio.gather(*[r.run_forever() for r in runners])

if __name__ == "__main__":
    asyncio.run(main())
```

## 事件过滤

### 按事件类型过滤

```python
# 只监听消息事件
runner = BotRunner(
    lambda c: MyBot(c),
    event_types=["message"]
)

# 监听多种事件
runner = BotRunner(
    lambda c: MyBot(c),
    event_types=["message", "presence", "reaction"]
)
```

### 使用 narrow 过滤

Narrow 是 Zulip 的过滤语法：

```python
# 只监听特定频道
runner = BotRunner(
    lambda c: MyBot(c),
    narrow=[["stream", "general"]]
)

# 只监听私聊
runner = BotRunner(
    lambda c: MyBot(c),
    narrow=[["is", "private"]]
)

# 组合过滤
runner = BotRunner(
    lambda c: MyBot(c),
    narrow=[
        ["stream", "general"],
        ["topic", "bot-testing"]
    ]
)
```

常用的 narrow 操作符：

- `["stream", "stream-name"]`: 特定频道
- `["topic", "topic-name"]`: 特定主题
- `["is", "private"]`: 私聊消息
- `["is", "mentioned"]`: 提及 Bot 的消息
- `["sender", "user@example.com"]`: 特定发送者

## 配置客户端

通过 `client_kwargs` 配置 `AsyncClient`：

```python
runner = BotRunner(
    lambda c: MyBot(c),
    client_kwargs={
        "config_file": "~/.zuliprc",
        "verbose": True,
        "retry_on_errors": True,
    }
)

# 或直接指定凭据
runner = BotRunner(
    lambda c: MyBot(c),
    client_kwargs={
        "email": "bot@example.com",
        "api_key": "your-api-key",
        "site": "https://zulip.example.com",
    }
)
```

## 完整示例

### 生产环境 Bot

```python
import asyncio
import signal
from bot_sdk import BotRunner, BaseBot, Message
from loguru import logger

class ProductionBot(BaseBot):
    async def on_start(self):
        logger.info(f"Bot {self.__class__.__name__} started")
        # 初始化数据库连接等
        
    async def on_stop(self):
        logger.info(f"Bot {self.__class__.__name__} stopping")
        # 清理资源
        
    async def on_message(self, message: Message):
        try:
            await self.send_reply(message, "Hello!")
        except Exception as e:
            logger.error(f"Error handling message: {e}")

async def main():
    runner = BotRunner(
        lambda c: ProductionBot(c),
        event_types=["message"],
        client_kwargs={
            "config_file": "~/.zuliprc",
            "verbose": False,
            "retry_on_errors": True,
        }
    )
    
    # 设置信号处理
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()
    
    def signal_handler():
        logger.info("Received stop signal")
        stop_event.set()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    async with runner:
        logger.info("Bot runner started")
        
        # 同时运行 bot 和等待停止信号
        run_task = asyncio.create_task(runner.run_forever())
        stop_task = asyncio.create_task(stop_event.wait())
        
        done, pending = await asyncio.wait(
            [run_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # 取消未完成的任务
        for task in pending:
            task.cancel()
        
        logger.info("Bot runner stopped")

if __name__ == "__main__":
    asyncio.run(main())
```

### 带健康检查的 Bot

```python
import asyncio
from bot_sdk import BotRunner, BaseBot, Message

class HealthCheckBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.message_count = 0
        self.last_message_time = None
        
    async def on_message(self, message: Message):
        self.message_count += 1
        self.last_message_time = asyncio.get_event_loop().time()
        await self.send_reply(message, f"Processed {self.message_count} messages")

async def health_check(runner):
    """定期检查 Bot 健康状态"""
    while True:
        await asyncio.sleep(60)  # 每分钟检查
        
        if runner.bot:
            bot = runner.bot
            print(f"Health: {bot.message_count} messages processed")
            
            if bot.last_message_time:
                idle = asyncio.get_event_loop().time() - bot.last_message_time
                print(f"Idle for {idle:.0f} seconds")

async def main():
    runner = BotRunner(lambda c: HealthCheckBot(c))
    
    async with runner:
        # 并行运行 bot 和健康检查
        await asyncio.gather(
            runner.run_forever(),
            health_check(runner),
        )

if __name__ == "__main__":
    asyncio.run(main())
```

## 最佳实践

1. **使用上下文管理器**：确保资源正确清理
2. **错误处理**：在 Bot 的事件处理方法中捕获异常
3. **信号处理**：响应 SIGTERM/SIGINT 优雅关闭
4. **日志记录**：记录启动、停止和错误
5. **配置管理**：使用配置文件管理多个 Bot

```python
# 推荐模式
async def main():
    try:
        async with BotRunner(lambda c: MyBot(c)) as runner:
            await runner.run_forever()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
```
