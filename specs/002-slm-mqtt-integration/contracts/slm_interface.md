# Contract: SLM Engine Interface

**Feature**: 002-slm-mqtt-integration  
**Component**: `src/command/slm_engine.py`  
**Purpose**: Phi-4-Mini-GGUF model integration for command intent extraction

## Interface

### `class SLMEngine`

Manages the Phi-4-Mini-GGUF model lifecycle and provides intent extraction from transcribed text.

#### Initialization

```python
def __init__(
    self,
    model_path: str,
    n_ctx: int = 2048,
    n_threads: int = 4,
    n_gpu_layers: int = 0,
    temperature: float = 0.1,
    timeout_seconds: int = 10
):
    """
    Initialize the SLM engine with Phi-4-Mini-GGUF model.
    
    Args:
        model_path: Path to the .gguf model file
        n_ctx: Context window size (default: 2048)
        n_threads: Number of CPU threads (default: 4)
        n_gpu_layers: Number of layers to offload to GPU (default: 0 for CPU-only)
        temperature: Sampling temperature (default: 0.1 for deterministic)
        timeout_seconds: Maximum inference time (default: 10, per FR-019)
    
    Raises:
        FileNotFoundError: If model_path doesn't exist
        ModelLoadError: If model fails to load
    """
```

#### Core Methods

```python
def extract_command(self, transcription: str, timeout: Optional[int] = None) -> Command:
    """
    Extract command intent and parameters from transcribed text.
    
    Args:
        transcription: Text from speech-to-text system
        timeout: Override default timeout for this inference
    
    Returns:
        Command object with intent, device, parameters, and confidence
    
    Raises:
        SLMError: If inference fails or times out
        ValueError: If transcription is empty
    
    Example:
        >>> engine = SLMEngine("models/phi-4-mini-q4.gguf")
        >>> cmd = engine.extract_command("turn on the living room light")
        >>> assert cmd.intent == "turn_on"
        >>> assert cmd.device == "living_room_light"
    """

def is_loaded(self) -> bool:
    """
    Check if model is loaded and ready for inference.
    
    Returns:
        True if model is loaded, False otherwise
    """

def unload(self):
    """
    Unload model from memory and cleanup resources.
    Should be called during graceful shutdown.
    """
```

## Input/Output Contracts

### Input: `extract_command(transcription: str)`

**Preconditions**:
- `transcription` must be non-empty string
- Model must be loaded (`is_loaded() == True`)
- Transcription should be clean text from speech-to-text (no audio data)

**Valid Input Examples**:
```python
"turn on the living room light"
"set bedroom light to 50 percent"
"turn off all lights"
"what's the weather"  # Unknown intent
```

**Invalid Input Examples**:
```python
""  # Empty string → ValueError
None  # None type → TypeError
"<binary audio data>"  # Binary data → ValueError
```

### Output: `Command` object

**Structure**:
```python
@dataclass
class Command:
    intent: str          # One of: turn_on, turn_off, set_brightness, set_temperature, set_color, unknown
    device: str          # Device identifier (snake_case, e.g., "living_room_light")
    parameters: Dict[str, Any]  # Optional parameters (brightness, temperature, color, etc.)
    confidence: float    # 0.0-1.0 confidence score
    timestamp: datetime  # UTC timestamp of extraction
```

**Postconditions**:
- `intent` is one of the allowed values
- `device` is normalized to snake_case
- `confidence` is between 0.0 and 1.0
- `parameters` contains only valid keys for the intent type
- If intent is `unknown`, device may be None and `parameters` may contain `reason` key

**Example Outputs**:

```python
# Success case: Clear command
Command(
    intent="turn_on",
    device="living_room_light",
    parameters={},
    confidence=0.95,
    timestamp=datetime(2025, 12, 11, 10, 30, 0)
)

# Success case: Command with parameters
Command(
    intent="set_brightness",
    device="bedroom_light",
    parameters={"brightness": 50},
    confidence=0.88,
    timestamp=datetime(2025, 12, 11, 10, 30, 5)
)

# Unknown intent
Command(
    intent="unknown",
    device=None,
    parameters={"reason": "not a device command"},
    confidence=0.32,
    timestamp=datetime(2025, 12, 11, 10, 30, 10)
)
```

## Error Handling

### `SLMError`
**When**: Model inference fails, times out, or returns invalid response  
**User Message**: "I couldn't understand that command. Please try again"  
**Recovery**: Log error, return Command with intent="unknown"

### `TimeoutError`
**When**: Inference exceeds timeout_seconds (FR-019)  
**User Message**: "That took too long to process. Please try again"  
**Recovery**: Cancel inference, raise SLMError

### `ModelLoadError`
**When**: Model file not found or fails to load during __init__  
**User Message**: "Command processing is unavailable"  
**Recovery**: Application should fail to start (critical error)

## Performance Requirements

- **Model Load Time**: <15 seconds (SC-007)
- **Inference Latency**: <1 second for typical commands (<20 words)
- **Timeout**: 10 seconds maximum (FR-019)
- **Memory**: <2GB additional RAM for Q4_K_M model
- **Throughput**: Handle 50+ consecutive inferences without degradation (SC-006)

## Prompt Template

The SLM uses a structured prompt for deterministic JSON output:

```
You are a home automation command parser. Extract intent and parameters from user speech.

Examples:
User: "turn on the living room light"
Output: {"intent": "turn_on", "device": "living_room_light", "parameters": {}}

User: "set bedroom light to 50 percent"
Output: {"intent": "set_brightness", "device": "bedroom_light", "parameters": {"brightness": 50}}

User: "what's the weather"
Output: {"intent": "unknown", "device": null, "parameters": {}, "reason": "not a device command"}

Rules:
- intent: turn_on, turn_off, set_brightness, set_temperature, set_color, unknown
- device: normalize to snake_case (e.g., "living room" → "living_room_light")
- parameters: include only values mentioned by user
- If unclear, set intent to "unknown" with reason

User: "{transcription}"
Output:
```

**Response Parsing**:
- Extract JSON from SLM response
- Validate against schema
- If parsing fails, retry once with temperature=0
- After 2 failures, return intent="unknown"

## Testing Requirements

### Contract Tests (`tests/contract/test_slm_engine_contract.py`)

1. **Model Loading**: Verify model loads successfully
2. **Basic Inference**: Test with "turn on the light" → valid Command
3. **Timeout Enforcement**: Test with max_tokens=10000 → TimeoutError within 10s
4. **Empty Input**: Test with "" → ValueError
5. **Unknown Intent**: Test with "what's the weather" → intent="unknown"

### Unit Tests (`tests/unit/test_slm_engine.py`)

1. **Prompt Construction**: Verify prompt template formatting
2. **JSON Parsing**: Test response parsing with valid/invalid JSON
3. **Device Normalization**: Test "Living Room" → "living_room_light"
4. **Parameter Extraction**: Test "50 percent" → {"brightness": 50}
5. **Confidence Scoring**: Verify confidence calculation

### Integration Tests (`tests/integration/test_text_to_command_pipeline.py`)

1. **End-to-End**: Transcription → SLM → Command → validation
2. **Multiple Commands**: Process 10 commands in sequence
3. **Error Recovery**: SLM failure → graceful degradation

## Dependencies

- `llama-cpp-python>=0.2.0`: GGUF model inference
- `dataclasses`: Command data structure (stdlib)
- `datetime`: Timestamps (stdlib)
- `json`: Response parsing (stdlib)
- `signal`: Timeout enforcement (stdlib)

## Thread Safety

- **Model Inference**: NOT thread-safe (use locking if concurrent access needed)
- **Model Loading**: Thread-safe (one-time operation at startup)
- **Recommendation**: Single SLMEngine instance, serialize command extraction

## Configuration

Environment variables and config file settings:

```yaml
# config/slm.yaml
model:
  path: "models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf"
  context_size: 2048
  threads: 4
  gpu_layers: 0  # Set to 32 for GPU acceleration
  
inference:
  temperature: 0.1
  max_tokens: 150
  timeout_seconds: 10
  
prompting:
  system_prompt_path: "config/prompts/command_extraction.txt"
```

## Privacy Compliance

- **No Logging of Transcriptions**: Never log `transcription` parameter (FR-014)
- **Metadata Only**: Log only intent, device, confidence, duration
- **No Model Telemetry**: Disable llama-cpp-python telemetry/logging

```python
# GOOD: Privacy-safe logging
logger.info(f"Command extracted: intent={cmd.intent}, device={cmd.device}, confidence={cmd.confidence:.2f}")

# BAD: Privacy violation
# logger.info(f"User said: {transcription}")  ❌
```

---

**Contract Status**: ✅ Complete  
**Implements**: FR-002, FR-003, FR-004, FR-019  
**Success Criteria**: SC-002, SC-007
