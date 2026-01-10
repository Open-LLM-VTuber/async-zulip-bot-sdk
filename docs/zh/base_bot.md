# BaseBot API

`BaseBot` 是所有 Zulip 机器人的基类，提供了消息处理、命令解析和回复功能。

## 类：BaseBot

```python
from bot_sdk import BaseBot
```

### 继承并实现

```python
from bot_sdk import BaseBot, Message

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        # 处理消息
        await self.send_reply(message, "收到消息！")
```

## 类属性

### command_prefixes

```python
command_prefixes = ("/", "!")
```

命令前缀字符元组。默认为 `/` 和 `!`。

**示例**：

```python
class MyBot(BaseBot):
    command_prefixes = ("/", "!", "@")  # 支持三种前缀
```

### enable_mention_commands

```python
enable_mention_commands = True
```

是否将 @-提及视为命令触发器。默认为 `True`。

**示例**：

```python
# 这些都会触发命令（如果 enable_mention_commands=True）：
# "@Bot help"
# "@**Bot Name** status"
```

### auto_help_command

```python
auto_help_command = True
```

是否自动注册内置的 help 命令。默认为 `True`。

### 内置命令

- `whoami`：显示调用者的角色与权限等级。
- `perm`：权限管理（设置 bot_owner、调整角色等级、允许/禁止 stop）。
- `stop`：在具备权限时请求安全停止 BotRunner。

> 权限校验：如果 `CommandSpec` 设置了 `min_level`，BaseBot 会在分发前检查；`perm`/`stop` 已内置限制。

## 实例属性

### client

```python
self.client: AsyncClient
```

关联的 `AsyncClient` 实例，用于调用 Zulip API。

### command_parser

```python
self.command_parser: CommandParser
```

命令解析器实例，用于注册和解析命令。

## 方法

### 构造函数

```python
def __init__(self, client: AsyncClient) -> None
```

初始化 Bot。通常由 `BotRunner` 自动调用。

**参数**：

- **client**: AsyncClient 实例

### 生命周期钩子

#### post_init()

```python
async def post_init(self) -> None
```

初始化后的钩子，用于设置 Bot。在 Bot 启动时自动调用。

**默认行为**：
1. 获取 Bot 的用户信息
2. 设置命令解析器的身份别名

3. 更新在线状态为 "active"

**重写示例**：

```python

class MyBot(BaseBot):
    async def post_init(self) -> None:
        await super().post_init()  # 调用父类方法
        # 你的初始化逻辑
        self.data = await self.load_data()
```

#### on_start()

```python
async def on_start(self) -> None
```

Bot 启动时的钩子。在 `post_init()` 之后调用。

**示例**：

```python
class MyBot(BaseBot):
    async def on_start(self) -> None:
        print("Bot 启动了！")
        # 加载配置、数据库连接等
```

#### on_stop()

```python
async def on_stop(self) -> None
```

Bot 停止时的钩子。用于清理资源。

**示例**：

```python
class MyBot(BaseBot):
    async def on_stop(self) -> None:
        print("Bot 停止了！")
        # 关闭数据库连接、保存状态等
```

### 事件处理

#### on_event()

```python
async def on_event(self, event: Event) -> None
```

处理所有事件。**通常不需要重写**此方法。

**默认行为**：
1. 过滤 message 类型事件
2. 忽略来自自己的消息
3. 尝试解析命令
4. 如果是命令，先校验 `min_level`（如设置），再调用命令处理器
5. 否则调用 `on_message()`

**重写示例**（处理其他事件类型）：

```python
class MyBot(BaseBot):
    async def on_event(self, event: Event) -> None:
        if event.type == "presence":
            # 处理在线状态变化
            print(f"在线状态更新: {event}")
        else:
            await super().on_event(event)  # 调用默认处理
```

#### on_message() ⭐

```python
@abc.abstractmethod
async def on_message(self, message: Message) -> None
```

**必须实现**的方法，处理非命令消息。

**参数**：

- **message**: `Message` 对象

**示例**：

```python
class EchoBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        # 回显消息
        await self.send_reply(message, f"你说: {message.content}")

class SmartBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        content = message.content.lower()
        
        if "hello" in content:
            await self.send_reply(message, "Hello! 👋")
        elif "help" in content:
            await self.send_reply(message, "使用 /help 查看命令")
        else:
            await self.send_reply(message, "我不明白，请使用 /help")
```

#### on_command()

```python
async def on_command(self, command: CommandInvocation, message: Message) -> None
```

遗留的命令处理钩子。**推荐使用 CommandSpec 的 handler**。

### 命令相关

#### parse_command()

```python
def parse_command(self, message: Message) -> CommandInvocation | None
```

解析消息为命令调用。

**返回**：
- `CommandInvocation`: 如果消息是命令
- `None`: 如果不是命令

**示例**：

```python
class MyBot(BaseBot):
    async def on_event(self, event: Event) -> None:
        if event.type == "message":
            cmd = self.parse_command(event.message)
            if cmd:
                print(f"命令: {cmd.name}, 参数: {cmd.args}")
```

### 消息发送

#### send_reply()

```python
async def send_reply(self, original: Message, content: str) -> None
```

回复消息（自动处理频道消息和私聊）。

**参数**：

- **original**: 原始消息对象
- **content**: 回复内容（支持 Markdown）

**行为**：
- 对于频道消息：回复到同一频道和主题
- 对于私聊消息：回复给发送者

**示例**：

```python
class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        # 简单回复
        await self.send_reply(message, "收到消息！")
        
        # Markdown 格式
        await self.send_reply(
            message,
            "**粗体** *斜体* `代码`\n"
            "[链接](https://example.com)"
        )
        
        # 代码块
        await self.send_reply(
            message,
            "```python\n"
            "print('Hello, World!')\n"
            "```"
        )
```

## 完整示例

### 基础 Bot

```python
from bot_sdk import BaseBot, Message, run_bot

class SimpleBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        await self.send_reply(message, f"收到: {message.content}")

if __name__ == "__main__":
    run_bot(SimpleBot)
```

### 带状态的 Bot

```python
from bot_sdk import BaseBot, Message, run_bot
from collections import defaultdict

class CounterBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.message_counts = defaultdict(int)
    
    async def on_message(self, message: Message) -> None:
        self.message_counts[message.sender_id] += 1
        count = self.message_counts[message.sender_id]
        
        await self.send_reply(
            message,
            f"这是你发送的第 {count} 条消息！"
        )

if __name__ == "__main__":
    run_bot(CounterBot)
```

### 带命令的 Bot

```python
from bot_sdk import (
    BaseBot, Message, CommandSpec, CommandArgument,
    CommandInvocation, run_bot
)

class TodoBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        self.todos = []
        
        # 注册命令
        self.command_parser.register_spec(
            CommandSpec(
                name="add",
                description="添加待办事项",
                args=[
                    CommandArgument(
                        name="task",
                        type=str,
                        required=True,
                        multiple=True,  # 捕获所有剩余词语
                        description="任务描述"
                    )
                ],
                handler=self.handle_add
            )
        )
        
        self.command_parser.register_spec(
            CommandSpec(
                name="list",
                description="显示所有待办事项",
                handler=self.handle_list
            )
        )
        
        self.command_parser.register_spec(
            CommandSpec(
                name="done",
                description="标记任务完成",
                args=[
                    CommandArgument(
                        name="index",
                        type=int,
                        required=True,
                        description="任务编号"
                    )
                ],
                handler=self.handle_done
            )
        )
    
    async def handle_add(self, invocation: CommandInvocation, message, bot):
        task = " ".join(invocation.args["task"])
        self.todos.append(task)
        await self.send_reply(message, f"✅ 已添加: {task}")
    
    async def handle_list(self, invocation: CommandInvocation, message, bot):
        if not self.todos:
            await self.send_reply(message, "没有待办事项")
            return
        
        lines = [f"{i+1}. {task}" for i, task in enumerate(self.todos)]
        await self.send_reply(message, "\n".join(lines))
    
    async def handle_done(self, invocation: CommandInvocation, message, bot):
        idx = invocation.args["index"] - 1
        if 0 <= idx < len(self.todos):
            task = self.todos.pop(idx)
            await self.send_reply(message, f"✅ 完成: {task}")
        else:
            await self.send_reply(message, "❌ 无效的任务编号")
    
    async def on_message(self, message: Message) -> None:
        await self.send_reply(message, "使用 /help 查看可用命令")

if __name__ == "__main__":
    run_bot(TodoBot)
```

### 高级 Bot（处理多种事件）

```python
from bot_sdk import BaseBot, Message, Event, run_bot

class AdvancedBot(BaseBot):
    async def post_init(self) -> None:
        await super().post_init()
        self.user_cache = {}
    
    async def on_event(self, event: Event) -> None:
        # 处理其他类型事件
        if event.type == "realm_user":
            if event.op == "add":
                print(f"新用户加入: {event}")
            elif event.op == "remove":
                print(f"用户离开: {event}")
        
        # 默认消息处理
        await super().on_event(event)
    
    async def on_message(self, message: Message) -> None:
        # 获取发送者信息
        sender = message.sender_full_name
        
        if "info" in message.content.lower():
            info = f"""
**消息信息**
- 发送者: {sender}
- 类型: {message.type}
- ID: {message.id}
            """
            await self.send_reply(message, info)
        else:
            await self.send_reply(message, f"你好，{sender}!")

if __name__ == "__main__":
    run_bot(AdvancedBot)
```

## 最佳实践

1. **总是调用 super()**：重写钩子方法时调用父类方法
2. **异常处理**：在 `on_message` 中捕获异常
3. **状态管理**：使用实例变量保存 Bot 状态
4. **命令优先**：复杂功能使用命令系统
5. **日志记录**：使用 loguru 记录重要事件

```python
from loguru import logger

class MyBot(BaseBot):
    async def on_message(self, message: Message) -> None:
        try:
            logger.info(f"处理消息: {message.id}")
            # 处理逻辑
            await self.send_reply(message, "完成")
        except Exception as e:
            logger.error(f"错误: {e}")
            await self.send_reply(message, "抱歉，出错了")
```
