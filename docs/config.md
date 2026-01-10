# Configuration

Configure bots via `bots.yaml` using Pydantic models `AppConfig` / `BotConfig`.

## BotConfig (per bot)

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
