<div align="center">

# 🤖 Async Zulip Bot SDK

**异步、类型安全的 Zulip 机器人开发框架**

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![GitHub release](https://img.shields.io/github/v/release/Open-LLM-VTuber/async-zulip-bot-sdk)](https://github.com/Open-LLM-VTuber/async-zulip-bot-sdk/releases)

[English](README.md) | [中文](README.zh-CN.md)

---

</div>

### ✨ 特性

- 🚀 **异步优先** — 基于 `httpx.AsyncClient` 的高性能异步操作，完全兼容官方 `zulip.Client` 接口
- 📝 **类型安全** — 使用 Pydantic v2 模型提供完整的类型提示和自动验证
- 🎯 **命令系统** — 强大的内置命令解析器，支持类型检查、参数验证和自动帮助生成
- 💾 **灵活存储** — 可选择轻量级 JSON 存储或完整的 SQLAlchemy ORM（支持 Alembic 迁移）
- 🌐 **国际化支持** — 内置 i18n 支持，基于 JSON 的翻译文件
- 🔧 **YAML 配置** — 在 `bot.yaml` 中统一管理所有机器人配置
- 🖥️ **交互式控制台** — 基于 Rich 的精美 TUI 界面，支持多机器人管理、实时日志和命令历史
- 📦 **生产就绪** — 内置长轮询事件循环、自动重连和错误恢复机制

### 📦 安装

自 **v0.2.0** 起，本项目通过 GitHub Actions 在发布 **GitHub Release** 时
自动构建并发布到 **PyPI**，因此从该版本开始可以直接通过 `(uv)pip` 安装。

#### 方式一：从 PyPI 安装（普通用户推荐）

```bash
# 使用 uv（推荐）
uv pip install async-zulip-bot-sdk

# 或直接使用 pip
pip install async-zulip-bot-sdk
```

#### 方式二：从源码安装（开发者推荐）

```bash
git clone https://github.com/Open-LLM-VTuber/async-zulip-bot-sdk.git
cd async-zulip-bot-sdk

# 使用 uv（推荐）
uv venv
uv pip install -e .

# 或使用 venv + pip
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
pip install -e .
```

### 🚀 快速开始

> ⚠️ 重大变更（下一主版本）：Bot 配置仅从各自的 `bot.yaml` 读取，类属性（如 `command_prefixes`、`enable_storage`、`enable_orm`）不再生效。请在该 Bot 的 YAML 中设置前缀/提及/help/存储/ORM 等选项。

#### 交互式控制台（推荐）

本 SDK 内置了一个功能强大的交互式控制台，用于管理 Bot，基于 `rich` 提供了美观的 TUI（文本用户界面）。

1. **运行控制台**：
   ```bash
   python main.py
   ```

   **主要功能：**
   - **Rich TUI**：美观的分屏布局，同时显示日志、状态和输入框。
   - **命令历史**：使用 `上`/`下` 箭头键浏览历史命令。
   - **日志滚动**：使用 `PageUp`/`PageDown` 键滚动查看历史日志。
   - **Bot 管理**：动态启动、停止和重载 Bot。
    - **Tab 补全**：按 `Tab` 键自动补全命令和 Bot 名称。

#### 创建单文件 Bot

如果您只需要一个简单的脚本，不需要管理器：

#### 1. 配置 Zulip 凭据

下载 `zuliprc` 文件：

你可以在 `Settings - Personal - Account & privacy` 中创建和重新创建你的 API Key，输入你的密码，并选择 `Download zuliprc`。请将每个机器人的凭据放在各自的目录下，例如 `bots/echo_bot/zuliprc`。

#### 2. 配置 bots.yaml

在根目录创建一个 `bots.yaml` 文件，你可以参考 `bots.yaml.example` 了解详情。
声明要启动的机器人及其位置：

```yaml
bots:
  - name: echo_bot
    module: bots.echo_bot
    class_name: BOT_CLASS
    enabled: true
    # 可选：自定义 zuliprc 路径（默认 bots/<name>/zuliprc）
    # zuliprc: bots/echo_bot/zuliprc
    config: {}  # 可选，作为第二个参数传给工厂
```
#### 3. 配置每个 Bot 的 bot.yaml

在 `bots/echo_bot/bot.yaml` 里设置前缀/提及/help/存储/ORM 等：

```yaml
command_prefixes:
- "!"
enable_mention_commands: true
auto_help_command: true
enable_storage: true
# storage_path: bot_data/echo_bot.db
enable_orm: false
# orm_db_path: bot_data/echo_bot.sqlite
language: en
```

#### 4. 创建你的第一个机器人

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
    def __init__(self, client):
        super().__init__(client)
        # 注册命令（前缀来源于 bot.yaml）
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

#### 5. 运行机器人

```bash
python main.py
```

进入交互式控制台后，使用 run 命令启动你的机器人：

```
bot-console> run echo_bot
```

你可以使用 help 命令查看更多控制台命令。

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

> ⚠️ 注意：从下一主版本开始，配置应在 `bot.yaml` 中设置，而非类属性。

在 `bot.yaml` 中配置：
```yaml
command_prefixes: ["!", "/", "."]
enable_mention_commands: true  # 启用 @bot 触发命令
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

---

## 📚 文档

完整的 API 文档可在线访问：

- **在线文档**（托管版）：https://docs.llmvtuber.com/async-zulip-bot-sdk/
- **源码文档**（本仓库）：见 `docs/` 目录（使用 `mkdocs serve` 构建）

文档包括：
- 📖 快速开始指南
- 🔧 API 参考（AsyncClient、BaseBot、BotRunner）
- 💬 命令系统
- 📊 数据模型
- ⚙️ 配置管理
- 📝 日志记录

---

### 🤝 贡献

欢迎贡献！请随时提交 Pull Request。

**贡献文档**：我们欢迎中英文文档的贡献。

### 🙏 致谢与声明

- [bot_sdk/async_zulip.py](bot_sdk/async_zulip.py) 的部分实现改编自 Zulip 上游客户端：https://github.com/zulip/python-zulip-api/blob/main/zulip/zulip/__init__.py。
- 上游项目采用 Apache-2.0 许可证；原始许可声明已保留在源码中，完整许可证文本见 [Apache2.0.LICENSE](Apache2.0.LICENSE)。
- 特别感谢 Zulip 团队的卓越工作和开源贡献。

### 📄 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

<div align="center">

Made with ❤️ for the Open-LLM-VTuber Zulip team

</div>
