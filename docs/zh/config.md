# 配置（bots.yaml）

通过 `bots.yaml` 配置多个 Bot，Pydantic 模型为 `AppConfig` / `BotConfig`。

## BotConfig（单个 Bot）

字段说明：
- `name` (str)：Bot 名称/标识。
- `module` (str，可选)：Bot 所在的 Python 模块路径。
- `class_name` (str，可选)：Bot 类名。
- `enabled` (bool，默认 `True`)：是否启用该 Bot。
- `zuliprc` (str，可选)：Zulip 凭据文件路径。
- `event_types` (list[str]，默认 `["message"]`)：订阅的 Zulip 事件类型。
- `config` (dict，默认 `{}`)：自定义配置，原样传给 bot 工厂。
- `storage` (`StorageConfig`，可选)：KV 存储行为（自动缓存、flush 间隔、重试策略）。

## StorageConfig

- `auto_cache` (bool)：是否启用常驻 KV 缓存并定期 flush。
- `auto_flush_interval` (float)：两次 flush 之间的秒数。
- `auto_flush_retry` (float)：DB 忙时的重试间隔（秒）。
- `auto_flush_max_retries` (int)：每次 flush、每个键的最大重试次数。

## AppConfig（多 Bot）

- `bots`：`BotConfig` 列表。

## bots.yaml 示例

```yaml
bots:
  - name: dev_bot
    module: bots.dev_bot
    class_name: TranslatorBot
    enabled: true
    zuliprc: bots/dev_bot/zuliprc
    event_types: ["message"]
    storage:
      auto_cache: true
      auto_flush_interval: 5.0
      auto_flush_retry: 1.0
      auto_flush_max_retries: 3
    config:
      native_language_default: "en"

  - name: echo_bot
    module: bots.echo_bot
    class_name: EchoBot
    enabled: false  # 关闭该 Bot
```

## 加载配置

```python
from bot_sdk.config import load_config, AppConfig

app_config = load_config("bots.yaml", AppConfig)
for bot_cfg in app_config.bots:
    if bot_cfg.enabled:
        print(bot_cfg.name, bot_cfg.storage)
```

## 迁移说明

- SDK 级迁移（若有）只覆盖共享表，放在 SDK 路径下。
- 每个 Bot 的业务表和 Alembic 迁移应放在各自的 Bot 目录中，互不干扰。
