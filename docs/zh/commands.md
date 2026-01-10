# 命令系统 API

Bot SDK 提供了强大的命令解析和处理系统。

## CommandParser

命令解析器负责从消息中识别和解析命令。

### 类：CommandParser

```python
from bot_sdk import CommandParser
```

#### 初始化

```python
parser = CommandParser(
    prefixes: Sequence[str] = ("/", "!"),
    *,
    enable_mentions: bool = True,
    mention_aliases: Optional[Iterable[str]] = None,
    specs: Optional[Iterable[CommandSpec]] = None,
    auto_help: bool = True,
)
```

**参数**：

- **prefixes**: 命令前缀元组（默认 `("/", "!")`）
- **enable_mentions**: 是否启用 @-提及触发命令
- **mention_aliases**: 提及别名列表
- **specs**: 初始命令规范列表
- **auto_help**: 是否自动添加 help 命令

**示例**：

```python
parser = CommandParser(
    prefixes=("/", "!", "#"),
    enable_mentions=True,
    auto_help=True
)
```

### 方法

#### register_spec()

```python
parser.register_spec(spec: CommandSpec) -> None
```

注册命令规范。

**示例**：

```python
from bot_sdk import CommandSpec, CommandArgument

parser.register_spec(
    CommandSpec(
        name="greet",
        description="打招呼",
        args=[
            CommandArgument(name="name", type=str, required=True)
        ],
        handler=async_handler_function
    )
)
```

#### parse_message()

```python
invocation = parser.parse_message(message: Message) -> Optional[CommandInvocation]
```

从消息中解析命令。

**返回**：

- `CommandInvocation`: 如果是命令
- `None`: 如果不是命令

#### parse_text()

```python
invocation = parser.parse_text(text: str) -> CommandInvocation
```

直接从文本解析命令。

**异常**：

- `CommandError`: 空命令
- `UnknownCommandError`: 未知命令
- `InvalidArgumentsError`: 参数错误

**示例**：

```python
try:
    inv = parser.parse_text("greet Alice")
    print(inv.name)  # "greet"
    print(inv.args)  # {"name": "Alice"}
except CommandError as e:
    print(f"命令错误: {e}")
```

#### dispatch()

```python
await parser.dispatch(
    invocation: CommandInvocation,
    *,
    message: Any,
    bot: Any
) -> None
```

分发命令到处理器。

#### generate_help()

```python
help_text = parser.generate_help() -> str
```

生成概览帮助文本。

#### 内置 help 命令（支持单条指令详情）

- 默认自动注册 `help` 命令。
- 用法：
    - `!help`：显示所有命令概要
    - `!help <command>`：显示指定指令的详细用法、参数描述、别名、最小权限（若设置）

#### add_identity_aliases()

```python
parser.add_identity_aliases(
    *,
    full_name: Optional[str] = None,
    email: Optional[str] = None,
    extra: Optional[Iterable[str]] = None
) -> None
```

添加 Bot 身份的提及别名。

## CommandSpec

命令规范定义命令的结构和行为。

### 类：CommandSpec

```python
from bot_sdk import CommandSpec

@dataclass
class CommandSpec:
    name: str
    description: str = ""
    args: List[CommandArgument] = field(default_factory=list)
    aliases: List[str] = field(default_factory=list)
    allow_extra: bool = False
    handler: Optional[Callable] = None
    show_in_help: bool = True
    min_level: Optional[int] = None

### 字段

- **name** (`str`): 命令名称（必需）
- **description** (`str`): 命令描述
- **args** (`List[CommandArgument]`): 参数列表
- **aliases** (`List[str]`): 命令别名
- **allow_extra** (`bool`): 是否允许额外参数
- **handler** (`Callable`): 命令处理函数
- **show_in_help** (`bool`): 是否在帮助中显示
- **min_level** (`int`, 可选): 最小权限等级；BaseBot 在分发前会校验

参数的 `description` 字段会出现在 `!help <command>` 的详细帮助输出中。

### 示例

#### 简单命令

```python
CommandSpec(
    name="ping",
    description="检查 Bot 是否在线",
    handler=handle_ping
)

async def handle_ping(invocation, message, bot):
    await bot.send_reply(message, "Pong! 🏓")
```

#### 带参数的命令

```python
CommandSpec(
    name="calculate",
    description="计算两数之和",
    args=[
        CommandArgument(name="a", type=int, required=True),
        CommandArgument(name="b", type=int, required=True),
    ],
    handler=handle_calculate
)

async def handle_calculate(invocation, message, bot):
    a = invocation.args["a"]
    b = invocation.args["b"]
    result = a + b
    await bot.send_reply(message, f"{a} + {b} = {result}")
```

#### 带别名的命令

```python
CommandSpec(
    name="status",
    description="显示 Bot 状态",
    aliases=["s", "info", "stat"],
    handler=handle_status
)

# 以下都会触发此命令：
# /status
# /s
# /info
# /stat
```

#### 可变参数命令

```python
CommandSpec(
    name="echo",
    description="回显所有输入",
    args=[
        CommandArgument(
            name="words",
            type=str,
            multiple=True,  # 捕获所有剩余参数
            description="要回显的词语"
        )
    ],
    handler=handle_echo
)

async def handle_echo(invocation, message, bot):
    words = invocation.args["words"]  # 列表
    text = " ".join(words)
    await bot.send_reply(message, text)

# 用法: /echo hello world everyone
# 结果: words = ["hello", "world", "everyone"]
```

#### 可选参数命令

```python
CommandSpec(
    name="greet",
    description="打招呼",
    args=[
        CommandArgument(
            name="name",
            type=str,
            required=False,  # 可选
            description="要打招呼的人（可选）"
        )
    ],
    handler=handle_greet
)

async def handle_greet(invocation, message, bot):
    name = invocation.args.get("name")
    if name:
        await bot.send_reply(message, f"你好，{name}!")
    else:
        await bot.send_reply(message, "大家好!")
```

## CommandArgument

命令参数定义。

### 类：CommandArgument

```python
from bot_sdk import CommandArgument

@dataclass
class CommandArgument:
    name: str
    type: type = str
    required: bool = True
    description: str = ""
    multiple: bool = False
```

### 字段

- **name** (`str`): 参数名称
- **type** (`type`): 参数类型（`str`, `int`, `float`, `bool`）
- **required** (`bool`): 是否必需
- **description** (`str`): 参数描述
- **multiple** (`bool`): 是否捕获多个值

### 支持的类型

#### 字符串 (str)

```python
CommandArgument(name="message", type=str)
# 用法: /cmd hello
# 结果: args["message"] = "hello"
```

#### 整数 (int)

```python
CommandArgument(name="count", type=int)
# 用法: /cmd 42
# 结果: args["count"] = 42
```

#### 浮点数 (float)

```python
CommandArgument(name="price", type=float)
# 用法: /cmd 19.99
# 结果: args["price"] = 19.99
```

#### 布尔值 (bool)

```python
CommandArgument(name="enabled", type=bool)
# 用法: /cmd true
# 结果: args["enabled"] = True

# 支持的值：
# true: "true", "1", "yes", "y", "on"
# false: "false", "0", "no", "n", "off"
```

### 示例

```python
CommandSpec(
    name="config",
    description="配置设置",
    args=[
        CommandArgument(
            name="key",
            type=str,
            required=True,
            description="配置键"
        ),
        CommandArgument(
            name="value",
            type=str,
            required=True,
            description="配置值"
        ),
        CommandArgument(
            name="persistent",
            type=bool,
            required=False,
            description="是否持久化"
        ),
    ],
    handler=handle_config
)

async def handle_config(invocation, message, bot):
    key = invocation.args["key"]
    value = invocation.args["value"]
    persistent = invocation.args.get("persistent", False)
    
    # 保存配置...
    await bot.send_reply(
        message,
        f"设置 {key}={value} (持久化: {persistent})"
    )

# 用法: /config theme dark true
```

## CommandInvocation

命令调用实例，包含解析后的命令信息。

### 类：CommandInvocation

```python
@dataclass
class CommandInvocation:
    name: str
    args: Dict[str, Any]
    tokens: List[str]
    spec: CommandSpec
```

### 字段

- **name**: 命令名称
- **args**: 解析后的参数字典
- **tokens**: 原始词语列表
- **spec**: 对应的 CommandSpec

### 示例

```python
# 命令: /greet Alice --loud
inv = CommandInvocation(
    name="greet",
    args={"name": "Alice", "loud": True},
    tokens=["greet", "Alice", "--loud"],
    spec=greet_spec
)
```

## 异常

- `CommandError`: 空命令或解析错误
- `UnknownCommandError`: 未知命令
- `InvalidArgumentsError`: 参数错误（错误信息会包含 Usage，便于纠正）

```python
try:
    inv = parser.parse_text("")
except CommandError as e:
    print(f"命令错误: {e}")
```

### UnknownCommandError

未知命令错误。

```python
from bot_sdk import UnknownCommandError

try:
    inv = parser.parse_text("invalid_command")
except UnknownCommandError as e:
    print(f"未知命令: {e}")
```

### InvalidArgumentsError

参数错误。

```python
from bot_sdk import InvalidArgumentsError

try:
    inv = parser.parse_text("greet")  # 缺少必需参数
except InvalidArgumentsError as e:
    print(f"参数错误: {e}")
    print(f"命令: {e.command}")
```

## 完整示例

### 完整的命令 Bot

```python
from bot_sdk import (
    BaseBot, Message, CommandSpec, CommandArgument,
    CommandInvocation, run_bot
)

class CalculatorBot(BaseBot):
    def __init__(self, client):
        super().__init__(client)
        
        # 加法
        self.command_parser.register_spec(
            CommandSpec(
                name="add",
                description="计算两数之和",
                aliases=["plus", "+"],
                args=[
                    CommandArgument(name="a", type=float, required=True),
                    CommandArgument(name="b", type=float, required=True),
                ],
                handler=self.handle_add
            )
        )
        
        # 乘法
        self.command_parser.register_spec(
            CommandSpec(
                name="multiply",
                description="计算两数之积",
                aliases=["mul", "*"],
                args=[
                    CommandArgument(name="a", type=float, required=True),
                    CommandArgument(name="b", type=float, required=True),
                ],
                handler=self.handle_multiply
            )
        )
        
        # 幂运算
        self.command_parser.register_spec(
            CommandSpec(
                name="power",
                description="计算 a 的 b 次方",
                aliases=["pow", "**"],
                args=[
                    CommandArgument(name="base", type=float, required=True),
                    CommandArgument(name="exponent", type=float, required=True),
                ],
                handler=self.handle_power
            )
        )
    
    async def handle_add(self, inv: CommandInvocation, message, bot):
        result = inv.args["a"] + inv.args["b"]
        await self.send_reply(
            message,
            f"{inv.args['a']} + {inv.args['b']} = {result}"
        )
    
    async def handle_multiply(self, inv: CommandInvocation, message, bot):
        result = inv.args["a"] * inv.args["b"]
        await self.send_reply(
            message,
            f"{inv.args['a']} × {inv.args['b']} = {result}"
        )
    
    async def handle_power(self, inv: CommandInvocation, message, bot):
        result = inv.args["base"] ** inv.args["exponent"]
        await self.send_reply(
            message,
            f"{inv.args['base']} ^ {inv.args['exponent']} = {result}"
        )
    
    async def on_message(self, message: Message) -> None:
        await self.send_reply(
            message,
            "我是计算器 Bot！使用 /help 查看可用命令。"
        )

if __name__ == "__main__":
    run_bot(CalculatorBot)
```

## 最佳实践

1. **清晰的命令名称**：使用动词作为命令名
2. **提供别名**：为常用命令提供短别名
3. **详细的描述**：帮助用户理解命令用途
4. **参数验证**：在处理器中验证参数合法性
5. **错误反馈**：提供清晰的错误消息

```python
async def handle_command(inv, message, bot):
    try:
        # 验证参数
        if inv.args["value"] < 0:
            await bot.send_reply(message, "❌ 值必须为正数")
            return
        
        # 处理命令
        result = process(inv.args["value"])
        await bot.send_reply(message, f"✅ 结果: {result}")
        
    except Exception as e:
        logger.error(f"命令处理失败: {e}")
        await bot.send_reply(message, "❌ 命令执行失败，请稍后重试")
```
