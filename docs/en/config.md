# Configuration

How to configure the SDK via `Config`.

## Config class

```python
from bot_sdk import Config

Config(
    email: str,
    api_key: str,
    realm: str,
    site: str | None = None,
    bot_name: str | None = None,
    bot_aliases: list[str] | None = None,
    parse_stream_mentions: bool = False,
    cache_dir: str | Path | None = None,
)
```

### Fields

- **email**: Bot email.
- **api_key**: Bot API key.
- **realm**: Zulip realm (server URL).
- **site**: Optional site name for logging.
- **bot_name**: Display name.
- **bot_aliases**: Extra @mention aliases.
- **parse_stream_mentions**: Parse `@**stream**` mentions.
- **cache_dir**: Cache directory for tokens, etc.

## Loading config

- **Environment variables**: `BOT_EMAIL`, `BOT_API_KEY`, `BOT_REALM`.
- **YAML file**: `bots.yaml` supports multiple bot configs.

```yaml
bots:
  - name: echo
    email: echo-bot@example.com
    api_key: YOUR_API_KEY
    realm: https://chat.example.com
```

## Validation tips

- Ensure realm URL ends with scheme (`https://`).
- Keep API keys secret; prefer env vars in CI.
- Provide aliases matching how users mention the bot.
