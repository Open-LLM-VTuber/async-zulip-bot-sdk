# 配置

通过 `bots.yaml`（全局配置多个 Bot）和 `bot.yaml`（各 Bot 目录内的本地配置）来配置 Bot。

## BotLocalConfig（Per-Bot 本地设置）

存储在 `bot.yaml`（与 bot 模块在同一目录）。字段说明：

- `owner_user_id` (int，可选)：显式指定 bot 所有者（Zulip user_id），独立于组织 owner/admin。
- `language` (str，默认 `"en"`)：此 bot 的默认语言/地区代码（如 `"en"`, `"zh"`）。控制 i18n 系统加载哪个翻译文件。
- `role_levels` (dict[str, int])：角色名到权限等级的映射。默认：
  - `user`: 1
  - `admin`: 50
  - `owner`: 100
  - `bot_owner`: 200
  
  等级越高权限越大。用于检查带 `min_level` 的命令。可按 bot 自定义。
  
- `settings` (dict，默认 `{}`)：其他 bot 特定的任意键值对。

**示例 `bot.yaml`**：

```yaml
owner_user_id: 42
language: zh
role_levels:
  user: 1
  moderator: 30
  admin: 50
  owner: 100
  bot_owner: 200
settings:
  custom_key: custom_value
```

修改 `bot.yaml` 后，可使用 `!reload`（管理员级别命令）在不重启 bot 的情况下重新加载配置和翻译。

## BotConfig（bots.yaml 中的单个 Bot）

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
