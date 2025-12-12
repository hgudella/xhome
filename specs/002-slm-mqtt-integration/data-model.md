# Data Model: SLM Command Processing and MQTT Integration

**Feature**: 002-slm-mqtt-integration  
**Date**: 2025-12-11  
**Phase**: 1 - Design

## Overview

This document defines the data entities for the SLM command processing and MQTT integration feature. All entities are ephemeral (in-memory only) to comply with privacy requirements (FR-014: no command/transcription persistence).

---

## 1. Command

**Purpose**: Represents a parsed user intent extracted from transcribed text by the SLM.

### Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `intent` | `str` (enum) | Command intent type | One of: `turn_on`, `turn_off`, `set_brightness`, `set_temperature`, `set_color`, `unknown` |
| `device` | `str` | Target device identifier (normalized) | Must match device name in configuration, snake_case format |
| `parameters` | `Dict[str, Any]` | Command-specific parameters | Optional. Keys: `brightness` (0-100), `temperature` (int), `color` (str), `mode` (str) |
| `confidence` | `float` | SLM confidence score | 0.0-1.0. If <0.7, may request clarification |
| `timestamp` | `datetime` | When command was extracted | UTC timestamp |
| `raw_transcription` | `str` | Original transcribed text (ephemeral) | **Discarded after command extraction** per FR-014 |

### Validation Rules

- `intent` must be in allowed enum values
- `device` must exist in device configuration before MQTT publishing
- `parameters` keys must match device capabilities (e.g., `brightness` only for lights)
- `confidence` < 0.5 → intent should be `unknown`

### Example

```python
@dataclass
class Command:
    intent: str
    device: str
    parameters: Dict[str, Any]
    confidence: float
    timestamp: datetime
    raw_transcription: Optional[str] = None  # Cleared after processing
    
    def to_mqtt_payload(self) -> Dict[str, Any]:
        """Convert to MQTT message payload"""
        payload = {"state": "ON" if self.intent == "turn_on" else "OFF"}
        payload.update(self.parameters)
        return payload
    
    def __post_init__(self):
        # Validate intent
        allowed_intents = {"turn_on", "turn_off", "set_brightness", 
                          "set_temperature", "set_color", "unknown"}
        if self.intent not in allowed_intents:
            raise ValueError(f"Invalid intent: {self.intent}")
```

### Relationships

- **One-to-One** with `CommandSession` (each command belongs to one session)
- **Many-to-One** with `DeviceMapping` (many commands target one device)
- **One-to-One** with `MQTTMessage` (each command generates one MQTT message)

---

## 2. DeviceMapping

**Purpose**: Links natural language device references to MQTT topics and capabilities.

### Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `name` | `str` | Canonical device identifier | Unique, snake_case (e.g., `living_room_light`) |
| `aliases` | `List[str]` | Alternative names user might say | Case-insensitive matching (e.g., ["living room light", "lounge light"]) |
| `device_type` | `str` (enum) | Type of device | One of: `light`, `switch`, `thermostat`, `fan`, `sensor` |
| `command_topic` | `str` | MQTT topic for commands | Format: `home/{type}/{location}/set` |
| `state_topic` | `str` | MQTT topic for state updates | Format: `home/{type}/{location}/state` |
| `capabilities` | `List[str]` | Supported operations | E.g., [`on_off`, `brightness`, `color_temp`] |
| `location` | `str` | Physical location | Optional. E.g., "living_room", "bedroom" |

### Validation Rules

- `name` must be unique across all devices
- `command_topic` and `state_topic` must be valid MQTT topic patterns
- `capabilities` must be in allowed set: `on_off`, `brightness`, `color_temp`, `temperature`, `humidity`, `mode`
- At least one `alias` must be provided

### Example

```python
@dataclass
class DeviceMapping:
    name: str
    aliases: List[str]
    device_type: str
    command_topic: str
    state_topic: str
    capabilities: List[str]
    location: Optional[str] = None
    
    def supports_capability(self, capability: str) -> bool:
        """Check if device supports a specific capability"""
        return capability in self.capabilities
    
    def matches(self, user_input: str) -> bool:
        """Check if user input matches this device"""
        normalized = user_input.lower().strip()
        return normalized == self.name or normalized in [a.lower() for a in self.aliases]
```

### Relationships

- **One-to-Many** with `Command` (one device can receive many commands)
- **One-to-One** with `DeviceState` (each device has one current state)

### Storage

- Loaded from `config/devices.yaml` at startup
- Indexed in memory by both `name` and `aliases` for fast lookup
- **Not persisted** during runtime (read-only configuration)

---

## 3. MQTTMessage

**Purpose**: Represents a message to be published to the MQTT broker.

### Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `topic` | `str` | MQTT topic to publish to | Must match device `command_topic` |
| `payload` | `Dict[str, Any]` or `str` | Message content | JSON dict for structured data, string for simple messages |
| `qos` | `int` | Quality of Service level | Fixed at 1 per FR-020 (at least once delivery) |
| `retain` | `bool` | Whether broker should retain message | Default: False for commands |
| `timestamp` | `datetime` | When message was created | UTC timestamp |
| `device_id` | `str` | Target device identifier | Reference to `DeviceMapping.name` |

### Validation Rules

- `topic` must be non-empty and valid MQTT format (no wildcards in publish topics)
- `qos` must be 1 (per FR-020 specification)
- `payload` must be JSON-serializable if dict

### Example

```python
@dataclass
class MQTTMessage:
    topic: str
    payload: Union[Dict[str, Any], str]
    qos: int = 1  # Fixed per FR-020
    retain: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    device_id: Optional[str] = None
    
    def to_json(self) -> str:
        """Serialize payload to JSON string"""
        if isinstance(self.payload, dict):
            return json.dumps(self.payload)
        return str(self.payload)
    
    @classmethod
    def from_command(cls, command: Command, device: DeviceMapping) -> 'MQTTMessage':
        """Create MQTT message from a Command"""
        return cls(
            topic=device.command_topic,
            payload=command.to_mqtt_payload(),
            device_id=device.name
        )
```

### Relationships

- **One-to-One** with `Command` (each command generates one message)
- **Many-to-One** with `DeviceMapping` (many messages target one device topic)

### Lifecycle

1. Created from `Command` + `DeviceMapping`
2. Published to MQTT broker
3. Confirmation received (QoS 1 ACK)
4. **Discarded** (not persisted)

---

## 4. DeviceState

**Purpose**: Tracks the current state of a device based on MQTT state messages.

### Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `device_id` | `str` | Device identifier | Must match `DeviceMapping.name` |
| `state` | `Dict[str, Any]` | Current device state | Keys: `state` ("ON"/"OFF"), `brightness` (0-100), `temperature` (int), etc. |
| `last_updated` | `datetime` | When state was last updated | UTC timestamp |
| `available` | `bool` | Whether device is online/reachable | False if offline or state is stale |
| `ttl_seconds` | `int` | Time-to-live for this state | Default: 300 seconds (5 minutes) |

### State Freshness

- State is considered **fresh** if `(now - last_updated) < ttl_seconds`
- State is considered **stale** if TTL expired
- Stale state still returned but marked as `available=False`

### Validation Rules

- `device_id` must exist in device configuration
- `state` must contain at minimum a `state` key with "ON" or "OFF"
- `last_updated` must be <= current time
- `ttl_seconds` must be > 0

### Example

```python
@dataclass
class DeviceState:
    device_id: str
    state: Dict[str, Any]
    last_updated: datetime
    available: bool = True
    ttl_seconds: int = 300
    
    def is_fresh(self) -> bool:
        """Check if state is within TTL"""
        age = datetime.utcnow() - self.last_updated
        return age.total_seconds() < self.ttl_seconds
    
    def is_on(self) -> Optional[bool]:
        """Check if device is currently on"""
        if not self.is_fresh():
            return None  # Unknown state
        return self.state.get('state') == 'ON'
    
    def get_brightness(self) -> Optional[int]:
        """Get current brightness level (0-100)"""
        if not self.is_fresh():
            return None
        return self.state.get('brightness')
```

### Relationships

- **One-to-One** with `DeviceMapping` (each device has one state)
- **Updated by** incoming MQTT state messages

### Storage

- **In-memory cache only** (no persistence)
- Indexed by `device_id` for O(1) lookup
- Cleared and repopulated on application restart
- Thread-safe updates via locking mechanism

---

## 5. CommandSession

**Purpose**: Represents the lifecycle of a single voice command from transcription to MQTT publication.

### Attributes

| Attribute | Type | Description | Constraints |
|-----------|------|-------------|-------------|
| `session_id` | `str` (UUID) | Unique session identifier | Auto-generated UUID |
| `transcribed_text` | `str` | Input from Feature 001 | Ephemeral, discarded after command extraction |
| `command` | `Optional[Command]` | Extracted command | None if parsing failed |
| `mqtt_message` | `Optional[MQTTMessage]` | Generated MQTT message | None if command invalid |
| `start_time` | `datetime` | Session start timestamp | UTC timestamp |
| `end_time` | `Optional[datetime]` | Session completion timestamp | UTC timestamp |
| `duration_ms` | `Optional[float]` | Total processing time | Calculated: end_time - start_time |
| `status` | `str` (enum) | Session outcome | One of: `success`, `failed`, `timeout`, `unknown_intent` |
| `error` | `Optional[str]` | Error message if failed | User-friendly error description |

### State Transitions

```
START → TRANSCRIBED → PARSED → VALIDATED → PUBLISHED → SUCCESS
   ↓        ↓           ↓          ↓            ↓
  FAILED  FAILED     FAILED    FAILED       FAILED
```

### Validation Rules

- `session_id` must be unique (UUID ensures this)
- `duration_ms` must be calculated from `end_time - start_time`
- `status` must be set before session completion
- If `status == "failed"`, `error` must be populated

### Example

```python
from uuid import uuid4

@dataclass
class CommandSession:
    session_id: str = field(default_factory=lambda: str(uuid4()))
    transcribed_text: Optional[str] = None
    command: Optional[Command] = None
    mqtt_message: Optional[MQTTMessage] = None
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    duration_ms: Optional[float] = None
    status: str = "in_progress"
    error: Optional[str] = None
    
    def complete(self, status: str, error: Optional[str] = None):
        """Mark session as complete"""
        self.end_time = datetime.utcnow()
        self.duration_ms = (self.end_time - self.start_time).total_seconds() * 1000
        self.status = status
        self.error = error
        
        # Clear ephemeral data per FR-014
        self.transcribed_text = None
    
    def to_log_entry(self) -> Dict[str, Any]:
        """Create privacy-safe log entry (no PII)"""
        return {
            "session_id": self.session_id,
            "intent": self.command.intent if self.command else None,
            "device": self.command.device if self.command else None,
            "duration_ms": self.duration_ms,
            "status": self.status,
            "error": self.error
        }
```

### Relationships

- **One-to-One** with `Command` (one session produces one command)
- **One-to-One** with `MQTTMessage` (one session publishes one message)

### Lifecycle

1. Created when transcription received from Feature 001
2. Command extracted by SLM
3. Device validated against configuration
4. State checked (optional, User Story 3)
5. MQTT message published
6. Session completed with status
7. **Discarded** after logging metadata (no persistence)

---

## Data Flow Diagram

```
[Voice Input (Feature 001)]
         ↓
  transcribed_text
         ↓
[CommandSession created]
         ↓
[SLM Parser] → [Command] ← validates → [DeviceMapping]
         ↓                                    ↓
   [State Cache] ← reads ← [DeviceState]    |
         ↓                                    ↓
   [MQTTMessage] ← from_command() ← [Command + DeviceMapping]
         ↓
   [MQTT Client]
         ↓
  [MQTT Broker] → publishes → [Home Devices]
         ↓
   [State Update] → updates → [DeviceState]
         ↓
[CommandSession complete]
```

---

## Privacy & Retention

Per FR-014 and constitution Privacy-First Architecture:

| Entity | Retention | Justification |
|--------|-----------|---------------|
| `Command.raw_transcription` | Cleared immediately after parsing | Privacy requirement |
| `CommandSession.transcribed_text` | Cleared on session completion | Privacy requirement |
| `Command` | Discarded after MQTT publish | Ephemeral processing only |
| `MQTTMessage` | Discarded after publish confirmation | Ephemeral processing only |
| `DeviceState` | In-memory with 5-min TTL | Operational need, no PII |
| `DeviceMapping` | Read-only configuration | Static, no user data |

**Logging**: Only metadata logged (intent, device, timestamp, duration, status). No transcriptions or command parameters logged per FR-013.

---

## Validation Checklist

- [x] All entities defined with attributes and types
- [x] Relationships between entities documented
- [x] Validation rules specified for each entity
- [x] Privacy requirements addressed (0-day retention)
- [x] Example implementations provided
- [x] Data flow diagram included

**Status**: ✅ Data Model Complete
