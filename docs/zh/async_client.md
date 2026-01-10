# AsyncClient API

`AsyncClient` 是与 Zulip 服务器交互的核心异步客户端。

## 类：AsyncClient

```python
from bot_sdk import AsyncClient
```

### 初始化

```python
client = AsyncClient(
    email: Optional[str] = None,
    api_key: Optional[str] = None,
    config_file: Optional[str] = None,
    verbose: bool = False,
    retry_on_errors: bool = True,
    site: Optional[str] = None,
    client: Optional[str] = None,
    cert_bundle: Optional[str] = None,
    insecure: Optional[bool] = None,
    client_cert: Optional[str] = None,
    client_cert_key: Optional[str] = None,
)
```

#### 参数

- **email** (`str`, 可选): Bot 或用户的邮箱地址
- **api_key** (`str`, 可选): API 密钥
- **config_file** (`str`, 可选): 配置文件路径（默认 `~/.zuliprc`）
- **verbose** (`bool`): 是否启用详细日志（默认 `False`）
- **retry_on_errors** (`bool`): 遇到错误时是否重试（默认 `True`）
- **site** (`str`, 可选): Zulip 服务器 URL
- **client** (`str`, 可选): 客户端名称（用于 User-Agent）
- **cert_bundle** (`str`, 可选): CA 证书包路径
- **insecure** (`bool`, 可选): 是否禁用 SSL 验证（不推荐）
- **client_cert** (`str`, 可选): 客户端证书路径
- **client_cert_key** (`str`, 可选): 客户端证书密钥路径

### 配置文件格式

默认从 `~/.zuliprc` 读取配置：

```ini
[api]
email=bot@example.com
key=your-api-key-here
site=https://your-zulip-server.com
```

### 主要方法

#### 生命周期管理

##### ensure_session()

```python
await client.ensure_session()
```

确保 HTTP 会话已初始化。通常在发送请求前自动调用。

##### aclose()

```python
await client.aclose()
```

关闭客户端并清理资源。

**示例**：

```python
async with AsyncClient() as client:
    # 使用 client
    pass
# 自动关闭
```

#### 用户信息

##### get_profile()

```python
profile = await client.get_profile()
```

获取当前用户的个人资料。

**返回**: `UserProfileResponse`

**字段**：

- `user_id`: 用户 ID
- `email`: 邮箱地址
- `full_name`: 全名
- `is_bot`: 是否为 Bot
- `is_admin`: 是否为管理员
- `avatar_url`: 头像 URL
- `timezone`: 时区

**示例**：

```python
profile = await client.get_profile()

print(f"Bot ID: {profile.user_id}")
print(f"Name: {profile.full_name}")
```

#### 消息操作


##### send_message()

```python
response = await client.send_message(request: Dict[str, Any])

```

发送消息（支持频道消息和私聊消息）。

**参数**：

- **request**: 消息请求字典，包含：
  - `type`: "stream" 或 "private"
  - `to`: 接收者（频道 ID 或用户 ID 列表）
  - `topic`: 主题（仅频道消息）
  - `content`: 消息内容（支持 Markdown）

**返回**: `SendMessageResponse`

**示例**：

```python
# 发送频道消息
from bot_sdk import StreamMessageRequest

await client.send_message(
    StreamMessageRequest(
        to=123,  # 频道 ID
        topic="General",
        content="Hello, world!"
    ).model_dump(exclude_none=True)
)

# 发送私聊消息
from bot_sdk import PrivateMessageRequest

await client.send_message(
    PrivateMessageRequest(
        to=[456],  # 用户 ID 列表
        content="Hi there!"
    ).model_dump(exclude_none=True)
)
```

##### get_messages()

```python
messages = await client.get_messages(request: Dict[str, Any])
```

获取消息历史。

**参数**：

- `anchor`: 锚点消息 ID
- `num_before`: 锚点之前的消息数
- `num_after`: 锚点之后的消息数
- `narrow`: 过滤条件

**返回**: 消息列表

##### update_message()

```python
await client.update_message(request: Dict[str, Any])
```

更新已发送的消息。

##### delete_message()

```python
await client.delete_message(message_id: int)
```

删除消息。

#### 事件和长轮询

##### register()

```python
response = await client.register(
    event_types: Optional[List[str]] = None,
    narrow: Optional[List[List[str]]] = None,
    **kwargs
)
```

注册事件队列。

**参数**：

- **event_types**: 事件类型列表（如 `["message"]`）
- **narrow**: 过滤条件

**返回**: `RegisterResponse` 包含 `queue_id` 和 `last_event_id`

**示例**：

```python
reg = await client.register(
    event_types=["message", "presence"]
)
queue_id = reg.queue_id
```

##### get_events()

```python
response = await client.get_events(
    queue_id: str,
    last_event_id: int = -1
)
```

获取事件（长轮询）。

**返回**: `EventsResponse` 包含事件列表

##### call_on_each_event()

```python
await client.call_on_each_event(
    callback: Callable[[Event], Awaitable[None]],
    event_types: Optional[List[str]] = None,
    narrow: Optional[List[List[str]]] = None
)
```

持续监听事件并调用回调函数。

**参数**：

- **callback**: 事件处理函数
- **event_types**: 监听的事件类型
- **narrow**: 过滤条件

**示例**：

```python
async def handle_event(event: Event):
    if event.type == "message":
        print(f"收到消息: {event.message.content}")

await client.call_on_each_event(
    handle_event,
    event_types=["message"]
)
```

##### deregister()

```python
await client.deregister(queue_id: str)
```

注销事件队列。

#### 频道操作

##### get_streams()

```python
streams = await client.get_streams(**kwargs)
```

获取所有频道列表。

##### get_stream_id()

```python
stream_id = await client.get_stream_id(stream_name: str)
```

通过名称获取频道 ID。

##### get_subscriptions()

```python
response = await client.get_subscriptions()
```

获取当前用户订阅的频道。

**返回**: `SubscriptionsResponse`

##### subscribe()

```python
await client.subscribe(streams: List[Dict[str, Any]])
```

订阅频道。

##### unsubscribe()

```python
await client.unsubscribe(streams: List[str])
```

取消订阅频道。

#### 用户状态

##### update_presence()

```python
await client.update_presence(request: UpdatePresenceRequest)
```

更新用户在线状态。

**示例**：

```python
from bot_sdk import UpdatePresenceRequest

await client.update_presence(
    UpdatePresenceRequest(status="active")
)
```

##### get_presence()

```python
presence = await client.get_presence(**kwargs)
```

获取用户在线状态。

#### 低级 API

##### call_endpoint()

```python
result = await client.call_endpoint(
    url: str,
    method: str = "POST",
    request: Optional[Dict[str, Any]] = None,
    longpolling: bool = False,
    files: Optional[List[IO[Any]]] = None,
    timeout: Optional[float] = None
)
```

直接调用 Zulip API 端点。

## 使用模式

### 上下文管理器

```python
async with AsyncClient() as client:
    profile = await client.get_profile()
    print(profile.full_name)
```

### 手动管理

```python
client = AsyncClient()
try:
    await client.ensure_session()
    # 使用 client
finally:
    await client.aclose()
```

### 与 BotRunner 配合

```python
from bot_sdk import BotRunner, BaseBot

runner = BotRunner(
    lambda c: MyBot(c),
    client_kwargs={"config_file": "~/.zuliprc"}
)

async with runner:
    await runner.run_forever()
```

## 异常处理

### 异常类型

- `ZulipError`: 基础异常
- `ConfigNotFoundError`: 配置文件未找到
- `MissingURLError`: 缺少服务器 URL
- `UnrecoverableNetworkError`: 无法恢复的网络错误

### 示例

```python
from bot_sdk import AsyncClient, ConfigNotFoundError

try:
    client = AsyncClient(config_file="/invalid/path")
except ConfigNotFoundError as e:
    print(f"配置错误: {e}")
```

## 注意事项

1. **总是使用 await**: 所有方法都是异步的
2. **正确关闭**: 使用 `aclose()` 或上下文管理器
3. **错误重试**: 默认启用，可通过 `retry_on_errors=False` 禁用
4. **长轮询**: 获取事件时自动处理长轮询超时
5. **SSL 验证**: 生产环境不要使用 `insecure=True`
