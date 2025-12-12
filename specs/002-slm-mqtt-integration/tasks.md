# Tasks: SLM Command Processing and MQTT Integration

**Feature**: 002-slm-mqtt-integration  
**Input**: spec.md, plan.md, research.md, data-model.md, contracts/  
**Generated**: 2025-12-11

**Organization**: Tasks grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: User story mapping (US1, US2, US3, US4, FOUND = Foundational)
- All paths relative to repository root

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency management

- [ ] T001 Add new dependencies to requirements.txt: llama-cpp-python, paho-mqtt==1.6.0, pyyaml
- [ ] T002 Download Phi-4-Mini-GGUF Q4_K_M model (~2GB) to models/Phi-4-Mini-GGUF/
- [ ] T003 [P] Create config/devices.yaml.example with sample device mappings
- [ ] T004 [P] Create .env.example with MQTT broker and SLM configuration variables
- [ ] T005 [P] Create src/command/ directory for SLM integration module
- [ ] T006 [P] Create src/devices/ directory for device mapping and MQTT module
- [ ] T007 [P] Create tests/contract/ directory for contract tests
- [ ] T008 [P] Create config/ directory for device configuration files

**Checkpoint**: Project structure ready for implementation

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story implementation

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Configuration Management

- [ ] T009 [P] [FOUND] Implement DeviceConfig class in src/devices/config.py to load YAML
  - Parse devices.yaml with device mappings
  - Support aliases for flexible device name matching
  - Validate MQTT topic structure (home/{type}/{location}/{set|state})
  - Raise ConfigurationError for malformed YAML

- [ ] T010 [P] [FOUND] Implement MQTTConfig class in src/devices/mqtt_config.py
  - Load broker host, port, username, password from environment
  - Provide defaults (localhost:1883)
  - Validate configuration completeness

### Custom Exceptions

- [ ] T011 [P] [FOUND] Create exception hierarchy in src/utils/exceptions.py
  - SLMError (base for SLM-related errors)
  - ModelLoadError (model loading failures)
  - InferenceError (SLM inference failures)
  - TimeoutError (SLM timeout exceeded)
  - MQTTError (base for MQTT-related errors)
  - MQTTConnectionError (connection failures)
  - MQTTPublishError (publish failures)
  - DeviceNotFoundError (device not in configuration)
  - ConfigurationError (malformed configuration)
  - CommandParsingError (invalid command structure)

### Data Models

- [ ] T012 [P] [FOUND] Create Command dataclass in src/command/models.py
  - Attributes: intent (str), device (str), parameters (dict), confidence (float), timestamp (datetime)
  - Validation: require intent and device, validate intent values
  - JSON serialization support for logging

- [ ] T013 [P] [FOUND] Create DeviceMapping dataclass in src/devices/models.py
  - Attributes: name (str), aliases (List[str]), device_type (str), command_topic (str), state_topic (str), capabilities (List[str])
  - Method: matches(query: str) -> bool for alias matching

- [ ] T014 [P] [FOUND] Create MQTTMessage dataclass in src/devices/models.py
  - Attributes: topic (str), payload (dict), qos (int), timestamp (datetime)
  - JSON payload serialization
  - QoS validation (0, 1, 2)

- [ ] T015 [P] [FOUND] Create DeviceState dataclass in src/devices/state.py
  - Attributes: device_id (str), state (dict), last_updated (datetime), available (bool)
  - Method: is_stale(ttl_seconds: int) -> bool for TTL checking

- [ ] T016 [P] [FOUND] Create CommandSession dataclass in src/command/session.py
  - Attributes: session_id (UUID), transcription (str), commands (List[Command]), mqtt_messages (List[MQTTMessage]), errors (List[str]), duration_ms (int)
  - Privacy: clear() method to wipe transcription after processing
  - Logging support with PII redaction

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Command Understanding (Priority: P1) 🎯 MVP

**Goal**: Process natural language text and extract structured commands using Phi-4-Mini-GGUF

**Independent Test**: Provide text input → verify correct Command objects with intent, device, parameters

### Contract Tests for User Story 1

> **⚠️ WRITE THESE TESTS FIRST, ENSURE THEY FAIL BEFORE IMPLEMENTATION**

- [ ] T017 [P] [US1] Contract test for SLMEngine in tests/contract/test_slm_interface.py
  - Test: Model loads successfully within 15s (FR-002, SC-007)
  - Test: extract_command("turn on living room light") returns Command(intent="turn_on", device="living_room_light")
  - Test: extract_command with brightness returns Command with parameters={"brightness": 50}
  - Test: Unrelated text returns None or CommandParsingError
  - Test: SLM timeout after 10s raises TimeoutError (FR-019)
  - Test: Malformed SLM output raises InferenceError
  - Test: Model unload cleans up resources

- [ ] T018 [P] [US1] Integration test for text-to-command pipeline in tests/integration/test_command_extraction.py
  - Test: Multiple command formats (turn on/off, set brightness, set temperature)
  - Test: Device alias matching ("lounge light" → "living_room_light")
  - Test: Confidence scores returned for ambiguous commands
  - Test: Batch command extraction for multi-device utterances (FR-018)
  - Test: Performance: 50 consecutive commands without memory leaks (SC-006)

### Implementation for User Story 1

- [ ] T019 [US1] Implement SLMEngine class in src/command/slm_engine.py
  - Load Phi-4-Mini-GGUF using llama-cpp-python
  - Configure context_length=2048, n_gpu_layers=32 (if GPU available)
  - Implement __init__(model_path: str) with model loading
  - Implement is_loaded() property
  - Implement unload() for cleanup
  - Add structured logging (model load time, memory usage)
  - Handle ModelLoadError if model file missing or corrupted

- [ ] T020 [US1] Implement extract_command method in SLMEngine (src/command/slm_engine.py)
  - Build prompt with few-shot examples (from contracts/slm_interface.md)
  - Set temperature=0.1 for deterministic output
  - Set max_tokens=256 for command extraction
  - Enforce 10s timeout using threading or asyncio (FR-019)
  - Parse JSON response into Command object
  - Handle InferenceError for unparseable output
  - Handle TimeoutError if inference exceeds 10s
  - Log inference time (target: <1s per FR-020 performance)
  - NEVER log transcription text (privacy: FR-014)

- [ ] T021 [US1] Implement prompt template in src/command/prompts.py
  - Few-shot JSON examples for intents: turn_on, turn_off, set_brightness, set_temperature
  - Handle multi-device commands (FR-018)
  - Handle ambiguous/unrelated text with confidence scoring
  - Format: System prompt + few-shot examples + user transcription

- [ ] T022 [US1] Implement CommandParser class in src/command/parser.py
  - Wrapper around SLMEngine for high-level command extraction
  - parse(transcription: str) -> List[Command] supporting batch commands
  - Integrate device alias matching from DeviceConfig
  - Validate extracted device names against configuration
  - Raise DeviceNotFoundError if device not in config (FR-012)
  - Create CommandSession for tracking (FR-014)

- [ ] T023 [US1] Add command extraction logging in src/command/parser.py
  - Log: session_id, intent, device, parameters (NOT transcription)
  - Log: SLM inference time, confidence score
  - Log: Errors with context (model load, timeout, parsing)
  - Use structured JSON logging for machine parsing (FR-013)

**Checkpoint**: Text input → Command extraction working independently

---

## Phase 4: User Story 2 - MQTT Command Publishing (Priority: P1) 🎯 MVP

**Goal**: Publish extracted commands to MQTT broker with QoS 1 reliability

**Independent Test**: Provide Command objects → verify correct MQTT messages published to topics

### Contract Tests for User Story 2

> **⚠️ WRITE THESE TESTS FIRST, ENSURE THEY FAIL BEFORE IMPLEMENTATION**

- [ ] T024 [P] [US2] Contract test for MQTTClient in tests/contract/test_mqtt_publisher.py
  - Test: connect() establishes connection within 5s
  - Test: publish_command() sends message with QoS 1 and receives PUBACK (FR-020)
  - Test: publish_command for turn_on sends {"state":"ON"} payload
  - Test: publish_command for set_brightness sends {"state":"ON","brightness":50}
  - Test: Connection retry with exponential backoff (2s, 4s, 8s) on failure (FR-010)
  - Test: MQTTConnectionError raised after 3 failed connection attempts
  - Test: MQTTPublishError raised on publish timeout
  - Test: disconnect() closes connection cleanly

- [ ] T025 [P] [US2] Integration test for command-to-MQTT pipeline in tests/integration/test_mqtt_publishing.py
  - Test: Command(intent="turn_on") → correct topic and payload
  - Test: Multiple commands publish to different topics (FR-018)
  - Test: Batch commands publish sequentially with QoS 1 confirmation
  - Test: Performance: <100ms publish latency per message (SC-003)
  - Test: Broker unavailable → error logged and user notified (FR-010)

### Implementation for User Story 2

- [ ] T026 [US2] Implement MQTTClient class in src/devices/mqtt_client.py
  - Use paho-mqtt library (version 1.6.0+)
  - Implement __init__(host: str, port: int, username: str, password: str)
  - Implement connect() with retry logic (exponential backoff: 2s, 4s, 8s)
  - Implement on_connect, on_disconnect, on_publish callbacks
  - Track connection state with is_connected property
  - Raise MQTTConnectionError after 3 failed attempts (FR-010)
  - Log connection events (connected, disconnected, retrying)

- [ ] T027 [US2] Implement publish_command method in MQTTClient (src/devices/mqtt_client.py)
  - Accept Command and DeviceMapping as input
  - Build MQTT topic from DeviceMapping.command_topic
  - Build payload dict from Command.intent and Command.parameters
  - Serialize payload to JSON
  - Publish with QoS 1 (at least once) per FR-020
  - Wait for PUBACK confirmation (timeout: 5s)
  - Raise MQTTPublishError on timeout or failure
  - Log: topic, payload size, QoS level, publish latency
  - Return MQTTMessage object for session tracking

- [ ] T028 [US2] Implement payload builders in src/devices/payload.py
  - build_turn_on_payload() -> {"state": "ON"}
  - build_turn_off_payload() -> {"state": "OFF"}
  - build_set_brightness_payload(value: int) -> {"state": "ON", "brightness": value}
  - build_set_temperature_payload(value: int) -> {"temperature": value}
  - Validate parameter ranges (brightness: 0-100, temperature: configurable)
  - Raise ValueError for out-of-range parameters

- [ ] T029 [US2] Implement disconnect and cleanup in MQTTClient (src/devices/mqtt_client.py)
  - disconnect() method for graceful shutdown
  - Flush pending messages before disconnecting
  - Clear connection state
  - Log disconnection event

- [ ] T030 [US2] Implement CommandRouter class in src/command/router.py
  - Orchestrate full pipeline: SLMEngine → DeviceConfig → MQTTClient
  - process_command(transcription: str) -> CommandSession
  - Stage 1: Extract Command(s) using SLMEngine
  - Stage 2: Validate device exists in DeviceConfig
  - Stage 3: Publish to MQTT using MQTTClient
  - Stage 4: Track results in CommandSession
  - Handle errors at each stage with user-friendly messages
  - Ensure transcription cleared after processing (privacy: FR-014)

- [ ] T031 [US2] Add MQTT logging in src/devices/mqtt_client.py
  - Log: connection state changes, retry attempts, connection duration
  - Log: publish events (topic, QoS, size, latency, success/failure)
  - Log: PUBACK confirmations for QoS 1 messages
  - Use structured JSON logging (FR-013)

**Checkpoint**: Command objects → MQTT messages published successfully (MVP COMPLETE)

---

## Phase 5: User Story 3 - Device State Awareness (Priority: P2)

**Goal**: Subscribe to device state topics and track current device states to avoid redundant commands

**Independent Test**: Publish state messages → verify system tracks states → verify redundancy detection

### Contract Tests for User Story 3

> **⚠️ WRITE THESE TESTS FIRST, ENSURE THEY FAIL BEFORE IMPLEMENTATION**

- [ ] T032 [P] [US3] Contract test for state subscription in tests/contract/test_mqtt_state.py
  - Test: subscribe_state_topics() subscribes to all device state topics from config
  - Test: State callback receives and parses state messages
  - Test: DeviceState updated with new state, timestamp, availability
  - Test: Stale state detection after TTL (5 minutes) expired
  - Test: State cache cleared on disconnect

- [ ] T033 [P] [US3] Integration test for state-aware commands in tests/integration/test_state_awareness.py
  - Test: Device state ON → "turn on" command returns "already on" message
  - Test: Device state OFF → "turn on" command publishes normally
  - Test: Stale state (>5 min) → command proceeds without redundancy check
  - Test: State unavailable → command proceeds with warning
  - Test: Multiple devices with different states handled correctly

### Implementation for User Story 3

- [ ] T034 [US3] Implement DeviceStateCache class in src/devices/state_cache.py
  - Dictionary storage: device_id -> DeviceState
  - update(device_id: str, state: dict) method
  - get(device_id: str) -> Optional[DeviceState] method
  - is_stale(device_id: str, ttl_seconds: int = 300) -> bool (5 min TTL)
  - clear() for cleanup on disconnect
  - Thread-safe operations using threading.Lock

- [ ] T035 [US3] Implement state subscription in MQTTClient (src/devices/mqtt_client.py)
  - subscribe_state_topics(topics: List[str]) method
  - Subscribe with QoS 1 for reliable state updates
  - on_message callback to parse state messages
  - Call state_callback(device_id, state_dict) on message
  - Log state subscription events and message receipt

- [ ] T036 [US3] Integrate state awareness in CommandRouter (src/command/router.py)
  - Add DeviceStateCache to __init__
  - Add check_state parameter to process_command (default: True)
  - Stage 2.5: After device validation, check current state
  - If state matches intent (e.g., already ON for turn_on), skip MQTT publish
  - Return feedback: "Device is already in requested state"
  - If state is stale (>5 min), proceed with command (log warning)
  - If state unavailable, proceed with command (log info)

- [ ] T037 [US3] Implement get_device_state method in CommandRouter (src/command/router.py)
  - get_device_state(device_id: str) -> Optional[dict]
  - Return current state from DeviceStateCache
  - Return None if state unknown or stale
  - Used by US4 for feedback generation

- [ ] T038 [US3] Add state awareness logging in src/devices/state_cache.py
  - Log: state updates (device, previous state, new state, timestamp)
  - Log: stale state detections (device, age, TTL threshold)
  - Log: cache operations (size, hit rate for debugging)

**Checkpoint**: State awareness working, redundant commands detected and skipped

---

## Phase 6: User Story 4 - Command Confirmation and Feedback (Priority: P3)

**Goal**: Generate clear user-facing feedback messages for command results

**Independent Test**: Process commands with various outcomes → verify appropriate feedback messages generated

### Contract Tests for User Story 4

> **⚠️ WRITE THESE TESTS FIRST, ENSURE THEY FAIL BEFORE IMPLEMENTATION**

- [ ] T039 [P] [US4] Contract test for feedback generation in tests/contract/test_feedback.py
  - Test: Successful command → "Living room light turned on"
  - Test: Already in state → "Living room light is already on"
  - Test: Device not found → "I don't recognize a device called 'garage light'"
  - Test: MQTT publish failure → "Could not reach the bedroom light"
  - Test: SLM parsing failure → "I didn't understand that command"
  - Test: Multiple commands → separate feedback for each

### Implementation for User Story 4

- [ ] T040 [US4] Implement FeedbackGenerator class in src/command/feedback.py
  - generate(command: Command, result: str, error: Optional[Exception]) -> str
  - Template-based message generation
  - Success messages: "{device} {action} successfully" (friendly names)
  - State-aware messages: "{device} is already {state}"
  - Error messages: map exception types to user-friendly text
  - DeviceNotFoundError → "I don't recognize a device called '{device}'"
  - MQTTConnectionError → "Could not reach {device}"
  - CommandParsingError → "I didn't understand that command"
  - TimeoutError → "Command processing took too long"

- [ ] T041 [US4] Integrate feedback in CommandRouter (src/command/router.py)
  - Add FeedbackGenerator to __init__
  - Stage 5: Generate feedback after each command
  - Store feedback in CommandSession.feedback field
  - Return feedback as part of process_command response
  - Support batch feedback for multiple commands

- [ ] T042 [US4] Implement friendly device name mapping in src/devices/config.py
  - Add display_name field to DeviceMapping
  - get_friendly_name(device_id: str) -> str method
  - Convert "living_room_light" → "Living room light" for messages
  - Use in feedback generation for natural language responses

**Checkpoint**: All user stories complete, full voice-to-MQTT pipeline functional

---

## Phase 7: Integration & Testing

**Purpose**: End-to-end testing and integration across all user stories

- [ ] T043 [P] Integration test for full pipeline in tests/integration/test_full_pipeline.py
  - Test: Text → SLM → MQTT → Feedback (all 4 user stories)
  - Test: Continuous processing (50 commands) without memory leaks (SC-006)
  - Test: Performance: <3s text-to-MQTT latency (SC-001, NFR performance)
  - Test: Privacy: transcription not persisted after processing (FR-014)
  - Test: Error recovery: handle SLM failure, MQTT disconnect, invalid device

- [ ] T044 [P] Unit test for SLMEngine in tests/unit/test_slm_engine.py
  - Test model loading with valid and invalid paths
  - Test prompt formatting with various inputs
  - Test JSON parsing from SLM responses
  - Test timeout enforcement mechanism
  - Test memory cleanup on unload

- [ ] T045 [P] Unit test for MQTTClient in tests/unit/test_mqtt_client.py
  - Test connection state management
  - Test retry logic with mock broker
  - Test QoS 1 publish and PUBACK handling
  - Test payload serialization
  - Test error handling for network issues

- [ ] T046 [P] Unit test for CommandRouter in tests/unit/test_command_router.py
  - Test 5-stage pipeline logic
  - Test error handling at each stage
  - Test state awareness integration
  - Test feedback generation
  - Test session tracking and cleanup

- [ ] T047 [P] Unit test for DeviceStateCache in tests/unit/test_state_cache.py
  - Test update and retrieval operations
  - Test TTL expiration logic
  - Test thread safety with concurrent access
  - Test cache clearing

- [ ] T048 [P] Unit test for configuration loading in tests/unit/test_device_config.py
  - Test YAML parsing
  - Test device alias matching
  - Test configuration validation
  - Test error handling for malformed files

---

## Phase 8: CLI Integration & User Experience

**Purpose**: Integrate command processing into main.py CLI

- [ ] T049 Add --enable-commands flag to main.py CLI
  - Enable/disable command processing feature
  - Load SLMEngine and MQTTClient on startup if enabled
  - Add --mqtt-host and --mqtt-port CLI arguments
  - Add --device-config argument for custom devices.yaml path

- [ ] T050 Integrate CommandRouter into continuous listening mode (main.py)
  - After transcription, call CommandRouter.process_command()
  - Display feedback to user (console output)
  - Log session details to logs/assistant.log
  - Handle errors gracefully without crashing continuous mode

- [ ] T051 Add --state-awareness flag to main.py
  - Enable/disable state tracking (default: enabled)
  - Pass to CommandRouter during initialization
  - Document in --help output

- [ ] T052 Add --text-only mode for command testing
  - Skip voice input, accept text from stdin
  - Direct integration with CommandRouter for debugging
  - Display extracted Command objects and MQTT messages
  - Useful for testing without microphone

---

## Phase 9: Documentation & Polish

**Purpose**: Finalize documentation and deployment readiness

- [ ] T053 [P] Update README.md with Feature 002 information
  - Add SLM command processing overview
  - Add MQTT integration section
  - Update architecture diagram
  - Add new dependencies and setup steps

- [ ] T054 [P] Create API documentation in docs/api/command_processing.md
  - Document SLMEngine interface
  - Document MQTTClient interface
  - Document CommandRouter interface
  - Include usage examples

- [ ] T055 [P] Validate quickstart.md instructions
  - Run through all setup steps manually
  - Test example commands
  - Verify MQTT broker setup instructions
  - Validate troubleshooting section

- [ ] T056 [P] Add configuration documentation in docs/configuration.md
  - Document devices.yaml schema
  - Document environment variables
  - Provide example configurations for common devices
  - Document MQTT topic structure

- [ ] T057 Performance profiling and optimization
  - Profile SLM inference time (target: <1s)
  - Profile MQTT publish latency (target: <100ms)
  - Profile end-to-end latency (target: <3s per SC-001)
  - Optimize if any target exceeded
  - Document performance results

- [ ] T058 Security review
  - Verify no transcription persistence (FR-014)
  - Verify PII redaction in logs
  - Verify MQTT credentials from environment (not hardcoded)
  - Verify input validation for device parameters
  - Document security considerations

---

## Dependencies & Execution Order

### Phase Dependencies

1. **Setup (Phase 1)**: No dependencies - start immediately
2. **Foundational (Phase 2)**: Depends on Setup - BLOCKS all user stories
3. **User Story 1 (Phase 3)**: Depends on Foundational - Can start after T016
4. **User Story 2 (Phase 4)**: Depends on Foundational - Can start after T016
5. **User Story 3 (Phase 5)**: Depends on US2 complete - Extends MQTTClient and CommandRouter
6. **User Story 4 (Phase 6)**: Depends on US2 complete - Extends CommandRouter
7. **Integration (Phase 7)**: Depends on all user stories complete
8. **CLI Integration (Phase 8)**: Depends on US1 and US2 complete (US3/US4 optional)
9. **Documentation (Phase 9)**: Can start after US2, parallelize with US3/US4

### User Story Dependencies

- **US1 (P1)**: Independent - only needs Foundational
- **US2 (P1)**: Independent - only needs Foundational (can parallel with US1)
- **US3 (P2)**: Depends on US2 (extends MQTTClient and CommandRouter)
- **US4 (P3)**: Depends on US2 (extends CommandRouter)

### Critical Path (MVP)

```
Setup → Foundational → US1 + US2 (parallel) → CLI Integration → MVP COMPLETE
```

### Full Feature Path

```
Setup → Foundational → US1 + US2 (parallel) → US3 → US4 → Integration → CLI → Docs → COMPLETE
```

### Parallel Opportunities

**Phase 1 (Setup)**:
- T003, T004, T005, T006, T007, T008 (all parallel)

**Phase 2 (Foundational)**:
- T009, T010 (config loading - parallel)
- T011 (exceptions - parallel with config)
- T012, T013, T014, T015, T016 (all data models - parallel)

**Phase 3 (US1)**:
- T017, T018 (contract/integration tests - parallel)

**Phase 4 (US2)**:
- T024, T025 (contract/integration tests - parallel)

**Phase 7 (Integration)**:
- T043, T044, T045, T046, T047, T048 (all tests - parallel)

**Phase 9 (Documentation)**:
- T053, T054, T055, T056 (all docs - parallel)

---

## Implementation Strategy

### MVP First (US1 + US2 Only)

1. Complete Phase 1: Setup (T001-T008)
2. Complete Phase 2: Foundational (T009-T016) - CRITICAL BLOCKER
3. Complete Phase 3: US1 (T017-T023) - Command extraction
4. Complete Phase 4: US2 (T024-T031) - MQTT publishing
5. Complete Phase 8: CLI Integration (T049-T050)
6. **STOP and VALIDATE**: Test voice → text → command → MQTT end-to-end
7. Deploy/demo MVP

**MVP Delivers**: Voice commands control devices via MQTT

### Incremental Delivery (Full Feature)

1. Setup + Foundational → Foundation ready (T001-T016)
2. US1 + US2 → MVP functional (T017-T031)
3. CLI Integration → MVP usable (T049-T050)
4. **Deploy MVP** - Users can control devices
5. US3 → State awareness (T032-T038)
6. **Deploy v1.1** - Redundancy detection
7. US4 → Feedback (T039-T042)
8. **Deploy v1.2** - User-friendly messages
9. Integration Testing + Documentation (T043-T058)
10. **Deploy v1.0 Final** - Production ready

### Parallel Team Strategy

With 3 developers after Foundational phase complete:

- **Developer A**: US1 (T017-T023) - SLM integration
- **Developer B**: US2 (T024-T031) - MQTT integration
- **Developer C**: Unit tests (T044-T048) - Test infrastructure

After US1 + US2 complete:

- **Developer A**: US3 (T032-T038) - State awareness
- **Developer B**: US4 (T039-T042) - Feedback
- **Developer C**: CLI Integration (T049-T052)

---

## Test-First Workflow (TDD)

### For Each User Story

1. **Write Contract Tests** (T017, T024, T032, T039)
   - Define expected interfaces
   - Write tests that check inputs/outputs
   - **VERIFY TESTS FAIL** (no implementation yet)

2. **Write Integration Tests** (T018, T025, T033)
   - Define end-to-end user scenarios
   - Write tests for acceptance criteria
   - **VERIFY TESTS FAIL**

3. **Implement Core Functionality**
   - Write minimum code to pass contract tests
   - Refactor while keeping tests green
   - Add implementation details

4. **Verify Integration Tests Pass**
   - All acceptance scenarios working
   - Performance targets met
   - Error handling validated

5. **Write Unit Tests** (T044-T048)
   - Test edge cases and error paths
   - Test internal logic
   - Achieve 60% minimum coverage

---

## Quality Gates

Before marking feature complete:

- [ ] All contract tests passing (T017, T024, T032, T039)
- [ ] All integration tests passing (T018, T025, T033, T043)
- [ ] All unit tests passing (T044-T048)
- [ ] Test coverage ≥60%
- [ ] Performance targets met (SC-001: <3s, SC-007: <15s, NFR: <100ms publish)
- [ ] Privacy validation (FR-014: no transcription persistence)
- [ ] Security review complete (T058)
- [ ] Documentation complete (README, API docs, quickstart validated)
- [ ] CLI integration tested (manual testing with real voice + devices)
- [ ] Constitution check passing (all 7 principles upheld)

---

## Notes

- **[P]** tasks can run in parallel (different files, no shared state)
- **[Story]** labels map tasks to user stories for traceability
- TDD workflow: Write tests → Verify failure → Implement → Verify success
- MVP scope: US1 + US2 (command understanding + MQTT publishing)
- US3 and US4 are optional enhancements (state awareness + feedback)
- Privacy: Transcription must be cleared after processing (FR-014)
- Performance: Monitor SLM load time (<15s), inference time (<1s), MQTT latency (<100ms)
- MQTT QoS 1: At least once delivery with PUBACK confirmation (FR-020)
- Commit after each task or logical group of parallel tasks
- Stop at checkpoints to validate user story independence

**Total Tasks**: 58  
**MVP Tasks**: ~35 (Setup + Foundational + US1 + US2 + CLI Integration + Basic Docs)  
**Estimated MVP Effort**: 3-5 days (single developer)  
**Full Feature Effort**: 5-8 days (single developer)
