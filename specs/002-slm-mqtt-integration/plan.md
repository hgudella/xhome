# Implementation Plan: SLM Command Processing and MQTT Integration

**Branch**: `002-slm-mqtt-integration` | **Date**: 2025-12-11 | **Spec**: [spec.md](spec.md)  
**Status**: ✅ Phase 0 & Phase 1 Complete - Ready for Implementation  
**Input**: Feature specification from `/specs/002-slm-mqtt-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Process transcribed text from Feature 001 (Voice-to-Text) through the Phi-4-Mini-GGUF Small Language Model to extract command intents and parameters. Translate parsed commands into MQTT messages and publish them to a local broker for home automation device control. The system will maintain device state awareness, provide user feedback, and handle errors gracefully while ensuring all processing remains local without cloud dependencies. This feature completes the voice-to-action pipeline by adding natural language understanding and device control capabilities.

## Technical Context

**Language/Version**: Python 3.10+  
**Primary Dependencies**: llama-cpp-python (Phi-4-Mini-GGUF), paho-mqtt (MQTT client), existing dependencies from Feature 001 (torch, transformers, sounddevice, librosa)  
**Storage**: JSON/YAML device configuration file (device names → MQTT topics), no persistence of commands or state beyond in-memory cache  
**Testing**: pytest with minimum 60% code coverage  
**Target Platform**: Desktop (Windows/Linux/Mac) with network access to local MQTT broker  
**Project Type**: single (extends existing voice-to-text application)  
**Performance Goals**: <3s command processing latency, <15s SLM model load time, 90% intent accuracy, <1s feedback delivery  
**Constraints**: <4GB peak memory (both Whisper + Phi-4-Mini loaded), 0-day retention for commands/transcriptions, local-only processing (no cloud APIs), 10s SLM inference timeout  
**Scale/Scope**: 50+ device mappings, 50+ consecutive commands without degradation, multiple device types (lights, switches, thermostats)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **I. Specification-Driven** | Spec must be complete with Given-When-Then scenarios | ✅ PASS | spec.md complete with 4 user stories, 20 FRs (all clarified), acceptance scenarios defined |
| **II. Test-First (NON-NEGOTIABLE)** | Tests written before implementation | ⏳ PENDING | Will be enforced in tasks phase - tests must be created first |
| **III. Structured Planning** | Tasks organized by user story, tracked | ⏳ PENDING | Will be fulfilled in tasks.md generation |
| **IV. Independent User Stories** | Stories prioritized (P1/P2/P3) and independently testable | ✅ PASS | 2x P1 stories (command understanding, MQTT publishing), 1x P2 (state awareness), 1x P3 (feedback) - all independent |
| **V. Simplicity & YAGNI** | Implement only what's specified, justify complexity | ✅ PASS | Focused on core intent extraction and MQTT publishing - no over-engineering, out-of-scope explicit |
| **VI. Observability** | Structured logging, clear errors, text I/O | ✅ PASS | FR-013 (command logging), FR-015 (feedback), FR-020 (QoS 1 for reliability) |
| **VII. Versioning** | Semantic versioning for artifacts | ✅ PASS | Project follows semantic versioning, feature adds functionality (MINOR bump) |
| **Privacy-First Architecture** | Local processing, 0-day retention | ✅ PASS | FR-003 (local SLM), FR-014 (no command persistence), extends Feature 001 privacy model |
| **Security & Privacy** | No PII storage, secrets externalized | ✅ PASS | FR-016 (MQTT credentials configurable), device mappings in config file, no PII in logs |
| **Quality Gates** | 60% test coverage minimum | ⏳ PENDING | Will be enforced during implementation |
| **Module Architecture** | Follows defined module structure | ✅ PASS | Extends Command Router and MQTT Controller modules per constitution |

**Gate Status**: ✅ **PASS** - Proceed to Phase 0 Research

**Justifications**: None required - all applicable principles satisfied. Test-related items are appropriately deferred to implementation phase. This feature extends the existing architecture without introducing new complexity or violations.

## Project Structure

### Documentation (this feature)

```text
specs/002-slm-mqtt-integration/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
│   ├── slm_interface.md       # Phi-4-Mini-GGUF integration contract
│   ├── mqtt_publisher.md      # MQTT client interface contract
│   └── command_router.md      # Command extraction and routing contract
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/
├── audio/
│   ├── __init__.py
│   ├── capture.py       # [EXISTING] AudioStream implementation
│   ├── buffer.py        # [EXISTING] AudioBuffer implementation
│   ├── continuous.py    # [EXISTING] Continuous listening mode
│   └── vad.py           # [EXISTING] Voice Activity Detection
├── transcription/
│   ├── __init__.py
│   ├── whisper_engine.py  # [EXISTING] Tiny Whisper model integration
│   └── transcriber.py     # [EXISTING] Transcription service
├── command/             # [NEW] Command processing module
│   ├── __init__.py
│   ├── slm_engine.py    # Phi-4-Mini-GGUF model integration and prompt management
│   ├── parser.py        # Intent extraction and command parsing
│   └── models.py        # Command, CommandSession data structures
├── devices/             # [NEW] Device and MQTT management
│   ├── __init__.py
│   ├── mapping.py       # DeviceMapping configuration loader
│   ├── mqtt_client.py   # MQTT publisher/subscriber implementation
│   └── state.py         # DeviceState tracking and cache
├── session/
│   ├── __init__.py
│   └── voice_session.py # [EXISTING] VoiceSession management
├── utils/
│   ├── __init__.py
│   ├── logging.py       # [EXISTING] Privacy-aware logging
│   ├── config.py        # [EXISTING] Configuration management
│   └── exceptions.py    # [NEW] Custom exceptions for command processing
└── main.py              # [MODIFIED] Application entry point - integrate command pipeline

tests/
├── contract/
│   ├── test_audio_buffer_contract.py    # [EXISTING]
│   ├── test_audio_stream_contract.py    # [EXISTING]
│   ├── test_transcription_contract.py   # [EXISTING]
│   ├── test_vad_contract.py             # [EXISTING]
│   ├── test_slm_engine_contract.py      # [NEW] Phi-4-Mini interface verification
│   ├── test_mqtt_client_contract.py     # [NEW] MQTT client interface verification
│   └── test_command_parser_contract.py  # [NEW] Command extraction contract
├── integration/
│   ├── test_audio_capture_pipeline.py   # [EXISTING]
│   ├── test_audio_to_text_pipeline.py   # [EXISTING]
│   ├── test_continuous_listening.py     # [EXISTING]
│   ├── test_text_to_command_pipeline.py # [NEW] Transcription → Command → MQTT
│   └── test_full_voice_to_mqtt.py       # [NEW] End-to-end voice → MQTT
└── unit/
    ├── test_audio_buffer.py             # [EXISTING]
    ├── test_audio_capture.py            # [EXISTING]
    ├── test_transcription.py            # [EXISTING]
    ├── test_vad.py                      # [EXISTING]
    ├── test_whisper_engine.py           # [EXISTING]
    ├── test_slm_engine.py               # [NEW] SLM model loading and inference
    ├── test_command_parser.py           # [NEW] Intent extraction logic
    ├── test_device_mapping.py           # [NEW] Configuration loading
    ├── test_mqtt_client.py              # [NEW] MQTT operations
    └── test_device_state.py             # [NEW] State tracking

config/                  # [NEW] Configuration directory
├── devices.yaml         # Device name → MQTT topic mappings
└── devices.yaml.example # Example configuration template

logs/                    # Runtime logs directory (gitignored)
requirements.txt         # [MODIFIED] Add llama-cpp-python, paho-mqtt
.env.example            # [MODIFIED] Add MQTT broker settings
README.md               # [MODIFIED] Update with command processing features
```

**Structure Decision**: Extending the existing **Single Project** structure with two new top-level modules:
- `command/` - SLM integration and command parsing (natural language → structured commands)
- `devices/` - Device mapping and MQTT communication (structured commands → MQTT messages)

This maintains clean separation of concerns while integrating with the existing `audio/` and `transcription/` modules. The `session/` module will be extended to track the full voice-to-MQTT lifecycle.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations - this section intentionally left empty.

---

## Post-Design Constitution Re-evaluation

**Date**: 2025-12-11  
**Phase**: Phase 1 Complete (Research, Data Model, Contracts, Quickstart)

### Constitution Compliance Review

**I. Specification-Driven Development**: ✅ PASS
- Specification complete with 4 user stories, 20 FRs, all clarified (MQTT QoS 1)
- Success criteria defined and testable
- Version 1.0 maintained in spec.md

**II. Test-First Development (NON-NEGOTIABLE)**: ✅ PASS
- All three contracts specify comprehensive testing requirements:
  * `slm_interface.md` - Contract tests, unit tests, integration tests defined
  * `mqtt_publisher.md` - Contract tests with mock broker, integration tests specified
  * `command_router.md` - Contract tests, unit tests, pipeline integration tests specified
- Test structure added to project structure (tests/contract/, tests/unit/)
- TDD workflow will be enforced in implementation phase (Phase 2)

**III. Structured Planning & Task Decomposition**: ✅ PASS
- Implementation plan includes Technical Context, Project Structure, Complexity Tracking
- Research.md resolves all unknowns before implementation
- Data model defines clear entity relationships and validation rules
- Contracts provide testable interfaces for each component
- Next phase: tasks.md will decompose into actionable implementation tasks

**IV. Independent User Stories**: ✅ PASS
- 4 user stories prioritized: US1 (P1), US2 (P1), US3 (P2), US4 (P3)
- Each story independently testable:
  * US1: Text input → Command extraction (no US2 dependency)
  * US2: Command → MQTT publish (no US3 dependency)
  * US3: State awareness (optional enhancement to US2)
  * US4: Feedback generation (optional enhancement to all)
- Incremental delivery supported (MVP = US1 + US2)

**V. Simplicity & YAGNI**: ✅ PASS
- Research.md explicitly rejects overengineered solutions:
  * No database persistence (in-memory cache sufficient)
  * No complex NLU frameworks (SLM with few-shot prompting sufficient)
  * No custom MQTT protocol (paho-mqtt standard library sufficient)
- Complexity justified only where needed:
  * State cache TTL (5 min) prevents stale data without persistence overhead
  * Retry logic (exponential backoff) ensures reliability without complex queue systems

**VI. Observability & Debuggability**: ✅ PASS
- Contracts specify structured logging requirements:
  * `slm_interface.md` - Never log transcriptions (privacy), log intent extraction timing
  * `mqtt_publisher.md` - Log connection state, publish confirmations, errors with context
  * `command_router.md` - Log pipeline stages, error mappings, user feedback
- Error handling defined with actionable user messages
- Performance instrumentation specified (<3s latency requirement)

**VII. Versioning & Breaking Changes**: ✅ PASS
- Feature spec versioned at 1.0
- Contracts define stable interfaces (SLMEngine, MQTTClient, CommandRouter)
- Configuration format (devices.yaml) versioned in schema
- Breaking changes will follow semantic versioning (MAJOR.MINOR.PATCH)

### Architecture Compliance

**Module Architecture**: ✅ PASS
- Extends existing modules without breaking changes:
  * Speech-to-Text module unchanged (Feature 001)
  * New Command Router module added (US1)
  * New MQTT Controller module added (US2)
- Voice-to-Action Pipeline extended: capture_audio → transcribe_speech → **classify_intent** → **publish_mqtt**

**Technology Stack**: ✅ PASS
- Python 3.10+ (aligned)
- Virtual environment required (enforced)
- Core dependencies extended:
  * llama-cpp-python (Phi-4-Mini-GGUF) - NEW
  * paho-mqtt (MQTT client) - NEW
  * Existing: torch, transformers, sounddevice, librosa
- Testing framework: pytest with 60% minimum coverage (planned)

**Runtime Environment**: ✅ PASS
- New environment variables added to .env.example:
  * MQTT_BROKER_HOST (default: localhost)
  * MQTT_BROKER_PORT (default: 1883)
  * SLM_MODEL_PATH (Phi-4-Mini-GGUF path)
  * SLM_TIMEOUT (10s)
- Entry point unchanged: `python main.py` (with new `--enable-commands` flag)

**Security & Privacy**: ✅ PASS
- Privacy-first architecture maintained:
  * Local SLM processing (no cloud calls)
  * 0-day retention for transcriptions and commands (data-model.md)
  * Raw audio not retained (Feature 001 compliance)
  * PII redaction in logs (contracts specify no transcription logging)
- MQTT credentials externalized to environment variables
- Device configuration in config/devices.yaml (gitignored if contains secrets)

### Quality Gates Status

1. **Constitution Check**: ✅ PASS (this evaluation)
2. **Specification Complete**: ✅ PASS (all FRs clarified)
3. **Tests Written & Failing**: ⏳ PENDING (Phase 2 - tasks.md → implementation)
4. **Implementation Complete**: ⏳ PENDING (Phase 2)
5. **Tests Passing**: ⏳ PENDING (Phase 2)
6. **Code Review Approved**: ⏳ PENDING (Phase 2)
7. **Documentation Updated**: ⏳ PENDING (Phase 2 - will update README, quickstart complete)

### Conclusion

**Phase 1 Design Compliance**: ✅ ALL PRINCIPLES PASSING

No violations detected in research, data model, contracts, or quickstart design. All constitution principles upheld. Feature is architecturally sound and ready for Phase 2 (task decomposition via `/speckit.tasks`).

**Next Step**: Generate tasks.md to break down implementation into TDD-friendly, trackable tasks.
