# Research: SLM Command Processing and MQTT Integration

**Feature**: 002-slm-mqtt-integration  
**Date**: 2025-12-11  
**Phase**: 0 - Outline & Research

## Research Questions

This document resolves technical unknowns identified in the Technical Context and specification requirements.

---

## 1. Phi-4-Mini-GGUF Model Integration

**Question**: How do we integrate and run the Phi-4-Mini-GGUF model locally for command intent extraction?

### Decision: Use llama-cpp-python with Structured Prompting

**Rationale**:
- `llama-cpp-python` is the de facto standard for running GGUF models locally in Python
- Provides both CPU and GPU acceleration (via cuBLAS, Metal, OpenCL)
- Low memory overhead compared to transformers (suitable for running alongside Whisper)
- Supports prompt caching for faster repeated inferences
- Active community and well-documented

**Implementation Approach**:

```python
from llama_cpp import Llama

# Model initialization (once at startup)
llm = Llama(
    model_path="models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf",
    n_ctx=2048,        # Context window
    n_threads=4,       # CPU threads
    n_gpu_layers=0,    # 0 for CPU-only, >0 for GPU acceleration
    verbose=False
)

# Prompt template for command extraction
COMMAND_PROMPT = """You are a home automation assistant. Extract the command intent and parameters from the user's speech.

Output format (JSON):
{
  "intent": "turn_on|turn_off|set_brightness|set_temperature|unknown",
  "device": "device_identifier",
  "parameters": {"brightness": 50, "color": "warm_white"}
}

User said: "{transcription}"

Extract command:"""

# Inference with timeout
response = llm.create_completion(
    COMMAND_PROMPT.format(transcription=user_text),
    max_tokens=150,
    temperature=0.1,  # Low temperature for deterministic parsing
    stop=["User said:", "\n\n"]
)
```

**Model Selection**:
- **Phi-4-Mini Q4_K_M quantization**: Best balance of speed, accuracy, and memory (~2GB)
- Smaller than full Phi-4 (~7GB) but sufficient for command parsing
- Q4 quantization maintains 95%+ accuracy for structured tasks

**Download**: Hugging Face - `microsoft/Phi-4-Mini-GGUF` repository

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Full Phi-4 via transformers | Memory overhead too high (7GB+), slower inference, not GGUF optimized |
| OpenAI API | Violates local-only requirement (FR-003, FR-004), introduces cloud dependency |
| spaCy NER | Insufficient for natural language intent extraction, requires custom training |
| Regex patterns | Too brittle, won't handle natural language variations ("turn the light on" vs "light on please") |

---

## 2. Prompt Engineering for Command Extraction

**Question**: What prompt structure ensures reliable intent and parameter extraction from transcribed text?

### Decision: Few-Shot JSON Prompting with Strict Output Format

**Rationale**:
- Small Language Models respond well to structured output formats
- JSON output is easily parseable and validates against schema
- Few-shot examples improve accuracy for ambiguous commands
- Low temperature (0.1-0.2) ensures deterministic, consistent outputs

**Prompt Template**:

```python
SYSTEM_PROMPT = """You are a home automation command parser. Extract intent and parameters from user speech.

Examples:
User: "turn on the living room light"
Output: {"intent": "turn_on", "device": "living_room_light", "parameters": {}}

User: "set bedroom light to 50 percent"
Output: {"intent": "set_brightness", "device": "bedroom_light", "parameters": {"brightness": 50}}

User: "what's the weather"
Output: {"intent": "unknown", "device": null, "parameters": {}, "reason": "not a device command"}

Rules:
- intent: turn_on, turn_off, set_brightness, set_temperature, unknown
- device: normalize to snake_case (e.g., "living room" → "living_room_light")
- parameters: include only values mentioned by user
- If unclear, set intent to "unknown" with reason

User: "{transcription}"
Output:"""
```

**Validation Strategy**:
- Parse JSON response, catch `json.JSONDecodeError`
- Validate intent against known enum values
- Verify device exists in configuration
- If parsing fails, retry once with temperature=0 (more deterministic)
- After 2 failures, return `{"intent": "unknown", "reason": "parse_error"}`

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Free-form text output | Requires complex NLP parsing, error-prone, not deterministic |
| Multi-step prompts (CoT) | Slower inference, overkill for simple command extraction |
| Fine-tuning Phi-4 | Unnecessary complexity, pretrained model sufficient for structured tasks |

---

## 3. MQTT Client Integration Patterns

**Question**: How do we implement reliable MQTT publishing and state subscription with error handling?

### Decision: paho-mqtt with Connection Pooling and Retry Logic

**Rationale**:
- `paho-mqtt` is the official Eclipse MQTT client library (mature, stable)
- Supports QoS levels 0, 1, 2 as specified (FR-020: QoS 1)
- Built-in reconnection logic and keepalive handling
- Callback-based design fits event-driven state updates
- Well-documented and widely used in IoT projects

**Implementation Pattern**:

```python
import paho.mqtt.client as mqtt
import time
from threading import Lock

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883, qos=1):
        self.client = mqtt.Client(client_id="home_automation_assistant")
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.qos = qos
        self.connected = False
        self.lock = Lock()
        
    def connect(self, timeout=30):
        """Connect with retry logic"""
        attempts = 0
        max_attempts = 3
        
        while attempts < max_attempts:
            try:
                self.client.connect(self.broker_host, self.broker_port, keepalive=60)
                self.client.loop_start()  # Non-blocking background thread
                
                # Wait for connection confirmation
                start = time.time()
                while not self.connected and (time.time() - start) < timeout:
                    time.sleep(0.1)
                    
                if self.connected:
                    return True
                    
            except Exception as e:
                attempts += 1
                logger.warning(f"MQTT connection attempt {attempts} failed: {e}")
                time.sleep(2 ** attempts)  # Exponential backoff
                
        return False
    
    def publish_command(self, topic, payload, retain=False):
        """Publish with QoS 1 and confirmation"""
        if not self.connected:
            raise ConnectionError("MQTT broker not connected")
            
        with self.lock:
            result = self.client.publish(
                topic, 
                payload=json.dumps(payload),
                qos=self.qos,
                retain=retain
            )
            
            # Wait for publish confirmation (QoS 1)
            result.wait_for_publish(timeout=5.0)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise PublishError(f"MQTT publish failed: {mqtt.error_string(result.rc)}")
                
    def subscribe_state_topics(self, topics):
        """Subscribe to device state updates"""
        for topic in topics:
            self.client.subscribe(topic, qos=self.qos)
            logger.info(f"Subscribed to {topic}")
    
    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logger.info("MQTT connected")
        else:
            logger.error(f"MQTT connection failed: {mqtt.connack_string(rc)}")
    
    def _on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnect: {mqtt.error_string(rc)}")
            # Auto-reconnect handled by paho-mqtt internally
    
    def _on_message(self, client, userdata, msg):
        """Handle incoming state updates"""
        try:
            payload = json.loads(msg.payload.decode())
            self._update_device_state(msg.topic, payload)
        except Exception as e:
            logger.error(f"Failed to process MQTT message: {e}")
```

**Connection Lifecycle**:
1. **Startup**: Connect to broker, subscribe to state topics (`home/+/state`)
2. **Command**: Publish command, wait for QoS 1 acknowledgment
3. **State Update**: Receive state messages via callback, update cache
4. **Disconnect**: Graceful shutdown with `loop_stop()` and `disconnect()`

**Error Handling**:
- Connection failures: Retry with exponential backoff (2, 4, 8 seconds)
- Publish failures: Log error, notify user, don't retry automatically (command might be stale)
- Message parsing errors: Log and skip (don't crash)
- Automatic reconnection: Enabled by default in paho-mqtt

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| asyncio-mqtt | Adds async complexity, overkill for simple pub/sub pattern |
| Manual TCP sockets | Reinventing the wheel, error-prone, no QoS support |
| MQTT 5.0 only | Spec allows 3.1.1 or 5.0, better compatibility with 3.1.1 |

---

## 4. Device Configuration Management

**Question**: How do we map natural language device names to MQTT topics?

### Decision: YAML Configuration with Schema Validation

**Rationale**:
- YAML is human-readable and easy to edit
- Supports structured data (nested device types, capabilities)
- Python `PyYAML` library is standard and well-supported
- Can include comments for documentation
- JSON schema validation ensures correctness

**Configuration Format** (`config/devices.yaml`):

```yaml
# Device Mappings for Home Automation Assistant
# Each device maps natural language names to MQTT topics

devices:
  lights:
    - name: living_room_light
      aliases: ["living room light", "lounge light", "main light"]
      mqtt:
        command_topic: "home/light/living_room/set"
        state_topic: "home/light/living_room/state"
      capabilities:
        - on_off
        - brightness
        - color_temp
      
    - name: bedroom_light
      aliases: ["bedroom light", "bed light"]
      mqtt:
        command_topic: "home/light/bedroom/set"
        state_topic: "home/light/bedroom/state"
      capabilities:
        - on_off
        - brightness
  
  switches:
    - name: fan
      aliases: ["ceiling fan", "bedroom fan"]
      mqtt:
        command_topic: "home/switch/fan/set"
        state_topic: "home/switch/fan/state"
      capabilities:
        - on_off
  
  thermostats:
    - name: living_room_thermostat
      aliases: ["thermostat", "ac", "air conditioner"]
      mqtt:
        command_topic: "home/climate/living_room/set"
        state_topic: "home/climate/living_room/state"
      capabilities:
        - temperature
        - mode

# MQTT Broker Configuration (optional override)
mqtt_broker:
  host: localhost
  port: 1883
  username: null  # Set via environment variable MQTT_USERNAME
  password: null  # Set via environment variable MQTT_PASSWORD
```

**Loading and Validation**:

```python
import yaml
from typing import Dict, List
from dataclasses import dataclass

@dataclass
class DeviceMapping:
    name: str
    aliases: List[str]
    command_topic: str
    state_topic: str
    capabilities: List[str]
    device_type: str  # light, switch, thermostat

def load_device_config(config_path: str) -> Dict[str, DeviceMapping]:
    """Load and validate device configuration"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    
    devices = {}
    for device_type, device_list in config['devices'].items():
        for device in device_list:
            mapping = DeviceMapping(
                name=device['name'],
                aliases=device['aliases'],
                command_topic=device['mqtt']['command_topic'],
                state_topic=device['mqtt']['state_topic'],
                capabilities=device['capabilities'],
                device_type=device_type
            )
            
            # Index by name and all aliases for fast lookup
            devices[mapping.name] = mapping
            for alias in mapping.aliases:
                devices[alias.lower()] = mapping
    
    return devices

def resolve_device(user_input: str, devices: Dict) -> DeviceMapping:
    """Resolve user's natural language device reference"""
    normalized = user_input.lower().strip()
    return devices.get(normalized)
```

**Validation Rules**:
- Device names must be unique
- MQTT topics must follow pattern: `home/{type}/{location}/{action}`
- Capabilities must be in allowed set: `on_off`, `brightness`, `color_temp`, `temperature`, `mode`
- At least one alias must be provided per device

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| JSON configuration | Less readable, no comments, harder to edit manually |
| Python config file | Security risk (code execution), harder to parse programmatically |
| Database (SQLite) | Overkill for static configuration, adds dependency |
| Hardcoded mappings | Not configurable, requires code changes for new devices |

---

## 5. State Management and Caching

**Question**: How do we track device states to enable context-aware responses?

### Decision: In-Memory Cache with TTL (Time-To-Live)

**Rationale**:
- Simple dict-based cache sufficient for 50 devices
- TTL prevents stale state (default: 5 minutes)
- Atomic updates via threading.Lock for thread safety
- No persistence needed (repopulated on startup from MQTT state queries)
- Low latency lookups for command processing

**Implementation**:

```python
from dataclasses import dataclass
from datetime import datetime, timedelta
from threading import Lock
from typing import Optional, Dict, Any

@dataclass
class DeviceState:
    device_id: str
    state: Dict[str, Any]  # {"state": "ON", "brightness": 75}
    last_updated: datetime
    available: bool = True

class StateCache:
    def __init__(self, ttl_seconds=300):
        self.cache: Dict[str, DeviceState] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = Lock()
    
    def update(self, device_id: str, state: Dict[str, Any]):
        """Update device state from MQTT message"""
        with self.lock:
            self.cache[device_id] = DeviceState(
                device_id=device_id,
                state=state,
                last_updated=datetime.now(),
                available=True
            )
    
    def get(self, device_id: str) -> Optional[DeviceState]:
        """Get device state if not stale"""
        with self.lock:
            device_state = self.cache.get(device_id)
            
            if device_state is None:
                return None
            
            # Check TTL
            age = datetime.now() - device_state.last_updated
            if age > self.ttl:
                device_state.available = False
                return device_state  # Return but mark as potentially stale
            
            return device_state
    
    def mark_unavailable(self, device_id: str):
        """Mark device as offline (e.g., from LWT message)"""
        with self.lock:
            if device_id in self.cache:
                self.cache[device_id].available = False
    
    def is_on(self, device_id: str) -> Optional[bool]:
        """Check if device is currently on"""
        state = self.get(device_id)
        if state and state.available:
            return state.state.get('state') == 'ON'
        return None  # Unknown state
```

**State Query on Startup**:
```python
# Subscribe to state topics
mqtt_client.subscribe_state_topics([
    "home/light/+/state",
    "home/switch/+/state",
    "home/climate/+/state"
])

# Request current states (if devices support it)
for device in devices.values():
    mqtt_client.publish_command(
        device.command_topic + "/get",
        {}
    )
```

**User Story 3 Integration** (Device State Awareness):
```python
def process_command(transcription: str, state_cache: StateCache):
    command = extract_command(transcription)
    
    if command.intent == "turn_on":
        current_state = state_cache.is_on(command.device)
        
        if current_state is True:
            return f"The {command.device} is already on"
        elif current_state is False:
            # Proceed with command
            mqtt_client.publish_command(...)
            return f"Turning on the {command.device}"
        else:
            # Unknown state, send command anyway but warn
            mqtt_client.publish_command(...)
            return f"Turning on the {command.device} (state unknown)"
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Persistent storage (Redis/file) | Overkill, state repopulated quickly from MQTT, adds dependency |
| No caching (always query) | MQTT doesn't support synchronous queries, would need request/response pattern |
| Infinite TTL | Risk of stale data if device goes offline without LWT message |

---

## 6. Error Handling and User Feedback

**Question**: How do we handle errors gracefully and provide clear user feedback?

### Decision: Structured Exception Hierarchy with Feedback Messages

**Rationale**:
- Custom exceptions provide clear error categorization
- Each exception maps to user-friendly feedback message
- Logging at appropriate levels (ERROR for failures, WARNING for retries, INFO for success)
- Non-blocking error handling (don't crash on single command failure)

**Exception Hierarchy**:

```python
class CommandProcessingError(Exception):
    """Base exception for command processing"""
    def user_message(self) -> str:
        return "I encountered an error processing your command"

class SLMError(CommandProcessingError):
    """SLM model inference failed"""
    def user_message(self) -> str:
        return "I couldn't understand that command. Please try again"

class DeviceNotFoundError(CommandProcessingError):
    """Device not in configuration"""
    def __init__(self, device_name: str):
        self.device_name = device_name
    
    def user_message(self) -> str:
        return f"I don't recognize a device called '{self.device_name}'"

class MQTTPublishError(CommandProcessingError):
    """Failed to publish MQTT message"""
    def __init__(self, device_name: str, reason: str):
        self.device_name = device_name
        self.reason = reason
    
    def user_message(self) -> str:
        return f"Could not reach the {self.device_name}. {self.reason}"

class MQTTConnectionError(CommandProcessingError):
    """MQTT broker not reachable"""
    def user_message(self) -> str:
        return "Home automation system is offline. Please check the connection"
```

**Error Handling Flow**:

```python
def handle_voice_command(transcription: str):
    try:
        # Phase 1: Extract command with SLM
        command = slm_parser.extract_command(transcription, timeout=10)
        
        if command.intent == "unknown":
            logger.info(f"Unknown intent: {command.reason}")
            return speak(command.reason or "I didn't understand that")
        
        # Phase 2: Validate device exists
        device = device_registry.get(command.device)
        if device is None:
            raise DeviceNotFoundError(command.device)
        
        # Phase 3: Check state (optional, User Story 3)
        if state_cache.is_on(device.name) and command.intent == "turn_on":
            return speak(f"The {device.name} is already on")
        
        # Phase 4: Publish to MQTT
        mqtt_client.publish_command(
            device.command_topic,
            command.to_mqtt_payload()
        )
        
        logger.info(f"Command executed: {command.intent} on {device.name}")
        return speak(f"{device.name.replace('_', ' ').title()} {command.intent.replace('_', ' ')}")
        
    except SLMError as e:
        logger.error(f"SLM failed: {e}")
        return speak(e.user_message())
    
    except DeviceNotFoundError as e:
        logger.warning(f"Device not found: {e.device_name}")
        return speak(e.user_message())
    
    except MQTTPublishError as e:
        logger.error(f"MQTT publish failed: {e}")
        return speak(e.user_message())
    
    except MQTTConnectionError as e:
        logger.error(f"MQTT connection error: {e}")
        return speak(e.user_message())
    
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        return speak("Something went wrong. Please try again")
```

**Logging Standards**:
- **INFO**: Successful commands, state updates
- **WARNING**: Recoverable errors (device not found, unknown intent)
- **ERROR**: Failures that prevent command execution (MQTT publish, SLM timeout)
- **CRITICAL**: System-level failures (model won't load, broker permanently unreachable)

**Privacy-Aware Logging**:
```python
# GOOD: Log metadata only
logger.info(f"Command: intent={command.intent}, device={device.name}, latency={latency}ms")

# BAD: Do not log full transcription (privacy violation per FR-014)
# logger.info(f"User said: {transcription}")  ❌
```

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| HTTP-style error codes | Less pythonic, harder to handle specific cases |
| Global error handler only | Loses context, harder to provide specific feedback |
| Silent failures | Poor UX, user doesn't know if command worked |

---

## 7. Performance Optimization

**Question**: How do we meet the <3s latency requirement with two large models loaded?

### Decision: Model Preloading + Async Pipeline + Prompt Caching

**Optimization Strategies**:

1. **Model Preloading at Startup**:
   - Load both Whisper and Phi-4-Mini during initialization (~20s total)
   - Amortize cost across all commands (user pays once at startup)

2. **Prompt Caching**:
   - Phi-4-Mini system prompt remains constant
   - llama-cpp-python caches KV pairs for repeated prompt prefixes
   - Reduces inference time by ~30-40%

3. **Low Latency Settings**:
   ```python
   # Phi-4-Mini config for speed
   llm = Llama(
       model_path="...",
       n_ctx=2048,          # Sufficient for command extraction
       n_batch=512,         # Batch size for processing
       n_threads=4,         # Parallel CPU threads
       use_mlock=True,      # Keep model in RAM (no swapping)
       low_vram=True,       # Optimize for memory
   )
   
   # Inference config
   response = llm.create_completion(
       prompt,
       max_tokens=150,      # Short responses sufficient
       temperature=0.1,     # Deterministic = faster
       top_p=0.9,
       stop=["\n\n"],       # Early stopping
   )
   ```

4. **Timeout Enforcement**:
   ```python
   import signal
   
   def timeout_handler(signum, frame):
       raise TimeoutError("SLM inference timed out")
   
   signal.signal(signal.SIGALRM, timeout_handler)
   signal.alarm(10)  # 10 second timeout (FR-019)
   
   try:
       response = llm.create_completion(...)
   finally:
       signal.alarm(0)  # Cancel alarm
   ```

5. **Pipeline Parallelization**:
   - Transcription (Feature 001) runs independently
   - Once text available, immediately start SLM inference
   - MQTT publish is fast (<100ms with QoS 1)

**Latency Breakdown** (Target: <3s):
- Transcription (Whisper): ~1.5s (Feature 001, already optimized)
- SLM Inference (Phi-4-Mini): ~0.8s (with caching)
- Device lookup + validation: ~0.05s
- MQTT publish + confirm: ~0.1s
- **Total**: ~2.45s ✅ (within 3s target)

### Alternatives Considered

| Alternative | Rejected Because |
|-------------|------------------|
| Separate processes | IPC overhead, complexity |
| Quantized to Q2/Q3 | Accuracy degrades below Q4, not worth speed gain |
| Skip Whisper transcription | Already implemented in Feature 001, can't change |
| Cloud API for SLM | Violates local-only requirement |

---

## Summary of Decisions

| Research Area | Decision | Key Technology |
|---------------|----------|----------------|
| SLM Integration | llama-cpp-python with Phi-4-Mini Q4_K_M | llama-cpp-python |
| Prompt Engineering | Few-shot JSON prompting, low temperature | Structured prompts |
| MQTT Client | paho-mqtt with QoS 1, retry logic | paho-mqtt |
| Device Configuration | YAML with schema validation | PyYAML |
| State Management | In-memory cache with 5-min TTL | Dict + threading.Lock |
| Error Handling | Custom exception hierarchy | Python exceptions |
| Performance | Model preloading, prompt caching, timeouts | llama-cpp optimization |

All decisions align with constitution principles: local-only processing, privacy-first, simplicity, and observability.

---

**Status**: ✅ Research Complete - Ready for Phase 1 (Design)
