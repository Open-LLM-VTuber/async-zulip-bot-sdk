# 核心组件

Bot SDK 的核心组件提供了构建 Zulip 机器人所需的所有基础功能。

## 概述

Bot SDK 包含以下核心组件：

1. **[AsyncClient](async_client.md)** - 异步 Zulip API 客户端
2. **[BaseBot](base_bot.md)** - Bot 基类，提供事件处理框架
3. **[BotRunner](bot_runner.md)** - Bot 生命周期管理器

## 架构

```
┌─────────────────────────────────────────────┐
│              Your Bot                        │
│         (继承 BaseBot)                       │
│                                              │
│  - on_message()                              │
│  - 命令处理器                                │
│  - 自定义逻辑                                │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│            BaseBot                           │
│                                              │
│  - 事件分发                                  │
│  - 命令解析                                  │
│  - 消息回复                                  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│          AsyncClient                         │
│                                              │
│  - HTTP 请求                                 │
│  - 事件轮询                                  │
│  - API 封装                                  │
└──────────────┬──────────────────────────────┘
               │
┌──────────────▼──────────────────────────────┐
│         Zulip Server                         │
└──────────────────────────────────────────────┘
```

## 组件关系

### AsyncClient

底层 HTTP 客户端，负责：

- 与 Zulip 服务器通信
- 处理认证
- 管理长轮询连接
- 提供所有 Zulip API 的封装

**使用场景**：

- 需要直接调用 Zulip API
- 构建非标准的 Bot 行为
- 测试和调试

**示例**：
```python
from bot_sdk import AsyncClient

async with AsyncClient() as client:
    profile = await client.get_profile()
    print(profile.full_name)
```

### BaseBot

中层抽象，负责：

- 接收和分发事件
- 解析命令
- 提供便捷的回复方法
- 管理 Bot 状态

**使用场景**：

- 构建标准的消息处理 Bot
- 需要命令系统
- 需要事件驱动架构

**示例**：
```python
from bot_sdk import BaseBot, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message):
        await self.send_reply(message, "Hello!")
```

### BotRunner

顶层管理器，负责：

- 启动和停止 Bot
- 管理生命周期
- 处理事件循环
- 支持多 Bot 运行

**使用场景**：

- 生产环境部署
- 需要优雅关闭
- 运行多个 Bot
- 复杂的启动逻辑

**示例**：
```python
from bot_sdk import BotRunner

async with BotRunner(lambda c: MyBot(c)) as runner:
    await runner.run_forever()
```

## 快速开始

### 最简单的 Bot

```python
from bot_sdk import BaseBot, Message, run_bot

class SimpleBot(BaseBot):
    async def on_message(self, message: Message):
        await self.send_reply(message, "Echo: " + message.content)

if __name__ == "__main__":
    run_bot(SimpleBot)
```

### 带命令的 Bot

```python
from bot_sdk import BaseBot, Message, CommandSpec, CommandArgument

class CommandBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.command_parser.register_spec(
            CommandSpec(
                name="hello",
                description="Say hello",
                handler=self.handle_hello
            )
        )
    
    async def handle_hello(self, invocation, message, bot):
        await self.send_reply(message, "Hello, World!")
    
    async def on_message(self, message: Message):
        await self.send_reply(message, "Use /help for commands")
```

### 完整的生产 Bot

```python
import asyncio
from bot_sdk import BaseBot, Message, BotRunner, setup_logging
from loguru import logger

# 配置日志
setup_logging(level="INFO")

class ProductionBot(BaseBot):
    async def post_init(self):
        await super().post_init()
        # 初始化数据库等
        logger.info("Bot initialized")
    
    async def on_start(self):
        logger.info("Bot starting")
        # 加载数据
    
    async def on_stop(self):
        logger.info("Bot stopping")
        # 清理资源
    
    async def on_message(self, message: Message):
        logger.info(f"Message from {message.sender_full_name}")
        await self.send_reply(message, "Processed!")

async def main():
    async with BotRunner(lambda c: ProductionBot(c)) as runner:
        await runner.run_forever()

if __name__ == "__main__":
    asyncio.run(main())
```

## 选择合适的组件

### 何时直接使用 AsyncClient

- ✅ 需要完全控制 API 调用
- ✅ 构建非标准的应用（不是 Bot）
- ✅ 测试 Zulip API
- ✅ 批量操作（如数据迁移）

### 何时使用 BaseBot

- ✅ 构建标准的消息响应 Bot
- ✅ 需要命令系统
- ✅ 处理用户交互
- ✅ 大多数 Bot 场景

### 何时使用 BotRunner

- ✅ 生产环境部署
- ✅ 需要优雅启动/关闭
- ✅ 运行多个 Bot
- ✅ 需要健康检查和监控

## 深入学习

- [AsyncClient 详细文档](async_client.md)
- [BaseBot 详细文档](base_bot.md)
- [BotRunner 详细文档](bot_runner.md)
- [命令系统](commands.md)
- [数据模型](models.md)
