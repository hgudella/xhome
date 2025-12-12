# Contract: Command Router Interface

**Feature**: 002-slm-mqtt-integration  
**Component**: `src/command/parser.py`  
**Purpose**: Orchestrate command extraction, validation, and MQTT publishing pipeline

## Interface

### `class CommandRouter`

Coordinates the full command processing pipeline from transcription to MQTT publication.

#### Initialization

```python
def __init__(
    self,
    slm_engine: SLMEngine,
    mqtt_client: MQTTClient,
    device_registry: DeviceRegistry,
    state_cache: StateCache,
    enable_state_awareness: bool = True
):
    """
    Initialize command router with dependencies.
    
    Args:
        slm_engine: SLM model for intent extraction
        mqtt_client: MQTT client for publishing commands
        device_registry: Device configuration lookup
        state_cache: Current device state tracking
        enable_state_awareness: Enable User Story 3 (state-aware responses)
    """
```

#### Core Methods

```python
def process_command(self, transcription: str) -> CommandResult:
    """
    Process a voice transcription through the full command pipeline.
    
    Pipeline Stages:
        1. Extract command using SLM (User Story 1)
        2. Validate device exists in configuration
        3. Check current device state if enabled (User Story 3)
        4. Publish MQTT message (User Story 2)
        5. Return result with user feedback (User Story 4)
    
    Args:
        transcription: Text from speech-to-text system (Feature 001)
    
    Returns:
        CommandResult with status, feedback message, and session details
    
    Raises:
        ValueError: If transcription is empty
    
    Example:
        >>> router = CommandRouter(slm, mqtt, devices, cache)
        >>> result = router.process_command("turn on the living room light")
        >>> print(result.feedback)
        "Living room light turned on"
    """

def process_batch(self, transcriptions: List[str]) -> List[CommandResult]:
    """
    Process multiple commands in sequence (supports FR-018).
    
    Args:
        transcriptions: List of text transcriptions to process
    
    Returns:
        List of CommandResult objects, one per transcription
    
    Note: Processes sequentially, not concurrently (SLM not thread-safe)
    """

def get_device_state(self, device_name: str) -> Optional[Dict[str, Any]]:
    """
    Query current state of a device.
    
    Args:
        device_name: Device identifier (from configuration)
    
    Returns:
        Device state dictionary if available, None if unknown
    
    Example:
        >>> state = router.get_device_state("living_room_light")
        >>> print(state)
        {"state": "ON", "brightness": 75}
    """
```

## Data Structures

### `CommandResult`

Encapsulates the outcome of command processing for user feedback.

```python
@dataclass
class CommandResult:
    """Result of processing a single voice command."""
    
    status: str  # "success", "failed", "unknown_intent", "already_done"
    feedback: str  # User-friendly message to speak/display
    session: CommandSession  # Full session details for logging
    intent: Optional[str] = None  # Extracted intent (if successful)
    device: Optional[str] = None  # Target device (if identified)
    error: Optional[str] = None  # Error message (if failed)
    
    @property
    def success(self) -> bool:
        """Check if command completed successfully."""
        return self.status == "success"
    
    def to_log_entry(self) -> Dict[str, Any]:
        """Create privacy-safe log entry (no PII)."""
        return {
            "status": self.status,
            "intent": self.intent,
            "device": self.device,
            "duration_ms": self.session.duration_ms,
            "error": self.error
        }
```

## Processing Pipeline

### Pipeline Flow

```
[Transcription Input]
        ↓
┌───────────────────┐
│ 1. Extract Intent │ → SLMEngine.extract_command()
└───────────────────┘
        ↓
   ┌─────────┐
   │ Unknown?│ → Yes → Return "I didn't understand"
   └─────────┘
        ↓ No
┌───────────────────┐
│ 2. Validate Device│ → DeviceRegistry.get()
└───────────────────┘
        ↓
   ┌─────────┐
   │ Exists? │ → No → Return "I don't recognize that device"
   └─────────┘
        ↓ Yes
┌───────────────────┐
│ 3. Check State    │ → StateCache.is_on() [Optional, User Story 3]
└───────────────────┘
        ↓
   ┌──────────────┐
   │ Already Done?│ → Yes → Return "Already on/off"
   └──────────────┘
        ↓ No
┌───────────────────┐
│ 4. Publish MQTT   │ → MQTTClient.publish_command()
└───────────────────┘
        ↓
   ┌─────────┐
   │Success? │ → No → Return "Could not reach device"
   └─────────┘
        ↓ Yes
┌───────────────────┐
│ 5. Generate       │
│    Feedback       │ → Return "Device turned on"
└───────────────────┘
```

### State Awareness Logic (User Story 3)

```python
def _check_state_awareness(
    self, 
    command: Command, 
    device: DeviceMapping
) -> Optional[str]:
    """
    Check if command is redundant based on current device state.
    
    Returns:
        Feedback message if redundant, None if should proceed
    
    Examples:
        - Command: turn_on, State: ON → "The light is already on"
        - Command: turn_off, State: OFF → "The light is already off"
        - Command: turn_on, State: OFF → None (proceed)
        - Command: turn_on, State: unknown → None (proceed anyway)
    """
    if not self.enable_state_awareness:
        return None
    
    current_state = self.state_cache.get(device.name)
    
    if current_state is None or not current_state.is_fresh():
        return None  # Unknown state, proceed with command
    
    is_on = current_state.is_on()
    
    if command.intent == "turn_on" and is_on:
        return f"The {device.name.replace('_', ' ')} is already on"
    
    if command.intent == "turn_off" and not is_on:
        return f"The {device.name.replace('_', ' ')} is already off"
    
    return None  # Not redundant, proceed
```

## Error Handling

### Error Categories and Responses

| Error Type | Status | User Feedback | Example |
|------------|--------|---------------|---------|
| Unknown Intent | `unknown_intent` | "I didn't understand that command" | "what's the weather" |
| Device Not Found | `failed` | "I don't recognize a device called {name}" | "turn on the garage" (not configured) |
| State Check (Already Done) | `already_done` | "The {device} is already {state}" | "turn on" when already on |
| MQTT Publish Failed | `failed` | "Could not reach the {device}. {reason}" | Broker offline |
| SLM Timeout | `failed` | "That took too long to process" | SLM hangs |
| Unexpected Error | `failed` | "Something went wrong. Please try again" | Any uncaught exception |

### Exception Handling

```python
def process_command(self, transcription: str) -> CommandResult:
    session = CommandSession()
    session.transcribed_text = transcription
    
    try:
        # Stage 1: Extract Intent
        command = self.slm_engine.extract_command(transcription)
        session.command = command
        
        if command.intent == "unknown":
            session.complete("unknown_intent", command.parameters.get("reason"))
            return CommandResult(
                status="unknown_intent",
                feedback=f"I didn't understand that. {command.parameters.get('reason', '')}",
                session=session
            )
        
        # Stage 2: Validate Device
        device = self.device_registry.get(command.device)
        if device is None:
            raise DeviceNotFoundError(command.device)
        
        # Stage 3: Check State (Optional)
        redundant_msg = self._check_state_awareness(command, device)
        if redundant_msg:
            session.complete("already_done")
            return CommandResult(
                status="already_done",
                feedback=redundant_msg,
                session=session,
                intent=command.intent,
                device=device.name
            )
        
        # Stage 4: Publish MQTT
        mqtt_message = MQTTMessage.from_command(command, device)
        session.mqtt_message = mqtt_message
        
        self.mqtt_client.publish_command(
            mqtt_message.topic,
            mqtt_message.payload
        )
        
        # Stage 5: Success Feedback
        session.complete("success")
        feedback = self._generate_feedback(command, device)
        
        return CommandResult(
            status="success",
            feedback=feedback,
            session=session,
            intent=command.intent,
            device=device.name
        )
        
    except DeviceNotFoundError as e:
        session.complete("failed", str(e))
        return CommandResult(
            status="failed",
            feedback=e.user_message(),
            session=session,
            error=str(e)
        )
    
    except (MQTTPublishError, MQTTConnectionError) as e:
        session.complete("failed", str(e))
        return CommandResult(
            status="failed",
            feedback=e.user_message(),
            session=session,
            error=str(e)
        )
    
    except SLMError as e:
        session.complete("failed", str(e))
        return CommandResult(
            status="failed",
            feedback=e.user_message(),
            session=session,
            error=str(e)
        )
    
    except Exception as e:
        logger.exception(f"Unexpected error processing command: {e}")
        session.complete("failed", str(e))
        return CommandResult(
            status="failed",
            feedback="Something went wrong. Please try again",
            session=session,
            error=str(e)
        )
```

## Feedback Generation (User Story 4)

### Success Messages

```python
def _generate_feedback(self, command: Command, device: DeviceMapping) -> str:
    """Generate user-friendly confirmation message."""
    device_name = device.name.replace('_', ' ').title()
    
    if command.intent == "turn_on":
        return f"{device_name} turned on"
    
    elif command.intent == "turn_off":
        return f"{device_name} turned off"
    
    elif command.intent == "set_brightness":
        brightness = command.parameters.get('brightness')
        return f"{device_name} brightness set to {brightness}%"
    
    elif command.intent == "set_temperature":
        temp = command.parameters.get('temperature')
        return f"{device_name} temperature set to {temp}°"
    
    else:
        return f"{device_name} updated"
```

## Performance Requirements

- **Total Latency**: <5 seconds end-to-end (SC-001)
  - SLM Inference: ~0.8s
  - Device Lookup: ~0.05s
  - State Check: ~0.01s
  - MQTT Publish: ~0.1s
  - **Target**: <3s per spec (SC-001: within 5s of finishing speaking)
  
- **Throughput**: 50+ consecutive commands without degradation (SC-006)
- **Memory**: <100MB for router + dependencies (excluding models)

## Testing Requirements

### Contract Tests (`tests/contract/test_command_parser_contract.py`)

1. **Full Pipeline Success**: Transcription → MQTT publish → success result
2. **Unknown Intent**: Non-command text → unknown_intent result
3. **Device Not Found**: Invalid device → failed result with specific error
4. **State Awareness**: Redundant command → already_done result
5. **MQTT Failure**: Broker offline → failed result with error message

### Unit Tests (`tests/unit/test_command_parser.py`)

1. **Device Validation**: Test lookup logic
2. **State Check Logic**: Test redundancy detection
3. **Feedback Generation**: Test message formatting for each intent
4. **Error Mapping**: Test exception → user message conversion
5. **Batch Processing**: Test process_batch() with multiple commands

### Integration Tests (`tests/integration/test_text_to_command_pipeline.py`)

1. **End-to-End**: Voice → Text → Command → MQTT → Feedback
2. **Error Recovery**: SLM fails → graceful error response
3. **State Updates**: Publish command → verify state cache updated
4. **Multiple Devices**: Command 5 different devices in sequence

## Dependencies

- `src/command/slm_engine.py`: SLMEngine class
- `src/devices/mqtt_client.py`: MQTTClient class
- `src/devices/mapping.py`: DeviceRegistry class
- `src/devices/state.py`: StateCache class
- `src/command/models.py`: Command, CommandSession data classes
- `dataclasses`: Result structures (stdlib)
- `logging`: Operational logging (stdlib)

## Thread Safety

- **NOT Thread-Safe**: SLMEngine is not thread-safe
- **Recommendation**: Use single CommandRouter instance, process commands sequentially
- **Future Enhancement**: Add queue + worker thread for concurrent command handling

## Configuration

```yaml
# config/command_router.yaml
features:
  state_awareness: true      # User Story 3 - check redundancy
  feedback_generation: true  # User Story 4 - confirmation messages
  batch_processing: true     # FR-018 - multiple commands

timeouts:
  slm_inference: 10          # Seconds (FR-019)
  mqtt_publish: 5            # Seconds

validation:
  require_device_exists: true
  require_capability_match: true  # Validate intent matches device capabilities
```

## Privacy Compliance

- **No Transcription Logging**: CommandSession clears `transcribed_text` on completion
- **Metadata Only**: Log only intent, device, status, duration
- **Session Lifecycle**: Sessions are ephemeral, discarded after processing

```python
# GOOD: Privacy-safe logging
logger.info(f"Command processed: {result.to_log_entry()}")

# BAD: Privacy violation
# logger.info(f"User said: {transcription}")  ❌
```

---

**Contract Status**: ✅ Complete  
**Implements**: FR-001, FR-004, FR-005, FR-006, FR-012, FR-015, FR-018  
**User Stories**: US1 (Command Understanding), US2 (MQTT Publishing), US3 (State Awareness), US4 (Feedback)  
**Success Criteria**: SC-001, SC-002, SC-005, SC-008
