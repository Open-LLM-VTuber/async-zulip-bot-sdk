# 数据模型 API

Bot SDK 使用 Pydantic 模型定义所有数据结构，提供类型安全和自动验证。

## 目录

- [请求模型](#请求模型)
- [响应模型](#响应模型)
- [数据类型](#数据类型)

## 请求模型

### StreamMessageRequest

发送频道消息的请求。

```python
from bot_sdk import StreamMessageRequest

request = StreamMessageRequest(
    to: int | str | List[int] | List[str],
    topic: str,
    content: str,
    type: Literal["stream"] = "stream"  # 自动设置
)
```

**示例**：

- `message`: 新消息
- `reaction`: 反应变化
- `presence`: 在线状态变化
- `typing`: 输入状态
- `update_message`: 消息更新
- `delete_message`: 消息删除
- `realm_user`: 用户变化

```python
# 使用频道 ID
request = StreamMessageRequest(
    to=123,
    topic="General",
    content="Hello, world!"
)

# 使用频道名称
request = StreamMessageRequest(
    to="general",
    topic="Announcements",
    content="**Important**: Meeting at 3pm"
)

# 发送
await client.send_message(request.model_dump(exclude_none=True))
```

### PrivateMessageRequest

发送私聊消息的请求。

```python
from bot_sdk import PrivateMessageRequest

request = PrivateMessageRequest(
    to: List[int] | List[str],
    content: str,
    type: Literal["private"] = "private"  # 自动设置
)
```

**字段**：

- **to**: 接收者用户 ID 或邮箱列表
- **content**: 消息内容
- **type**: 消息类型（自动设置为 "private"）

**示例**：

```python
# 发送给单个用户
request = PrivateMessageRequest(
    to=[456],
    content="Hi there!"
)

# 发送给多个用户（群聊）
request = PrivateMessageRequest(
    to=[456, 789],
    content="Hello everyone!"
)

# 使用邮箱
request = PrivateMessageRequest(
    to=["user1@example.com", "user2@example.com"],
    content="Meeting reminder"
)

await client.send_message(request.model_dump(exclude_none=True))
```

### UpdatePresenceRequest

更新用户在线状态的请求。

```python
from bot_sdk import UpdatePresenceRequest

request = UpdatePresenceRequest(
    status: Literal["active", "idle"],
    new_user_input: Optional[bool] = None,
    ping_only: Optional[bool] = None,
    last_update_id: Optional[int] = None,
    history_limit_days: Optional[int] = None
)
```

**字段**：

- **status**: 状态（"active" 或 "idle"）
- **new_user_input**: 是否有新用户输入
- **ping_only**: 仅发送 ping
- **last_update_id**: 上次更新 ID
- **history_limit_days**: 历史限制天数

**示例**：

```python
# 设置为活跃
await client.update_presence(
    UpdatePresenceRequest(status="active")
)

# 设置为空闲
await client.update_presence(
    UpdatePresenceRequest(status="idle")
)
```

## 响应模型

### RegisterResponse

注册事件队列的响应。

```python
@dataclass
class RegisterResponse:
    queue_id: str
    last_event_id: int
    result: str
    msg: str = ""
```

**字段**：

- **queue_id**: 队列 ID（用于获取事件）
- **last_event_id**: 最后事件 ID
- **result**: 结果状态（"success" 或 "error"）
- **msg**: 消息

**示例**：

```python
response = await client.register(event_types=["message"])
print(f"Queue ID: {response.queue_id}")
print(f"Last Event ID: {response.last_event_id}")
```

### EventsResponse

获取事件的响应。

```python
@dataclass
class EventsResponse:
    result: str
    msg: str = ""
    events: List[Event] = []
```

**字段**：

- **result**: 结果状态
- **msg**: 消息
- **events**: 事件列表

**示例**：

```python
response = await client.get_events(queue_id, last_event_id)
for event in response.events:
    print(f"Event {event.id}: {event.type}")
```

### SendMessageResponse

发送消息的响应。

```python
@dataclass
class SendMessageResponse:
    result: str
    msg: str = ""
    id: Optional[int] = None
```

**字段**：

- **result**: 结果状态
- **msg**: 消息
- **id**: 消息 ID（成功时）

**示例**：

```python
response = await client.send_message(request.model_dump(exclude_none=True))
if response.result == "success":
    print(f"Message sent with ID: {response.id}")
else:
    print(f"Error: {response.msg}")
```

### UserProfileResponse

用户资料响应。

```python
@dataclass
class UserProfileResponse(User):
    result: str
    msg: str = ""
```

继承自 `User`，包含所有用户字段。

**示例**：

```python
profile = await client.get_profile()
print(f"User ID: {profile.user_id}")
print(f"Name: {profile.full_name}")
print(f"Email: {profile.email}")
print(f"Is Bot: {profile.is_bot}")
print(f"Is Admin: {profile.is_admin}")
```

### SubscriptionsResponse

订阅列表响应。

```python
@dataclass
class SubscriptionsResponse:
    result: str
    msg: str = ""
    subscriptions: List[Channel] = []
```

**示例**：

```python
response = await client.get_subscriptions()
for channel in response.subscriptions:
    print(f"{channel.name} (ID: {channel.stream_id})")
```

### ChannelResponse

单个频道信息响应。

```python
@dataclass
class ChannelResponse:
    result: str
    msg: str = ""
    stream: Channel
```

## 数据类型

### Message

消息对象。

```python
@dataclass
class Message:
    id: int
    type: Literal["stream", "private"]
    content: str
    sender_id: int
    sender_email: str
    sender_full_name: str
    client: Optional[str] = None
    stream_id: Optional[int] = None
    display_recipient: Optional[Union[List[PrivateRecipient], str]] = None
    subject: Optional[str] = None
    topic: Optional[str] = None
```

**属性**：

- **id**: 消息 ID
- **type**: 消息类型（"stream" 或 "private"）
- **content**: 消息内容
- **sender_id**: 发送者用户 ID
- **sender_email**: 发送者邮箱
- **sender_full_name**: 发送者全名
- **stream_id**: 频道 ID（频道消息）
- **display_recipient**: 接收者信息
- **subject/topic**: 主题

**方法**：
- **topic_or_subject**: 属性，返回 topic 或 subject（兼容性）

**示例**：

```python
async def on_message(self, message: Message):
    print(f"From: {message.sender_full_name}")
    print(f"Content: {message.content}")
    
    if message.type == "stream":
        print(f"Stream ID: {message.stream_id}")
        print(f"Topic: {message.topic_or_subject}")
    else:
        print("Private message")
```

### Event

事件对象。

```python
@dataclass
class Event:
    id: int
    type: str
    message: Optional[Message] = None
    op: Optional[str] = None
```

**字段**：

- **id**: 事件 ID
- **type**: 事件类型（"message", "presence", "reaction" 等）
- **message**: 消息对象（message 事件）
- **op**: 操作类型（某些事件）

**事件类型**：

- `message`: 新消息
- `reaction`: 反应变化
- `presence`: 在线状态变化
- `typing`: 输入状态
- `update_message`: 消息更新
- `delete_message`: 消息删除
- `realm_user`: 用户变化

**示例**：

```python
async def on_event(self, event: Event):
    if event.type == "message":
        print(f"New message: {event.message.content}")
    elif event.type == "reaction":
        print(f"Reaction: {event.op}")
    elif event.type == "presence":
        print("Presence updated")
```

### User

用户信息。

```python
@dataclass
class User:
    email: str
    user_id: int
    full_name: Optional[str] = None
    delivery_email: Optional[str] = None
    avatar_url: Optional[str] = None
    avatar_version: Optional[int] = None
    is_admin: Optional[bool] = None
    is_owner: Optional[bool] = None
    is_guest: Optional[bool] = None
    is_bot: Optional[bool] = None
    role: Optional[int] = None
    timezone: Optional[str] = None
    is_active: Optional[bool] = None
    date_joined: Optional[str] = None
    profile_data: Optional[Dict[str, ProfileFieldValue]] = None
    max_message_id: Optional[int] = None
```

**示例**：

```python
profile = await client.get_profile()
if profile.is_admin:
    print("This is an admin account")
if profile.is_bot:
    print("This is a bot account")
```

### PrivateRecipient

私聊接收者信息。

```python
@dataclass
class PrivateRecipient:
    id: int
    email: Optional[str] = None
    full_name: Optional[str] = None
    short_name: Optional[str] = None
    type: Optional[str] = None
```

**示例**：

```python
if message.type == "private":
    recipients = message.display_recipient
    if isinstance(recipients, list):
        for recipient in recipients:
            print(f"Recipient: {recipient.full_name} ({recipient.email})")
```

### Channel

频道（Stream）信息。

```python
@dataclass
class Channel:
    stream_id: int
    name: str
    description: Optional[str] = None
    rendered_description: Optional[str] = None
    invite_only: Optional[bool] = None
    is_web_public: Optional[bool] = None
    history_public_to_subscribers: Optional[bool] = None
    stream_post_policy: Optional[int] = None
    message_retention_days: Optional[int] = None
    is_announcement_only: Optional[bool] = None
    first_message_id: Optional[int] = None
    creation_date: Optional[int] = None
    stream_weekly_traffic: Optional[int] = None
```

**示例**：

```python
subs = await client.get_subscriptions()
for channel in subs.subscriptions:
    print(f"Channel: {channel.name}")
    if channel.invite_only:
        print("  (Private)")
    if channel.description:
        print(f"  Description: {channel.description}")
```

### ProfileFieldValue

用户资料字段值。

```python
@dataclass
class ProfileFieldValue:
    value: Optional[str] = None
    rendered_value: Optional[str] = None
```

## 使用示例

### 发送不同类型的消息

```python
from bot_sdk import AsyncClient, StreamMessageRequest, PrivateMessageRequest

async def send_messages():
    client = AsyncClient()
    
    # 频道消息
    await client.send_message(
        StreamMessageRequest(
            to="general",
            topic="Announcement",
            content="**Important**: System maintenance tonight"
        ).model_dump(exclude_none=True)
    )
    
    # 私聊消息
    await client.send_message(
        PrivateMessageRequest(
            to=[123],
            content="Hi! How are you?"
        ).model_dump(exclude_none=True)
    )
    
    await client.aclose()
```

### 处理不同类型的事件

```python
from bot_sdk import BaseBot, Event, Message

class EventBot(BaseBot):
    async def on_event(self, event: Event):
        if event.type == "message":
            await self.handle_message(event.message)
        elif event.type == "reaction":
            await self.handle_reaction(event)
        else:
            await super().on_event(event)
    
    async def handle_message(self, message: Message):
        print(f"Message from {message.sender_full_name}")
    
    async def handle_reaction(self, event: Event):
        print(f"Reaction: {event.op}")
    
    async def on_message(self, message: Message):
        # 处理普通消息
        pass
```

### 访问用户信息

```python
from bot_sdk import BaseBot, Message

class UserInfoBot(BaseBot):
    async def post_init(self):
        await super().post_init()
        
        # 获取自己的信息
        profile = await self.client.get_profile()
        self.bot_email = profile.email
        self.bot_name = profile.full_name
        
        print(f"Bot started: {self.bot_name} ({self.bot_email})")
    
    async def on_message(self, message: Message):
        # 访问发送者信息
        sender = message.sender_full_name
        sender_email = message.sender_email
        
        await self.send_reply(
            message,
            f"Hello {sender}! Your email is {sender_email}"
        )
```

## 最佳实践

1. **使用 model_dump()**：发送请求时使用 `model_dump(exclude_none=True)`
2. **类型检查**：利用类型注解进行 IDE 自动补全
3. **可选字段**：检查可选字段是否为 None
4. **Pydantic 验证**：让 Pydantic 自动验证数据

```python
from bot_sdk import StreamMessageRequest
from pydantic import ValidationError

try:
    request = StreamMessageRequest(
        to=123,
        topic="Test",
        content="Hello"
    )
    # Pydantic 自动验证
    await client.send_message(request.model_dump(exclude_none=True))
except ValidationError as e:
    print(f"Invalid data: {e}")
```
