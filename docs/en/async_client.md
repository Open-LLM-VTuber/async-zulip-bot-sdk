# AsyncClient API

`AsyncClient` is the core async client for talking to the Zulip server.

## Class: AsyncClient

```python
from bot_sdk import AsyncClient
```

### Initialization

```python
client = AsyncClient(
    email: str | None = None,
    api_key: str | None = None,
    config_file: str | None = None,
    verbose: bool = False,
    retry_on_errors: bool = True,
    site: str | None = None,
    client: str | None = None,
    cert_bundle: str | None = None,
    insecure: bool | None = None,
    client_cert: str | None = None,
    client_cert_key: str | None = None,
)
```

#### Parameters

- **email**: Bot or user email
- **api_key**: API key
- **config_file**: Path to `.zuliprc` (default `~/.zuliprc`)
- **verbose**: Verbose logging toggle
- **retry_on_errors**: Auto retry on network errors
- **site**: Zulip server URL
- **client**: Client name (User-Agent)
- **cert_bundle**: CA bundle path
- **insecure**: Disable TLS verification (not recommended)
- **client_cert**: Client certificate path
- **client_cert_key**: Client certificate key path

### Config file format

```ini
[api]
email=bot@example.com
key=your-api-key-here
site=https://your-zulip-server.com
```

## Key Methods

### Lifecycle

- **ensure_session()**: Initialize HTTP session if missing.
- **aclose()**: Close session and release resources.

### User info

- **get_profile()** → `UserProfileResponse`

### Messages

- **send_message(request)** → `SendMessageResponse`
- **get_messages(request)**
- **update_message(request)**
- **delete_message(message_id)**

### Events & long polling

- **register(event_types=None, narrow=None, \*\*kwargs)** → `RegisterResponse`
- **get_events(queue_id, last_event_id=-1)** → `EventsResponse`
- **call_on_each_event(callback, event_types=None, narrow=None)**
- **deregister(queue_id)**

### Streams

- **get_streams(**kwargs)**
- **get_stream_id(stream_name)**
- **get_subscriptions()** → `SubscriptionsResponse`
- **subscribe(streams)**
- **unsubscribe(streams)**

### Presence

- **update_presence(request: UpdatePresenceRequest)**
- **get_presence(**kwargs)**

### Low-level

- **call_endpoint(url, method="POST", request=None, longpolling=False, files=None, timeout=None)**

## Usage Patterns

### Context manager

```python
async with AsyncClient() as client:
    profile = await client.get_profile()
    print(profile.full_name)
```

### Manual management

```python
client = AsyncClient()
try:
    await client.ensure_session()
    # ... use client ...
finally:
    await client.aclose()
```

### With BotRunner

```python
from bot_sdk import BotRunner, BaseBot

runner = BotRunner(
    lambda c: MyBot(c),
    client_kwargs={"config_file": "~/.zuliprc"}
)

async with runner:
    await runner.run_forever()
```

## Exceptions

- `ZulipError`: Base exception
- `ConfigNotFoundError`: Config file missing
- `MissingURLError`: Missing Zulip server URL
- `UnrecoverableNetworkError`: Cannot connect to server

## Notes

- Always `await` async methods.
- Close the client via `aclose()` or `async with`.
- Retries are enabled by default; disable with `retry_on_errors=False`.
- Long polling is handled automatically for event fetching.
- Do not use `insecure=True` in production.
