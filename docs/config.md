# 配置管理 API

Bot SDK 提供了灵活的配置管理系统，支持 YAML 配置文件和 Pydantic 模型验证。

## 配置模型

### BotConfig

单个 Bot 的配置。

```python
from bot_sdk import BotConfig

@dataclass
class BotConfig:
    name: str
    module: Optional[str] = None
    class_name: Optional[str] = None
    enabled: bool = True
    zuliprc: Optional[str] = None
    config: dict[str, Any] = Field(default_factory=dict)
```

#### 字段

- **name** (`str`): Bot 名称（必需）
- **module** (`str`, 可选): Python 模块名
- **class_name** (`str`, 可选): Bot 类名
- **enabled** (`bool`): 是否启用（默认 `True`）
- **zuliprc** (`str`, 可选): Zulip 配置文件路径
- **config** (`dict`): 自定义配置字典

#### 示例

```python
bot_config = BotConfig(
    name="echo_bot",
    module="my_bots",
    class_name="EchoBot",
    enabled=True,
    zuliprc="~/.zuliprc",
    config={
        "prefix": "!",
        "max_length": 1000,
    }
)
```

### AppConfig

应用级配置，包含多个 Bot。

```python
from bot_sdk import AppConfig

@dataclass
class AppConfig:
    bots: List[BotConfig] = Field(default_factory=list)
```

#### 字段

- **bots**: Bot 配置列表

#### 示例

```python
app_config = AppConfig(
    bots=[
        BotConfig(name="bot1", class_name="Bot1"),
        BotConfig(name="bot2", class_name="Bot2"),
    ]
)
```

## 配置函数

### load_config()

```python
from bot_sdk import load_config

config = load_config(
    path: str,
    model: type[BaseModel]
) -> BaseModel
```

从 YAML 文件加载配置。

#### 参数

- **path**: 配置文件路径
- **model**: Pydantic 模型类

#### 返回

模型实例

#### 示例

```python
from bot_sdk.config import load_config, AppConfig

config = load_config("bots.yaml", AppConfig)
print(f"Loaded {len(config.bots)} bots")
```

## 配置文件格式

### Zulip 凭据配置 (.zuliprc)

```ini
[api]
email=bot@example.com
key=your-api-key-here
site=https://your-zulip-server.com

# 可选配置
[api]
insecure=false
cert_bundle=/path/to/ca-bundle.crt
```

#### 字段说明

- **email**: Bot 或用户的邮箱地址
- **key**: API 密钥
- **site**: Zulip 服务器 URL
- **insecure**: 是否禁用 SSL 验证（不推荐）
- **cert_bundle**: CA 证书包路径

### Bot 配置文件 (bots.yaml)

```yaml
bots:
  - name: echo_bot
    module: my_bots
    class_name: EchoBot
    enabled: true
    zuliprc: ~/.zuliprc
    config:
      prefix: "!"
      max_message_length: 1000

  - name: greeter_bot
    module: my_bots
    class_name: GreeterBot
    enabled: true
    zuliprc: ~/.zuliprc-greeter
    config:
      greeting: "Hello"
      farewell: "Goodbye"

  - name: disabled_bot
    module: my_bots
    class_name: DisabledBot
    enabled: false
```

#### 字段说明

- **name**: Bot 名称标识符
- **module**: Bot 类所在的 Python 模块
- **class_name**: Bot 类名
- **enabled**: 是否启用此 Bot
- **zuliprc**: 该 Bot 的 Zulip 配置文件路径
- **config**: Bot 特定的自定义配置

## 使用示例

### 基础用法

#### 1. 创建配置文件

创建 `bots.yaml`:

```yaml
bots:
  - name: my_bot
    module: bots.my_bot
    class_name: MyBot
    enabled: true
    zuliprc: ~/.zuliprc
    config:
      debug: false
      timeout: 30
```

#### 2. 加载配置

```python
from bot_sdk.config import load_config, AppConfig

config = load_config("bots.yaml", AppConfig)

for bot_config in config.bots:
    if bot_config.enabled:
        print(f"Bot: {bot_config.name}")
        print(f"Module: {bot_config.module}")
        print(f"Class: {bot_config.class_name}")
```

### 动态加载 Bot

```python
import asyncio
import importlib
from bot_sdk import BotRunner
from bot_sdk.config import load_config, AppConfig

async def main():
    config = load_config("bots.yaml", AppConfig)
    runners = []
    
    for bot_config in config.bots:
        if not bot_config.enabled:
            continue
        
        # 动态导入模块和类
        module = importlib.import_module(bot_config.module)
        bot_cls = getattr(module, bot_config.class_name)
        
        # 创建 runner
        runner = BotRunner(
            lambda c, cls=bot_cls, cfg=bot_config: cls(c, cfg.config),
            client_kwargs={
                "config_file": bot_config.zuliprc or "~/.zuliprc"
            }
        )
        
        runners.append(runner)
        await runner.start()
    
    # 运行所有 bot
    await asyncio.gather(*[r.run_forever() for r in runners])

if __name__ == "__main__":
    asyncio.run(main())
```

### 使用自定义配置

#### Bot 实现

```python
from bot_sdk import BaseBot, Message

class ConfigurableBot(BaseBot):
    def __init__(self, client, custom_config: dict):
        super().__init__(client)
        
        # 读取自定义配置
        self.prefix = custom_config.get("prefix", "/")
        self.max_length = custom_config.get("max_message_length", 500)
        self.debug = custom_config.get("debug", False)
    
    async def on_message(self, message: Message):
        if self.debug:
            print(f"[DEBUG] Received: {message.content}")
        
        # 检查消息长度
        if len(message.content) > self.max_length:
            await self.send_reply(
                message,
                f"Message too long (max {self.max_length} chars)"
            )
            return
        
        await self.send_reply(message, "Processed!")
```

#### 配置文件

```yaml
bots:
  - name: my_configurable_bot
    module: bots.configurable
    class_name: ConfigurableBot
    enabled: true
    zuliprc: ~/.zuliprc
    config:
      prefix: "!"
      max_message_length: 1000
      debug: true
```

### 多环境配置

#### 开发环境 (dev.yaml)

```yaml
bots:
  - name: test_bot
    module: bots.test_bot
    class_name: TestBot
    enabled: true
    zuliprc: ~/.zuliprc-dev
    config:
      debug: true
      log_level: DEBUG
      api_timeout: 60
```

#### 生产环境 (prod.yaml)

```yaml
bots:
  - name: prod_bot
    module: bots.prod_bot
    class_name: ProdBot
    enabled: true
    zuliprc: ~/.zuliprc-prod
    config:
      debug: false
      log_level: INFO
      api_timeout: 30
```

#### 加载脚本

```python
import os
import sys
from bot_sdk.config import load_config, AppConfig

# 根据环境变量选择配置
env = os.getenv("BOT_ENV", "dev")
config_file = f"{env}.yaml"

try:
    config = load_config(config_file, AppConfig)
    print(f"Loaded {env} configuration")
except FileNotFoundError:
    print(f"Config file {config_file} not found")
    sys.exit(1)
```

### 自定义配置模型

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from bot_sdk.config import load_config

class DatabaseConfig(BaseModel):
    host: str
    port: int = 5432
    database: str
    username: str
    password: str

class BotCustomConfig(BaseModel):
    name: str
    enabled: bool = True
    zuliprc: str
    database: DatabaseConfig
    features: List[str] = Field(default_factory=list)

class CustomAppConfig(BaseModel):
    bots: List[BotCustomConfig]
    global_timeout: int = 30
    log_level: str = "INFO"

# 配置文件 custom.yaml
"""
bots:
  - name: db_bot
    enabled: true
    zuliprc: ~/.zuliprc
    database:
      host: localhost
      port: 5432
      database: bot_db
      username: bot_user
      password: secret
    features:
      - logging
      - caching

global_timeout: 60
log_level: DEBUG
"""

# 加载
config = load_config("custom.yaml", CustomAppConfig)
print(f"Global timeout: {config.global_timeout}")
for bot in config.bots:
    print(f"Bot {bot.name} database: {bot.database.host}")
```

## 完整示例

### 生产环境配置系统

#### 目录结构

```
project/
├── config/
│   ├── base.yaml
│   ├── dev.yaml
│   └── prod.yaml
├── bots/
│   ├── __init__.py
│   ├── echo_bot.py
│   └── admin_bot.py
└── main.py
```

#### config/base.yaml

```yaml
bots:
  - name: echo_bot
    module: bots.echo_bot
    class_name: EchoBot
    enabled: true
    config:
      max_message_length: 1000
      rate_limit: 10

  - name: admin_bot
    module: bots.admin_bot
    class_name: AdminBot
    enabled: true
    config:
      admin_users:
        - admin@example.com
      allowed_commands:
        - restart
        - status
```

#### config/dev.yaml

```yaml
bots:
  - name: echo_bot
    module: bots.echo_bot
    class_name: EchoBot
    enabled: true
    zuliprc: ~/.zuliprc-dev
    config:
      max_message_length: 1000
      rate_limit: 100
      debug: true

  - name: admin_bot
    module: bots.admin_bot
    class_name: AdminBot
    enabled: false
```

#### config/prod.yaml

```yaml
bots:
  - name: echo_bot
    module: bots.echo_bot
    class_name: EchoBot
    enabled: true
    zuliprc: /etc/zulip/bot.zuliprc
    config:
      max_message_length: 500
      rate_limit: 10
      debug: false

  - name: admin_bot
    module: bots.admin_bot
    class_name: AdminBot
    enabled: true
    zuliprc: /etc/zulip/admin.zuliprc
    config:
      admin_users:
        - admin@company.com
      allowed_commands:
        - restart
        - status
        - logs
```

#### main.py

```python
import asyncio
import os
import sys
import importlib
from pathlib import Path
from bot_sdk import BotRunner
from bot_sdk.config import load_config, AppConfig
from loguru import logger

def load_environment_config() -> AppConfig:
    """根据环境加载配置"""
    env = os.getenv("BOT_ENV", "dev")
    config_dir = Path(__file__).parent / "config"
    config_file = config_dir / f"{env}.yaml"
    
    if not config_file.exists():
        logger.error(f"Config file not found: {config_file}")
        sys.exit(1)
    
    logger.info(f"Loading configuration from {config_file}")
    return load_config(str(config_file), AppConfig)

async def main():
    config = load_environment_config()
    runners = []
    
    for bot_config in config.bots:
        if not bot_config.enabled:
            logger.info(f"Bot {bot_config.name} is disabled, skipping")
            continue
        
        try:
            # 动态导入
            module = importlib.import_module(bot_config.module)
            bot_cls = getattr(module, bot_config.class_name)
            
            # 创建 runner
            runner = BotRunner(
                lambda c, cls=bot_cls, cfg=bot_config: cls(c, cfg.config),
                client_kwargs={
                    "config_file": bot_config.zuliprc or "~/.zuliprc"
                }
            )
            
            await runner.start()
            runners.append(runner)
            logger.info(f"Started bot: {bot_config.name}")
            
        except Exception as e:
            logger.error(f"Failed to start bot {bot_config.name}: {e}")
            continue
    
    if not runners:
        logger.error("No bots started")
        return
    
    try:
        await asyncio.gather(*[r.run_forever() for r in runners])
    finally:
        for runner in runners:
            await runner.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

#### 运行

```bash
# 开发环境
export BOT_ENV=dev
python main.py

# 生产环境
export BOT_ENV=prod
python main.py
```

## 最佳实践

1. **环境分离**：为不同环境创建独立配置文件
2. **敏感信息**：不要在配置文件中直接存储密码，使用环境变量
3. **类型验证**：使用 Pydantic 模型进行配置验证
4. **默认值**：为所有可选配置提供合理的默认值
5. **文档化**：为每个配置项添加注释说明

```yaml
# bots.yaml - 完整配置示例
bots:
  - name: my_bot
    module: bots.my_bot
    class_name: MyBot
    enabled: true
    zuliprc: ~/.zuliprc
    config:
      # 调试模式 (开发环境使用)
      debug: false
      
      # 消息处理
      max_message_length: 1000  # 最大消息长度
      rate_limit: 10            # 每分钟最大消息数
      
      # 功能开关
      features:
        - auto_reply
        - logging
        - metrics
```

## 环境变量支持

```python
import os
from bot_sdk.config import load_config, AppConfig

# 从环境变量读取配置路径
config_path = os.getenv("BOT_CONFIG", "bots.yaml")
config = load_config(config_path, AppConfig)

# 在 Bot 中使用环境变量
class MyBot(BaseBot):
    def __init__(self, client, custom_config):
        super().__init__(client)
        
        # 优先使用环境变量
        self.api_key = os.getenv("EXTERNAL_API_KEY") or custom_config.get("api_key")
        self.debug = os.getenv("DEBUG", "false").lower() == "true"
```
