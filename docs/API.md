# XHOME API Documentation

Comprehensive API documentation for the XHOME voice-controlled smart home system.

## Table of Contents

- [Feature 001: Voice-to-Text](#feature-001-voice-to-text)
  - [WhisperEngine](#whisperengine)
  - [ContinuousListener](#continuouslistener)
  - [AudioCapture](#audiocapture)
  - [VAD](#vad)
- [Feature 002: SLM & MQTT](#feature-002-slm--mqtt)
  - [CommandRouter](#commandrouter)
  - [SLMEngine](#slmengine)
  - [CommandParser](#commandparser)
  - [MQTTClient](#mqttclient)
  - [DeviceStateCache](#devicestatecache)

---

## Feature 001: Voice-to-Text

### WhisperEngine

Primary interface for speech-to-text transcription using OpenAI Whisper models.

#### Class Definition

```python
class WhisperEngine:
    def __init__(
        self,
        model_name: str = "openai/whisper-tiny",
        device: str = "cpu"
    ):
        """Initialize Whisper transcription engine.
        
        Args:
            model_name: Hugging Face model identifier
                       Options: openai/whisper-tiny, openai/whisper-base
            device: Compute device ("cpu" or "cuda")
        """
```

#### Methods

##### `transcribe(audio_array: np.ndarray) -> Transcription`

Transcribe audio to text.

**Parameters:**
- `audio_array` (np.ndarray): Audio samples at 16kHz, mono, float32 [-1.0, 1.0]

**Returns:**
- `Transcription`: Object containing transcription text, confidence, duration

**Example:**
```python
from src.transcription.whisper_engine import WhisperEngine
import numpy as np

engine = WhisperEngine(model_name="openai/whisper-base")
audio = np.random.randn(16000 * 3)  # 3 seconds
result = engine.transcribe(audio)
print(result.text)  # "Hello world"
print(result.confidence)  # 0.95
```

**Performance:**
- Latency: <3s for 3-second audio (base model, CPU)
- Memory: ~150MB (tiny), ~300MB (base)

---

### ContinuousListener

High-level interface for continuous voice capture with VAD.

#### Class Definition

```python
class ContinuousListener:
    def __init__(
        self,
        model_name: str = "openai/whisper-tiny",
        device: str = "cpu",
        on_transcription: Optional[Callable[[Transcription], None]] = None
    ):
        """Initialize continuous voice listener.
        
        Args:
            model_name: Whisper model to use
            device: Compute device
            on_transcription: Callback for each transcription
        """
```

#### Methods

##### `start() -> None`

Start continuous listening in background thread.

**Example:**
```python
from src.audio.continuous import ContinuousListener

def handle_transcription(transcription):
    print(f"Heard: {transcription.text}")

listener = ContinuousListener(
    model_name="openai/whisper-base",
    on_transcription=handle_transcription
)

listener.start()
# ... listener runs in background ...
listener.stop()
```

##### `stop() -> None`

Stop listening and clean up resources.

---

### AudioCapture

Low-level audio capture for single-shot recordings.

#### Methods

##### `capture_audio(duration: float = 3.0, sample_rate: int = 16000) -> np.ndarray`

Capture fixed-duration audio from microphone.

**Parameters:**
- `duration` (float): Recording duration in seconds
- `sample_rate` (int): Audio sample rate (default: 16000)

**Returns:**
- `np.ndarray`: Audio samples, shape (samples,), float32

**Example:**
```python
from src.audio.capture import capture_audio

audio = capture_audio(duration=5.0)
print(audio.shape)  # (80000,) for 5 seconds @ 16kHz
```

---

### VAD

Voice Activity Detection using Silero VAD.

#### Class Definition

```python
class VAD:
    def __init__(self, threshold: float = 0.5):
        """Initialize VAD.
        
        Args:
            threshold: Speech probability threshold (0.0-1.0)
        """
```

#### Methods

##### `is_speech(audio_chunk: np.ndarray) -> bool`

Check if audio chunk contains speech.

**Parameters:**
- `audio_chunk` (np.ndarray): Audio samples at 16kHz

**Returns:**
- `bool`: True if speech detected

**Example:**
```python
from src.audio.vad import VAD
import numpy as np

vad = VAD(threshold=0.5)
chunk = np.random.randn(4800)  # 300ms @ 16kHz
has_speech = vad.is_speech(chunk)
```

---

## Feature 002: SLM & MQTT

### CommandRouter

High-level orchestrator for voice-to-MQTT pipeline.

#### Class Definition

```python
class CommandRouter:
    def __init__(
        self,
        model_path: str,
        device_config_path: str,
        mqtt_config: MQTTConfig,
        enable_state_tracking: bool = False,
        state_ttl: int = 300
    ):
        """Initialize command router.
        
        Args:
            model_path: Path to SLM GGUF file
            device_config_path: Path to devices.yaml
            mqtt_config: MQTT broker configuration
            enable_state_tracking: Enable state awareness
            state_ttl: State time-to-live in seconds
        """
```

#### Methods

##### `connect_mqtt() -> None`

Connect to MQTT broker and subscribe to state topics.

##### `process_transcription(transcription: str) -> CommandSession`

Process voice transcription through complete pipeline.

**Parameters:**
- `transcription` (str): Voice transcription text

**Returns:**
- `CommandSession`: Session with commands, MQTT messages, errors

**Flow:**
1. Parse transcription → Command(s)
2. Check redundancy (if state tracking enabled)
3. Resolve device MQTT topics
4. Publish to MQTT broker
5. Update session tracking

**Example:**
```python
from src.command.router import CommandRouter
from src.devices.mqtt_config import MQTTConfig

mqtt_config = MQTTConfig(host="localhost", port=1883)
router = CommandRouter(
    model_path="models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf",
    device_config_path="config/devices.yaml",
    mqtt_config=mqtt_config,
    enable_state_tracking=True
)

router.connect_mqtt()

session = router.process_transcription("Turn on the living room light")
print(session.commands[0].intent)  # "turn_on"
print(session.mqtt_messages[0]['topic'])  # "home/lights/living_room/set"
```

##### `get_device_state(device_name: str) -> Optional[DeviceState]`

Get current cached state of a device.

**Parameters:**
- `device_name` (str): Device identifier

**Returns:**
- `DeviceState | None`: Current state if available and fresh

##### `cleanup() -> None`

Disconnect MQTT and clean up resources.

---

### SLMEngine

Low-level interface to Phi-4-Mini SLM for command extraction.

#### Class Definition

```python
class SLMEngine:
    def __init__(
        self,
        model_path: str,
        context_length: int = 2048,
        temperature: float = 0.1
    ):
        """Initialize SLM inference engine.
        
        Args:
            model_path: Path to GGUF model file
            context_length: Model context window
            temperature: Sampling temperature (lower = more deterministic)
        """
```

#### Methods

##### `extract_command(transcription: str, timeout: int = 30) -> List[Command]`

Extract structured commands from natural language.

**Parameters:**
- `transcription` (str): Voice transcription text
- `timeout` (int): Inference timeout in seconds

**Returns:**
- `List[Command]`: Extracted commands (may be empty)

**Raises:**
- `InferenceError`: If SLM fails
- `TimeoutError`: If inference exceeds timeout

**Example:**
```python
from src.command.slm_engine import SLMEngine

engine = SLMEngine(
    model_path="models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf"
)

commands = engine.extract_command("Turn on bedroom light and set it to 50 percent")
print(len(commands))  # 2
print(commands[0].intent)  # "turn_on"
print(commands[1].intent)  # "set_brightness"
```

---

### CommandParser

Combines SLM with device validation.

#### Class Definition

```python
class CommandParser:
    def __init__(
        self,
        model_path: str,
        device_config_path: str
    ):
        """Initialize command parser.
        
        Args:
            model_path: Path to SLM model
            device_config_path: Path to devices.yaml
        """
```

#### Methods

##### `parse(transcription: str, validate_devices: bool = True) -> List[Command]`

Parse transcription and validate devices.

**Parameters:**
- `transcription` (str): Voice transcription
- `validate_devices` (bool): Check device names against config

**Returns:**
- `List[Command]`: Validated commands

**Raises:**
- `DeviceNotFoundError`: If device not in configuration

---

### MQTTClient

Thread-safe MQTT client wrapper with QoS 1 enforcement.

#### Class Definition

```python
class MQTTClient:
    def __init__(self, config: MQTTConfig):
        """Initialize MQTT client.
        
        Args:
            config: MQTT broker configuration
        """
```

#### Methods

##### `connect() -> None`

Connect to MQTT broker with retry logic.

**Retry Policy:**
- Exponential backoff: 2s, 4s, 8s
- Max retries: 3

##### `publish_command(command: Command, topic: str) -> None`

Publish command with QoS 1 guarantee.

**Parameters:**
- `command` (Command): Command to publish
- `topic` (str): MQTT topic

**QoS 1 Behavior:**
- Waits for PUBACK confirmation
- Retries on network failure
- Timeout: 5 seconds

**Example:**
```python
from src.devices.mqtt_client import MQTTClient
from src.devices.mqtt_config import MQTTConfig
from src.command.models import Command

config = MQTTConfig(host="localhost", port=1883)
client = MQTTClient(config)
client.connect()

command = Command(
    device="living_room_light",
    intent="turn_on",
    parameters={}
)

client.publish_command(command, "home/lights/living_room/set")
```

##### `subscribe(topics: List[str]) -> None`

Subscribe to MQTT topics for state updates.

##### `disconnect() -> None`

Gracefully disconnect and flush messages.

---

### DeviceStateCache

Thread-safe cache for device states with TTL and redundancy detection.

#### Class Definition

```python
class DeviceStateCache:
    def __init__(self, default_ttl: int = 300):
        """Initialize state cache.
        
        Args:
            default_ttl: Time-to-live for states in seconds
        """
```

#### Methods

##### `update(device_id: str, state_data: Dict[str, Any]) -> None`

Update or create device state.

**Thread-Safety:** Uses RLock for concurrent access

**Example:**
```python
from src.devices.state import DeviceStateCache

cache = DeviceStateCache(default_ttl=300)
cache.update("living_room_light", {"state": "ON", "brightness": 100})
```

##### `get(device_id: str) -> Optional[DeviceState]`

Get fresh device state.

**Returns:**
- `DeviceState | None`: State if available and not stale

**Staleness:** Returns None if age > TTL

##### `is_redundant(device_id: str, intent: str, parameters: Dict) -> bool`

Check if command is redundant based on current state.

**Redundancy Rules:**
- `turn_on` when already ON
- `turn_off` when already OFF
- `set_brightness` to current brightness
- `set_temperature` to current temperature

**Parameters:**
- `device_id` (str): Device identifier
- `intent` (str): Command intent
- `parameters` (Dict): Command parameters

**Returns:**
- `bool`: True if command is redundant

**Example:**
```python
cache.update("light", {"state": "ON", "brightness": 50})

# This is redundant (already ON)
is_redundant = cache.is_redundant("light", "turn_on", {})
print(is_redundant)  # True

# This is NOT redundant (different brightness)
is_redundant = cache.is_redundant("light", "set_brightness", {"brightness": 75})
print(is_redundant)  # False
```

##### `cleanup_stale() -> int`

Remove stale state entries.

**Returns:**
- `int`: Number of states removed

---

## Data Models

### Command

```python
@dataclass
class Command:
    device: str              # Device identifier
    intent: str              # Action: turn_on, turn_off, set_brightness, etc.
    parameters: Dict[str, Any]  # Intent-specific parameters
    confidence: float = 1.0  # Extraction confidence
    
    def to_mqtt_payload(self) -> str:
        """Convert to MQTT JSON payload."""
```

### CommandSession

```python
@dataclass
class CommandSession:
    transcription: str
    commands: List[Command] = field(default_factory=list)
    mqtt_messages: List[Dict] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    @property
    def duration_ms(self) -> int:
        """Session duration in milliseconds."""
```

### DeviceState

```python
@dataclass
class DeviceState:
    device_id: str
    state: Dict[str, Any]
    last_updated: datetime
    available: bool = True
    
    def is_stale(self, ttl_seconds: int) -> bool:
        """Check if state exceeds TTL."""
    
    def is_on(self) -> Optional[bool]:
        """Check if device is ON/OFF."""
```

### Transcription

```python
@dataclass
class Transcription:
    text: str           # Transcribed text
    confidence: float   # Recognition confidence
    duration: float     # Audio duration in seconds
```

---

## Error Handling

### Custom Exceptions

```python
# Feature 001
class AudioCaptureError(Exception):
    """Audio capture failed."""

class TranscriptionError(Exception):
    """Whisper transcription failed."""

class VADError(Exception):
    """VAD operation failed."""

# Feature 002
class SLMError(Exception):
    """Base for SLM errors."""

class ModelLoadError(SLMError):
    """SLM model loading failed."""

class InferenceError(SLMError):
    """SLM inference failed."""

class TimeoutError(SLMError):
    """SLM inference timeout."""

class MQTTError(Exception):
    """Base for MQTT errors."""

class MQTTConnectionError(MQTTError):
    """MQTT connection failed."""

class MQTTPublishError(MQTTError):
    """MQTT publish failed."""

class DeviceNotFoundError(Exception):
    """Device not in configuration."""

class CommandParsingError(Exception):
    """Command parsing failed."""
```

---

## Configuration

### MQTTConfig

```python
@dataclass
class MQTTConfig:
    host: str = "localhost"
    port: int = 1883
    username: Optional[str] = None
    password: Optional[str] = None
    keepalive: int = 60
```

### DeviceConfig

Loaded from YAML:

```python
from src.devices.config import DeviceConfig

config = DeviceConfig.from_yaml("config/devices.yaml")
device = config.find_device("living_room_light")
print(device.command_topic)  # "home/lights/living_room/set"
```

---

## Best Practices

### Memory Management

```python
# Always cleanup resources
try:
    router = CommandRouter(...)
    router.connect_mqtt()
    # ... use router ...
finally:
    router.cleanup()
```

### Error Handling

```python
try:
    session = router.process_transcription(text)
except DeviceNotFoundError as e:
    print(f"Unknown device: {e}")
except MQTTPublishError as e:
    print(f"MQTT error: {e}")
except TimeoutError as e:
    print(f"SLM timeout: {e}")
```

### State Awareness

```python
# Enable for redundancy detection
router = CommandRouter(
    ...,
    enable_state_tracking=True,
    state_ttl=300  # 5 minutes
)

# Check state before manual commands
state = router.get_device_state("living_room_light")
if state and state.is_on():
    print("Light already on")
```

---

## Performance Tips

1. **Model Selection**:
   - Use `whisper-tiny` for <2s transcription
   - Use `whisper-base` for better accuracy (~3s)

2. **SLM Optimization**:
   - Q4_K_M quantization balances speed/quality
   - Reduce context_length for faster inference
   - Lower temperature for deterministic results

3. **MQTT**:
   - QoS 1 ensures delivery but adds latency
   - Use QoS 0 for non-critical messages

4. **State Caching**:
   - Enable only if redundancy detection needed
   - Adjust TTL based on device update frequency
   - Call `cleanup_stale()` periodically

---

## Version History

- **v2.0.0** (2025-12-12): Added Feature 002 (SLM & MQTT)
- **v1.0.0** (2025-12-01): Initial release (Feature 001)
