# Data Models

Core request/response types used by the SDK.

## Request Types

### SendMessageRequest

```python
class SendMessageRequest(TypedDict):
    type: str
    to: int | list[int] | list[str]
    content: str
    topic: str | None
```

### EditMessageRequest

### UploadFileRequest

### GetMessagesRequest

### AddReactionRequest

## Response Types

### Response[T]

Generic response with `result`, `msg`, `data: T | None`.

### MessagesResponse

Response with `messages: list[Message]`, `result`, `msg`.

### EventsResponse

Response with `events: list[Event]`, `result`, `msg`.

## Data Types

### Message

```python
class Message(TypedDict):
    id: int
    content: str
    sender_id: int
    sender_email: str
    sender_full_name: str
    display_recipient: str | list[str]
    type: str
    subject: str
    stream_id: int | None
    is_me_message: bool | None
```

## Event

```python
class Event(TypedDict):
    id: int
    type: str
    message: Message
    flags: list[str] | None
```

## Request Types

- **SendMessageRequest**
- **EditMessageRequest**
- **UploadFileRequest**
- **GetMessagesRequest**
- **AddReactionRequest**

```python
class SendMessageRequest(TypedDict):
    type: str
    to: int | list[int] | list[str]
    content: str
    topic: str | None
```

## Response Types

- **Response[T]**: `result`, `msg`, `data: T | None`.
- **MessagesResponse**: `messages: list[Message]`, `result`, `msg`.
- **EventsResponse**: `events: list[Event]`, `result`, `msg`.

## Type Aliases

- **UserIdOrEmail**: `int | str`
- **StreamIdOrName**: `int | str`
- **TopicName**: `str`

## Notes

- All models are TypedDicts for static checking.
- Optional fields may be `None`; check before use.
- Message content is rendered Markdown from Zulip.
