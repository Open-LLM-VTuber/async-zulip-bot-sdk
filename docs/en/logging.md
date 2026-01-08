# Logging

SDK logging utilities for bots.

## Logger setup

```python
from bot_sdk import setup_logging

setup_logging(level="INFO", json_format=False)
```

### Parameters

- **level**: `DEBUG`, `INFO`, `WARNING`, `ERROR`.
- **json_format**: Output JSON lines when `True`.

### Notes

- Uses standard `logging` module.
- JSON output is structured for log ingestion.
- Adjust handler/formatter as needed in your app.

## Example

```python
from bot_sdk import setup_logging

if __name__ == "__main__":
    setup_logging(level="DEBUG", json_format=True)
    # Your bot startup here
```
