# Contract: MQTT Publisher Interface

**Feature**: 002-slm-mqtt-integration  
**Component**: `src/devices/mqtt_client.py`  
**Purpose**: MQTT broker communication for command publishing and state subscription

## Interface

### `class MQTTClient`

Manages MQTT broker connection, command publishing, and device state subscriptions.

#### Initialization

```python
def __init__(
    self,
    broker_host: str,
    broker_port: int = 1883,
    username: Optional[str] = None,
    password: Optional[str] = None,
    client_id: str = "home_automation_assistant",
    qos: int = 1,
    keepalive: int = 60
):
    """
    Initialize MQTT client with broker connection parameters.
    
    Args:
        broker_host: MQTT broker hostname or IP address
        broker_port: MQTT broker port (default: 1883)
        username: Optional authentication username
        password: Optional authentication password
        client_id: MQTT client identifier (must be unique per broker)
        qos: Quality of Service level (default: 1 per FR-020)
        keepalive: Connection keepalive interval in seconds (default: 60)
    
    Note: Does not connect immediately. Call connect() to establish connection.
    """
```

#### Connection Management

```python
def connect(self, timeout: int = 30) -> bool:
    """
    Connect to MQTT broker with retry logic.
    
    Args:
        timeout: Maximum time to wait for connection (seconds)
    
    Returns:
        True if connected successfully, False otherwise
    
    Raises:
        MQTTConnectionError: If connection fails after all retry attempts
    
    Retry Behavior:
        - 3 attempts maximum
        - Exponential backoff: 2, 4, 8 seconds between attempts
        - Returns True on first successful connection
    
    Example:
        >>> client = MQTTClient("localhost", 1883)
        >>> if client.connect(timeout=30):
        ...     print("Connected")
    """

def disconnect(self):
    """
    Gracefully disconnect from MQTT broker.
    Stops background loop and closes connection.
    Should be called during application shutdown.
    """

def is_connected(self) -> bool:
    """
    Check if client is currently connected to broker.
    
    Returns:
        True if connected, False otherwise
    """
```

#### Command Publishing

```python
def publish_command(
    self,
    topic: str,
    payload: Dict[str, Any],
    retain: bool = False,
    timeout: float = 5.0
) -> bool:
    """
    Publish a command message to MQTT broker with QoS 1 confirmation.
    
    Args:
        topic: MQTT topic to publish to (e.g., "home/light/living_room/set")
        payload: Command payload as dictionary (will be JSON serialized)
        retain: Whether broker should retain this message (default: False)
        timeout: Maximum time to wait for publish confirmation (seconds)
    
    Returns:
        True if published and confirmed, False otherwise
    
    Raises:
        MQTTPublishError: If publish fails or times out
        ConnectionError: If not connected to broker
        ValueError: If topic is empty or payload is not serializable
    
    QoS Behavior (Level 1):
        - Guarantees at-least-once delivery
        - Waits for PUBACK from broker
        - May result in duplicate messages (devices should handle idempotently)
    
    Example:
        >>> client.publish_command(
        ...     "home/light/living_room/set",
        ...     {"state": "ON", "brightness": 75}
        ... )
        True
    """
```

#### State Subscription

```python
def subscribe_state_topics(self, topics: List[str]) -> bool:
    """
    Subscribe to device state update topics.
    
    Args:
        topics: List of MQTT topics (supports wildcards, e.g., "home/+/state")
    
    Returns:
        True if all subscriptions successful, False otherwise
    
    Raises:
        ConnectionError: If not connected to broker
    
    Callback Behavior:
        - State updates received via on_message callback
        - Automatically updates internal state cache
        - Runs in background thread (non-blocking)
    
    Example:
        >>> client.subscribe_state_topics([
        ...     "home/light/+/state",
        ...     "home/switch/+/state"
        ... ])
        True
    """

def set_state_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
    """
    Register callback function for state updates.
    
    Args:
        callback: Function called when state message received
                  Signature: callback(device_id: str, state: Dict[str, Any])
    
    Example:
        >>> def handle_state(device_id, state):
        ...     print(f"{device_id} is now {state}")
        >>> client.set_state_callback(handle_state)
    """
```

## Input/Output Contracts

### Input: `publish_command(topic, payload, ...)`

**Preconditions**:
- Client must be connected (`is_connected() == True`)
- `topic` must be non-empty, valid MQTT topic (no wildcards)
- `payload` must be JSON-serializable dictionary
- Topic should match device's `command_topic` from configuration

**Valid Input Examples**:
```python
publish_command("home/light/living_room/set", {"state": "ON"})
publish_command("home/light/bedroom/set", {"state": "ON", "brightness": 50})
publish_command("home/climate/main/set", {"temperature": 22, "mode": "cool"})
```

**Invalid Input Examples**:
```python
publish_command("", {"state": "ON"})  # Empty topic → ValueError
publish_command("home/+/set", {})  # Wildcard in publish topic → ValueError
publish_command("home/light/set", {"state": lambda: "ON"})  # Non-serializable → ValueError
```

### Output: Boolean + Exceptions

**Success Path** (`returns True`):
1. Message serialized to JSON
2. Published to broker with QoS 1
3. PUBACK received within timeout
4. Logged as successful

**Failure Paths**:
- **ConnectionError**: Not connected to broker
- **MQTTPublishError**: Publish failed or timed out
- **ValueError**: Invalid input parameters

## Error Handling

### `MQTTConnectionError`
**When**: Cannot establish connection to broker  
**User Message**: "Home automation system is offline. Please check the connection"  
**Recovery**: Automatic reconnection every 30 seconds (SC-009)

### `MQTTPublishError`
**When**: Message publish fails or times out  
**User Message**: "Could not send command to {device}. {reason}"  
**Recovery**: Log error, notify user, don't retry automatically

### Connection Loss During Operation
**Behavior**: 
- paho-mqtt handles automatic reconnection
- Queued messages may be lost if QoS 0
- QoS 1 messages will be retried after reconnection
- Application notified via `on_disconnect` callback

## Performance Requirements

- **Connection Time**: <5 seconds to broker on local network (SC-009: 30s max)
- **Publish Latency**: <100ms for QoS 1 publish + PUBACK
- **Throughput**: Support 10+ commands/second without backlog
- **Memory**: <50MB for client + message queue
- **Reconnection**: Automatic within 30 seconds of broker availability (SC-009)

## MQTT Protocol Details

### QoS Level: 1 (At Least Once)

**Rationale** (from FR-020 clarification):
- Guarantees message delivery (important for device commands)
- Allows duplicates (devices should handle idempotently)
- Lower overhead than QoS 2 (no 4-way handshake)
- Suitable for home automation where occasional duplicates are harmless

**Message Flow**:
```
Client                    Broker                    Device
  |-- PUBLISH (QoS 1) ----->|                         |
  |<----- PUBACK -----------|                         |
  |                         |-- PUBLISH (QoS 1) ----->|
  |                         |<----- PUBACK -----------|
```

### Topic Structure

**Command Topics** (publish):
```
home/{device_type}/{location}/set
Examples:
  home/light/living_room/set
  home/switch/fan/set
  home/climate/bedroom/set
```

**State Topics** (subscribe):
```
home/{device_type}/{location}/state
Wildcards:
  home/+/+/state          # All devices
  home/light/+/state      # All lights
```

### Payload Format

**JSON Structure**:
```json
{
  "state": "ON" | "OFF",
  "brightness": 0-100,      // Optional, lights only
  "temperature": int,       // Optional, thermostats only
  "color": "warm_white",    // Optional, lights only
  "mode": "cool" | "heat"   // Optional, thermostats only
}
```

## Testing Requirements

### Contract Tests (`tests/contract/test_mqtt_client_contract.py`)

1. **Connection**: Connect to test broker successfully
2. **Publish Success**: Publish message, verify PUBACK received
3. **Subscription**: Subscribe to topic, receive test message
4. **Disconnect**: Graceful shutdown without errors
5. **QoS 1 Confirmation**: Verify wait_for_publish() succeeds

### Unit Tests (`tests/unit/test_mqtt_client.py`)

1. **JSON Serialization**: Test payload → JSON conversion
2. **Topic Validation**: Reject empty/wildcard topics for publish
3. **Retry Logic**: Test exponential backoff on connection failure
4. **Callback Handling**: Verify state_callback invoked correctly
5. **Thread Safety**: Test concurrent publish operations

### Integration Tests (`tests/integration/test_text_to_command_pipeline.py`)

1. **End-to-End Publishing**: Command → MQTT → verify message on broker
2. **State Subscription**: Publish state → verify cache updated
3. **Connection Recovery**: Kill broker → restart → verify reconnection
4. **Multiple Commands**: Publish 20 commands rapidly

## Dependencies

- `paho-mqtt>=1.6.0`: MQTT client library
- `json`: Payload serialization (stdlib)
- `threading`: Background loop and locking (stdlib)
- `time`: Retry delays (stdlib)
- `logging`: Operational logging (stdlib)

## Thread Safety

- **Publish Operations**: Thread-safe with internal locking
- **Subscriptions**: Thread-safe (callbacks run in paho-mqtt thread)
- **Connection Management**: Thread-safe
- **Recommendation**: Safe for concurrent use from multiple threads

## Configuration

Environment variables and config file settings:

```yaml
# config/mqtt.yaml
broker:
  host: localhost          # Override with MQTT_BROKER_HOST env var
  port: 1883              # Override with MQTT_BROKER_PORT env var
  username: null          # Override with MQTT_USERNAME env var
  password: null          # Override with MQTT_PASSWORD env var
  
client:
  client_id: "home_automation_assistant"
  qos: 1                  # Fixed per FR-020
  keepalive: 60
  clean_session: true
  
connection:
  timeout: 30
  retry_attempts: 3
  retry_backoff: [2, 4, 8]  # Exponential backoff in seconds
  
topics:
  command_prefix: "home"
  state_suffix: "state"
  command_suffix: "set"
```

## Privacy Compliance

- **No Command Logging**: Never log full command payloads
- **Metadata Only**: Log topic, device ID, success/failure, latency
- **No Transcriptions**: Commands should not contain original transcription text

```python
# GOOD: Privacy-safe logging
logger.info(f"Published to {topic}: success={result}, latency={latency}ms")

# BAD: Privacy violation (if payload contains user data)
# logger.info(f"Published payload: {json.dumps(payload)}")  ⚠️ Use with caution
```

## Monitoring & Observability

**Logged Events**:
- Connection established/lost
- Publish success/failure
- Subscription confirmations
- QoS acknowledgments
- Error conditions

**Metrics** (optional):
- Publish latency (p50, p95, p99)
- Connection uptime
- Messages published per minute
- Failed publish count

---

**Contract Status**: ✅ Complete  
**Implements**: FR-008, FR-009, FR-010, FR-016, FR-020  
**Success Criteria**: SC-003, SC-009
