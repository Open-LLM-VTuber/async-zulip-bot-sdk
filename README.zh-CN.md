<div align="center">

# 🤖 Zulip Bot SDK

**异步、类型安全的 Zulip 机器人开发框架**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

[English](README.md) | [中文](README.zh-CN.md)

---

</div>

### ✨ 特性

- 🚀 **异步优先** — 基于 `httpx.AsyncClient` 的 Zulip REST API 异步绑定，完全兼容官方 `zulip.Client` 接口
- 📝 **类型安全** — 使用 Pydantic v2 模型提供完整的类型提示和自动验证
- 🎯 **命令系统** — 内置强大的命令解析器，支持类型检查、参数验证和自动帮助生成
- 🔧 **简单易用** — 极简的 Bot 基类和生命周期钩子，快速开发生产级机器人
- 📦 **开箱即用** — 长轮询事件循环、错误重试、自动重连全部内置

### 📦 安装

1. 克隆本仓库

```bash
git clone https://github.com/Open-LLM-VTuber/zulip-bots
cd zulip-bots
```

2. 在本地环境中安装，在这之前推荐先新建一个虚拟环境

```bash
# 使用 uv（推荐）
uv pip install -e .

# 或使用 pip
pip install -e .
```

### 🚀 快速开始

#### 1. 配置 Zulip 凭据

下载 `zuliprc` 文件：

你可以在 `Settings - Personal - Account & privacy` 中创建和重新创建你的 API Key，输入你的密码，并选择 `Download zuliprc`。请将每个机器人的凭据放在各自的目录下，例如 `bots/echo_bot/zuliprc`。

#### 2. 配置 bots.yaml

在根目录声明要启动的机器人及其位置：

```yaml
bots:
    - name: echo_bot
        module: bots.echo_bot        # 位于 bots/echo_bot/__init__.py
        class_name: BOT_CLASS        # 可选，默认使用 BOT_CLASS 或首个 BaseBot 子类
        enabled: true
        # 可选：自定义 zuliprc 路径（默认 bots/<name>/zuliprc）
        # zuliprc: bots/echo_bot/zuliprc
        config: {}                   # 可选，作为第二个参数传给工厂
```

#### 3. 创建你的第一个机器人

```python
import asyncio

from bot_sdk import (
    BaseBot,
    BotRunner,
    Message,
    CommandSpec,
    CommandArgument,
    setup_logging
)

class MyBot(BaseBot):
    command_prefixes = ("!", "/")  # 命令前缀
    
    def __init__(self, client):
        super().__init__(client)
        # 注册命令
        self.command_parser.register_spec(
            CommandSpec(
                name="echo",
                description="回显提供的文本",
                args=[CommandArgument("text", str, required=True, multiple=True)],
                handler=self.handle_echo,
            )
        )
    
    async def on_start(self):
        """启动时调用"""
        print(f"Bot started! User ID: {self._user_id}")
    
    async def handle_echo(self, invocation, message, bot):
        """处理 echo 命令"""
        text = " ".join(invocation.args.get("text", []))
        await self.send_reply(message, f"Echo: {text}")
    
    async def on_message(self, message: Message):
        """处理非命令消息"""
        await self.send_reply(message, "尝试使用 !help 查看可用命令！")

BOT_CLASS = MyBot
```

将这段代码保存到你在 `bots.yaml` 中配置的目录的 `__init__.py` 文件里，例如示例中存放为 `bots/echo_bot/__init__.py`。

#### 4. 运行机器人

```bash
python main.py
```

### 📚 核心概念

#### 异步客户端 (AsyncClient)

完全异步的 Zulip API 客户端，镜像官方 `zulip.Client` 的公共接口：

```python
from bot_sdk import AsyncClient

async with AsyncClient(config_file="zuliprc") as client:
    # 获取用户信息
    profile = await client.get_profile()
    
    # 发送消息
    await client.send_message({
        "type": "stream",
        "to": "general",
        "topic": "Hello",
        "content": "Hello, world!"
    })
    
    # 获取订阅
    subs = await client.get_subscriptions()
```

#### 命令系统

类型安全的命令定义和自动验证：

```python
from bot_sdk import CommandSpec, CommandArgument

# 定义带参数的命令
self.command_parser.register_spec(
    CommandSpec(
        name="greet",
        description="问候用户",
        args=[
            CommandArgument("name", str, required=True),
            CommandArgument("times", int, required=False),
        ],
        handler=self.handle_greet,
    )
)

async def handle_greet(self, invocation, message, bot):
    name = invocation.args["name"]
    times = invocation.args.get("times", 1)
    greeting = f"Hello, {name}! " * times
    await self.send_reply(message, greeting)
```

**自动生成帮助信息：**

使用 `!help` 或 `!?` 自动显示所有注册的命令和参数。

#### 生命周期钩子

```python
class MyBot(BaseBot):
    async def on_start(self):
        """Bot 启动时调用"""
        pass
    
    async def on_stop(self):
        """Bot 停止时调用"""
        pass
    
    async def on_message(self, message: Message):
        """收到非命令消息时调用"""
        pass
```

### 🔧 高级用法

#### 自定义命令前缀和提及检测

```python
class MyBot(BaseBot):
    command_prefixes = ("!", "/", ".")
    enable_mention_commands = True  # 启用 @bot 触发命令
```

#### 类型化的消息模型

```python
from bot_sdk import Message, StreamMessageRequest

async def on_message(self, message: Message):
    # 完整类型提示
    sender = message.sender_full_name
    content = message.content
    
    # 发送类型化消息
    await self.client.send_message(
        StreamMessageRequest(
            to=message.stream_id,
            topic="Reply",
            content="Typed reply!"
        )
    )
```

#### 错误处理

```python
from bot_sdk import CommandError, UnknownCommandError, InvalidArgumentsError

# 命令解析和调度会自动处理错误
# 并向用户发送友好的错误消息
```

### 📖 API 参考

#### BaseBot

- `command_prefixes: tuple[str, ...]` — 命令前缀（默认：`("!",)`）
- `enable_mention_commands: bool` — 是否启用 @提及 触发（默认：`True`）
- `auto_help_command: bool` — 是否自动注册 help 命令（默认：`True`）
- `async on_start()` — 启动钩子
- `async on_stop()` — 停止钩子
- `async on_message(message)` — 消息处理钩子
- `async send_reply(message, content)` — 回复消息工具方法

#### CommandSpec

- `name: str` — 命令名称
- `description: str` — 命令描述
- `args: List[CommandArgument]` — 参数定义
- `aliases: List[str]` — 命令别名
- `handler: Callable` — 处理函数
- `show_in_help: bool` — 是否在帮助中显示（默认：`True`）

#### CommandArgument

- `name: str` — 参数名称
- `type: type` — 参数类型（`str`, `int`, `float`, `bool`）
- `required: bool` — 是否必需（默认：`True`）
- `description: str` — 参数描述
- `multiple: bool` — 是否捕获剩余所有参数（默认：`False`）

### 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

### 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<div align="center">

Made with ❤️ for the Open-LLM-VTuber Zulip team

</div>
