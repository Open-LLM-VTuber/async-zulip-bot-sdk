# Logging

SDK logging utilities for bots.

The SDK uses [Loguru](https://github.com/Delgan/loguru) for logging, providing structured and colored output out of the box.

## Logger setup

```python
from bot_sdk import setup_logging

setup_logging(level="INFO", json_logs=False)
```

### Parameters

- **level**: Log level (e.g. `DEBUG`, `INFO`, `WARNING`, `ERROR`).
- **json_logs**: Output JSON lines when `True` (useful for production/ingestion).

### Console Integration

When running the interactive console (`main.py`):
- Logs are automatically captured and displayed in the "Logs" panel.
- Console UI (Rich) preserves ANSI colors for readability.
- Log levels can be filtered similarly.

## Example

```python
from bot_sdk import setup_logging
from loguru import logger

if __name__ == "__main__":
    setup_logging(level="DEBUG")
    logger.info("Bot starting...")
    # Your bot startup here
```

