# Configuration

Configure bots via `bots.yaml` using Pydantic models `AppConfig` / `BotConfig`.

## BotLocalConfig (per-bot settings)

Stored in `bot.yaml` (same directory as the bot module). **Breaking change:** class-level attributes are no longer read; configure everything here.

Fields (with defaults):

- `command_prefixes` (list[str], default `['!']`): Command prefixes.
- `enable_mention_commands` (bool, default `true`): Treat @-mentions as commands.
- `auto_help_command` (bool, default `true`): Auto-register built-in help command.
- `enable_storage` (bool, default `true`): Enable KV storage.
- `storage_path` (str, optional): Override KV DB path; otherwise `bot_data/<bot>.db`.
- `storage` (`StorageConfig`, default object): KV flush/cache settings.
- `enable_orm` (bool, default `false`): Enable ORM; reuses storage DB unless `orm_db_path` set.
- `orm_db_path` (str, optional): Separate ORM DB path.
- `owner_user_id` (int, optional): Explicit bot owner (Zulip user_id).
- `language` (str, default `"en"`): Locale for i18n.
- `role_levels` (dict[str, int], default `{user:1, admin:50, owner:100, bot_owner:200}`): Permission levels.
- `settings` (dict, default `{}`): Arbitrary bot-specific settings.

**Example `bot.yaml`**:

```yaml
command_prefixes: ["!", "/"]
enable_mention_commands: true
auto_help_command: true
enable_storage: true
enable_orm: false
language: en
role_levels:
  user: 1
  moderator: 30
  admin: 50
  owner: 100
  bot_owner: 200
settings:
  custom_key: custom_value
```

After editing `bot.yaml`, use `!reload` (admin-level command) to reload settings and translations without restarting.

## BotConfig (per bot in bots.yaml)

Fields:
- `name` (str): Bot name/id.
- `module` (str, optional): Python module path of the bot.
- `class_name` (str, optional): Bot class name.
- `enabled` (bool, default `True`): Skip bots when false.
- `zuliprc` (str, optional): Path to Zulip credentials file.
- `event_types` (list[str], default `["message"]`): Zulip events to subscribe to.
- `config` (dict, default `{}`): Custom bot-specific settings, passed to the bot factory.
- `storage` (`StorageConfig`, optional): KV storage behavior (auto-cache, flush intervals, retries).

## StorageConfig

- `auto_cache` (bool): Enable always-on KV cache with periodic flush.
- `auto_flush_interval` (float): Seconds between flush attempts.
- `auto_flush_retry` (float): Delay between retries when the DB is busy.
- `auto_flush_max_retries` (int): Max retries per key per flush cycle.

## AppConfig (multiple bots)

- `bots`: List of `BotConfig` entries.

## bots.yaml example

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
    enabled: false  # disabled
```

## Loading configuration

```python
from bot_sdk.config import load_config, AppConfig

# You may load your other yaml files similarly
# Of course, define your own Pydantic models as needed
app_config = load_config("bots.yaml", AppConfig)
for bot_cfg in app_config.bots:
    if bot_cfg.enabled:
        print(bot_cfg.name, bot_cfg.storage)
```

## Notes on migrations

- SDK-level migrations (if any) belong under the SDK path and cover only shared tables.
- Bot-specific schemas should keep their own Alembic config and migrations inside each bot directory.
