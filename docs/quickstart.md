# 快速开始

本指南将帮助你快速创建并运行第一个 Zulip 机器人。

## 前置要求

- Python 3.8 或更高版本
- 一个 Zulip 账户和 API 密钥

## 安装

```bash
pip install async-zulip-bot-sdk
```

## 配置 Zulip 凭据

创建 `~/.zuliprc` 文件：

```ini
[api]
email=your-bot@example.com
key=your-api-key
site=https://your-zulip-server.com
```

## 创建你的第一个 Bot

### 1. 基础 Echo Bot

创建 `my_bot.py`：

```python
from bot_sdk import BaseBot, Message, run_bot

class EchoBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        """回显收到的消息"""
        await self.send_reply(message, f"你说: {message.content}")

if __name__ == "__main__":
    run_bot(EchoBot)
```

运行：

```bash
python my_bot.py
```

### 2. 带命令的 Bot

```python
from bot_sdk import BaseBot, Message, CommandSpec, CommandArgument

class CommandBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        
        # 注册命令
        self.command_parser.register_spec(
            CommandSpec(
                name="greet",
                description="向某人打招呼",
                args=[
                    CommandArgument(
                        name="name",
                        type=str,
                        required=True,
                        description="要打招呼的人名"
                    )
                ],
                handler=self.handle_greet
            )
        )
    
    async def handle_greet(self, invocation, message, bot):
        """处理 greet 命令"""
        name = invocation.args["name"]
        await self.send_reply(message, f"你好，{name}！👋")
    
    async def on_message(self, message: Message) -> None:
        """处理非命令消息"""
        await self.send_reply(message, "使用 /help 查看可用命令")

if __name__ == "__main__":
    run_bot(CommandBot)
```

### 3. 使用多个 Bot

创建 `bots.yaml`：

```yaml
bots:
  - name: echo_bot
    module: my_bot
    class_name: EchoBot
    enabled: true
    
  - name: command_bot
    module: my_bot
    class_name: CommandBot
    enabled: true
```

创建 `main.py`：

```python
import asyncio
from bot_sdk import BotRunner, AsyncClient
from bot_sdk.config import load_config, AppConfig
from my_bot import EchoBot, CommandBot

async def main():
    config = load_config("bots.yaml", AppConfig)
    
    runners = []
    for bot_config in config.bots:
        if not bot_config.enabled:
            continue
            
        # 根据配置选择 Bot 类
        if bot_config.class_name == "EchoBot":
            bot_cls = EchoBot
        elif bot_config.class_name == "CommandBot":
            bot_cls = CommandBot
        else:
            continue
        
        runner = BotRunner(
            lambda c: bot_cls(c),
            client_kwargs={"config_file": bot_config.zuliprc or "~/.zuliprc"}
        )
        runners.append(runner)
        await runner.start()
    
    # 运行所有 bot
    await asyncio.gather(*[r.run_forever() for r in runners])

if __name__ == "__main__":
    asyncio.run(main())
```

## 下一步

- 查看 [BaseBot API](base_bot.md) 了解更多 Bot 功能
- 阅读 [命令系统](commands.md) 学习如何构建复杂命令
- 探索 [AsyncClient API](async_client.md) 了解所有可用的 Zulip API

## 常见问题

### 如何测试 Bot？

在测试服务器或私人频道中测试你的 Bot。

### Bot 没有响应？

1. 检查 `.zuliprc` 配置是否正确
2. 确认 Bot 账户有权限访问相关频道
3. 查看日志输出是否有错误信息

### 如何处理错误？

```python
from bot_sdk import BaseBot, Message
from loguru import logger

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        try:
            # 你的逻辑
            await self.send_reply(message, "处理成功")
        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            await self.send_reply(message, "抱歉，出错了！")
```
