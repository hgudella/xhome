# Feature Specification: SLM Command Processing and MQTT Integration

**Feature Branch**: `002-slm-mqtt-integration`  
**Created**: 2025-12-11  
**Status**: Draft  
**Input**: User description: "Pass transcribed text from audio to Phi-4-Mini-GGUF SLM and send commands to MQTT based on user commands"

## Clarifications

### Session 2025-12-11

- Q: What MQTT QoS level should be used for command messages? → A: QoS 1 (at least once) - Balanced approach ensuring delivery with possible duplicates, suitable for idempotent home automation commands

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Command Understanding (Priority: P1)

The user speaks a natural language command (e.g., "turn on the living room light"), which is transcribed to text and then processed by the Phi-4-Mini-GGUF model to extract the intent and parameters. The system identifies what action should be performed and on which device.

**Why this priority**: This is the foundational capability that bridges voice input to actionable commands. Without understanding user intent, the system cannot perform any meaningful actions. This transforms raw text into structured commands.

**Independent Test**: Can be fully tested by providing text transcriptions and verifying that the SLM correctly identifies the intent (e.g., "turn on"), target device (e.g., "living room light"), and parameters. Delivers the value of "the system understands my intent."

**Acceptance Scenarios**:

1. **Given** transcribed text "turn on the living room light", **When** processed by Phi-4-Mini-GGUF, **Then** the system identifies intent="turn_on", device="living_room_light"
2. **Given** transcribed text "set bedroom light to 50 percent brightness", **When** processed by the SLM, **Then** the system extracts intent="set_brightness", device="bedroom_light", value=50
3. **Given** transcribed text contains an ambiguous command, **When** processed by the SLM, **Then** the system requests clarification or uses the most likely interpretation
4. **Given** transcribed text is unrelated to device control, **When** processed, **Then** the system recognizes it as not actionable and provides appropriate feedback
5. **Given** transcribed text contains multiple commands, **When** processed, **Then** the system identifies each distinct command separately

---

### User Story 2 - MQTT Command Publishing (Priority: P1)

Once the system understands the user's intent, it translates the parsed command into an MQTT message and publishes it to the appropriate topic. The home automation devices subscribed to these topics receive and execute the commands.

**Why this priority**: This is equally critical as command understanding - it's the output mechanism that makes the system useful. Without MQTT publishing, understood commands cannot control any devices.

**Independent Test**: Can be fully tested by processing known commands and verifying that correct MQTT messages are published to the appropriate topics with proper payloads. Delivers the value of "the system controls my devices."

**Acceptance Scenarios**:

1. **Given** intent="turn_on" and device="living_room_light", **When** command is executed, **Then** MQTT message is published to topic "home/light/living_room/set" with payload {"state":"ON"}
2. **Given** intent="set_brightness" device="bedroom_light" value=50, **When** command is executed, **Then** MQTT message is published with payload {"state":"ON","brightness":50}
3. **Given** multiple commands are identified, **When** execution begins, **Then** each command publishes a separate MQTT message to its respective topic
4. **Given** MQTT broker is unreachable, **When** publishing is attempted, **Then** the system logs the error and notifies the user of the failure
5. **Given** a command is successfully published, **When** MQTT confirms delivery, **Then** the system logs the success and provides confirmation feedback

---

### User Story 3 - Device State Awareness (Priority: P2)

The system maintains awareness of device states by subscribing to MQTT state topics. This enables context-aware responses (e.g., "the light is already on") and prevents unnecessary commands.

**Why this priority**: While valuable for user experience and efficiency, the system can function without state awareness. Commands can still be sent even if devices are already in the desired state.

**Independent Test**: Can be fully tested by subscribing to device state topics, tracking state changes, and verifying that the system reflects current device states when responding to user commands. Delivers the value of "the system knows the current state of my devices."

**Acceptance Scenarios**:

1. **Given** the system is subscribed to "home/light/+/state", **When** a device publishes its state, **Then** the system updates its internal state cache
2. **Given** a user says "turn on the living room light" and it's already on, **When** the command is processed, **Then** the system responds with "the living room light is already on"
3. **Given** the system starts up, **When** initialization completes, **Then** the system subscribes to all relevant state topics and queries current device states
4. **Given** a device goes offline, **When** the user issues a command to that device, **Then** the system warns that the device may be unavailable

---

### User Story 4 - Command Confirmation and Feedback (Priority: P3)

The system provides audio or visual feedback to confirm command execution and report results. Users receive clear confirmation that their command was understood and executed.

**Why this priority**: This is a user experience enhancement. The system can successfully control devices without explicit confirmation feedback, though users benefit from knowing their commands were processed.

**Independent Test**: Can be fully tested by issuing commands and verifying that appropriate confirmation messages are generated (text or audio). Delivers the value of "I know the system did what I asked."

**Acceptance Scenarios**:

1. **Given** a command is successfully executed, **When** MQTT delivery is confirmed, **Then** the system provides feedback "Living room light turned on"
2. **Given** a command fails, **When** the error is detected, **Then** the system provides clear error feedback "Could not reach the bedroom light"
3. **Given** the user issues an unclear command, **When** the SLM cannot parse it, **Then** the system asks for clarification "I didn't understand which light you meant"

---

### Edge Cases

- What happens when the SLM model fails to load or crashes during inference?
- How does the system handle commands for devices that don't exist in the configuration?
- What happens when MQTT broker connection is lost during command execution?
- How does the system handle malformed or unexpected responses from the SLM?
- What happens when multiple devices match the user's description (e.g., "the light" when there are multiple lights)?
- How does the system behave when MQTT message queuing is full or backlogged?
- What happens when the transcription quality is poor and the SLM receives garbled text?
- How does the system handle commands that require confirmation before execution (e.g., "turn off all lights")?
- What happens when device state information is stale or inconsistent?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST accept transcribed text from the voice-to-text feature as input
- **FR-002**: System MUST process text using the Phi-4-Mini-GGUF model for intent extraction
- **FR-003**: System MUST run the Phi-4-Mini-GGUF model locally without external API calls
- **FR-004**: System MUST identify command intent from natural language (e.g., turn_on, turn_off, set_brightness, set_temperature)
- **FR-005**: System MUST extract target device identifiers from user commands
- **FR-006**: System MUST extract command parameters such as brightness levels, colors, or temperature values
- **FR-007**: System MUST maintain a mapping of natural language device names to MQTT topics
- **FR-008**: System MUST publish commands to MQTT broker using appropriate topics
- **FR-009**: System MUST format MQTT payloads according to device-specific requirements (e.g., JSON, plain text)
- **FR-010**: System MUST handle MQTT connection failures gracefully with retry logic
- **FR-011**: System MUST subscribe to device state topics to maintain current device status
- **FR-012**: System MUST validate commands before publishing to MQTT
- **FR-013**: System MUST log all command processing activities including intent, device, and MQTT topic
- **FR-014**: System MUST NOT persist user commands or transcribed text beyond immediate processing
- **FR-015**: System MUST provide feedback on command execution success or failure
- **FR-016**: System MUST support configurable MQTT broker connection parameters (host, port, credentials)
- **FR-017**: System MUST handle multiple device types (lights, switches, sensors, thermostats)
- **FR-018**: System MUST support batch commands when multiple devices are mentioned in a single utterance
- **FR-019**: System MUST timeout SLM inference if processing exceeds a reasonable duration
- **FR-020**: System MUST use QoS level 1 (at least once) for MQTT command messages to ensure reliable delivery while allowing graceful handling of potential duplicates

### Key Entities

- **Command**: Represents a parsed user intent extracted from transcribed text. Attributes include intent type (turn_on, turn_off, set_brightness, etc.), target device identifier, command parameters (brightness, color, temperature), confidence score, and timestamp.

- **DeviceMapping**: Links natural language device references to MQTT topics. Attributes include device name (natural language), device ID (system identifier), MQTT command topic, MQTT state topic, device type (light, switch, thermostat), and supported capabilities.

- **MQTTMessage**: Represents a message to be published to the MQTT broker. Attributes include topic, payload (structured data like JSON or plain text), QoS level, retain flag, and timestamp.

- **DeviceState**: Tracks the current state of a device based on MQTT state messages. Attributes include device ID, current state (on/off, brightness level, temperature, etc.), last updated timestamp, and availability status.

- **CommandSession**: Represents the lifecycle of a single voice command from transcription to MQTT publication. Tracks session ID, transcribed text input, extracted command(s), MQTT messages published, execution results, errors encountered, and duration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can issue voice commands that result in MQTT messages being published within 5 seconds of finishing speaking
- **SC-002**: The SLM correctly identifies command intent and target device with at least 90% accuracy for common commands
- **SC-003**: System successfully publishes MQTT messages with 95% reliability when the broker is reachable
- **SC-004**: System processes commands entirely locally without external API calls or cloud services
- **SC-005**: Users receive feedback on command execution within 1 second of MQTT publication
- **SC-006**: System handles at least 50 consecutive commands without memory leaks or performance degradation
- **SC-007**: The SLM model loads and is ready for inference within 15 seconds of system startup
- **SC-008**: System correctly handles ambiguous commands by requesting clarification in at least 80% of cases
- **SC-009**: MQTT connection recovers automatically within 30 seconds of broker becoming available after an outage

## Assumptions *(if applicable)*

- The voice-to-text feature (Feature 001) is fully implemented and provides transcribed text
- An MQTT broker is available and accessible on the local network
- Devices to be controlled are already configured and subscribed to their respective MQTT topics
- Device MQTT topic structure follows a consistent naming convention (e.g., home/device_type/device_name/set)
- The Phi-4-Mini-GGUF model is compatible with the target hardware (CPU or GPU inference)
- Users will issue commands in English for the initial implementation
- Device names and locations are predefined in a configuration file
- The system has sufficient resources to run both Whisper and Phi-4-Mini-GGUF models simultaneously (estimated 3-4 GB RAM)
- MQTT broker uses standard protocols (MQTT 3.1.1 or 5.0) without proprietary extensions

## Out of Scope *(if applicable)*

The following items are explicitly excluded from this feature:

- Device discovery and automatic configuration
- Multi-user voice profiles and personalized command preferences
- Advanced natural language conversation (follow-up questions, context from previous commands)
- Integration with cloud-based voice assistants (Alexa, Google Assistant)
- Voice authentication and authorization
- Device grouping and scene management (e.g., "movie mode")
- Scheduling and automation rules (time-based or event-triggered)
- Web or mobile UI for configuration and monitoring
- Integration with non-MQTT protocols (Zigbee, Z-Wave, Bluetooth directly)
- Device firmware updates or health monitoring
- Energy usage tracking and reporting
- Custom SLM model training or fine-tuning
- Multi-language support beyond English

## Dependencies *(if applicable)*

- **Feature 001**: Voice-to-Text Transcription must be implemented to provide text input
- **llama-cpp-python** or **gguf**: Required for running Phi-4-Mini-GGUF model locally
- **paho-mqtt**: Python MQTT client library for broker communication
- **Phi-4-Mini-GGUF model file**: Must be downloaded and available locally
- **Python 3.10+**: Runtime environment requirement
- **MQTT Broker**: External service (e.g., Mosquitto, HiveMQ) must be running and accessible
- **Device Configuration File**: JSON or YAML file mapping device names to MQTT topics

## Non-Functional Requirements *(if applicable)*

- **Performance**: Command processing latency from transcription receipt to MQTT publication should not exceed 3 seconds
- **Reliability**: System should successfully process 95% of well-formed commands when broker is available
- **Resource Usage**: Peak memory usage should not exceed 4 GB with both Whisper and Phi-4-Mini models loaded
- **Privacy**: Command text must not be persisted to disk; processed only in memory and then discarded
- **Logging**: Logs must include command metadata (intent, device, timestamp) but exclude full transcription text to minimize privacy exposure
- **Error Handling**: All errors (SLM failures, MQTT connection issues) must be caught, logged, and communicated to the user without crashing
- **Scalability**: System should support at least 50 unique device mappings without performance degradation
- **Startup Time**: System initialization including both models should complete within 20 seconds
- **MQTT Connection**: System must maintain persistent connection to broker with automatic reconnection on failure
- **Model Inference**: SLM inference timeout should be set to prevent indefinite blocking (recommend 10 second timeout)
