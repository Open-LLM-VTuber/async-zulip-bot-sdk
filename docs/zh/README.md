# Async Zulip Bot SDK API 文档

欢迎使用 Async Zulip Bot SDK 的 API 文档。本文档提供了该 SDK 所有核心组件的详细说明。

## 目录

- [快速开始](quickstart.md)
- [核心组件](core.md)
  - [AsyncClient](async_client.md) - 异步 Zulip API 客户端
  - [BaseBot](base_bot.md) - Bot 基类
  - [BotRunner](bot_runner.md) - Bot 运行器
- [命令系统](commands.md)
  - [CommandParser](commands.md#commandparser) - 命令解析器
  - [CommandSpec](commands.md#commandspec) - 命令规范
  - [CommandArgument](commands.md#commandargument) - 命令参数
- [数据模型](models.md)
  - [请求模型](models.md#请求模型)
  - [响应模型](models.md#响应模型)
  - [数据类型](models.md#数据类型)
- [配置](config.md)
- [日志](logging.md)

## 简介

Async Zulip Bot SDK 是一个基于 Python asyncio 的异步 Zulip 机器人开发框架。它提供了：

- 🚀 完全异步的 API 客户端
- 🤖 简单易用的 Bot 基类
- 📝 强大的命令解析系统
- 🔧 灵活的配置管理
- 📊 类型安全的数据模型

## 安装

```bash
pip install async-zulip-bot-sdk
```

## 快速示例

```python
from bot_sdk import BaseBot, BotRunner, AsyncClient, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        if "hello" in message.content.lower():
            await self.send_reply(message, "Hello! 👋")

if __name__ == "__main__":
    from bot_sdk import run_bot
    run_bot(MyBot)
```

## 版本

当前版本：0.9.1-async

## 许可证

本项目采用 MIT 许可证。
