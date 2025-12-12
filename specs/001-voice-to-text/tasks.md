# Tasks: Voice-to-Text Transcription

**Input**: Design documents from `/specs/001-voice-to-text/`  
**Prerequisites**: plan.md ✅, spec.md ✅, research.md ✅, data-model.md ✅

**Tests**: Tests are included per Test-First principle (NON-NEGOTIABLE per constitution)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- **Single project**: `src/`, `tests/` at repository root
- Paths follow structure defined in plan.md

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and basic structure

- [ ] T001 Create project directory structure (src/, tests/, logs/)
- [ ] T002 Initialize Python project with requirements.txt (torch>=2.0.0, transformers>=4.30.0, sounddevice>=0.4.6, librosa>=0.10.0, numpy>=1.24.0, pytest>=7.4.0, pytest-cov>=4.1.0, python-dotenv>=1.0.0)
- [ ] T003 [P] Create .env.example with configuration template (AUDIO_SAMPLE_RATE, AUDIO_CHANNELS, AUDIO_BUFFER_SIZE, WHISPER_MODEL_NAME, WHISPER_DEVICE, LOG_LEVEL, AUDIO_RETENTION_SECONDS)
- [ ] T004 [P] Create .gitignore for Python project (venv/, .env, logs/, __pycache__/, *.pyc, .pytest_cache/)
- [ ] T005 [P] Create README.md with project overview and quickstart reference
- [ ] T006 [P] Create all __init__.py files (src/, src/audio/, src/transcription/, src/session/, src/utils/)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core infrastructure that MUST be complete before ANY user story can be implemented

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [ ] T007 Implement configuration loader in src/utils/config.py (load from .env with validation)
- [ ] T008 [P] Implement privacy-aware logging utility in src/utils/logging.py (metadata only, no audio/text, structured format)
- [ ] T009 [P] Create base exception classes in src/utils/exceptions.py (AudioCaptureError, TranscriptionError, SessionError, ValidationError)
- [ ] T010 Download and verify Whisper model availability (openai/whisper-base ~150MB or openai/whisper-tiny ~39MB) via transformers library and validate all required dependencies (torch>=2.0.0, transformers>=4.30.0, sounddevice>=0.4.6, librosa>=0.10.0) are installed with compatible versions

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Real-time Voice Capture (Priority: P1) 🎯 MVP

**Goal**: Users can speak into their microphone, and the system continuously listens and captures audio in real-time.

**Independent Test**: Audio data is captured from the microphone and audio levels respond to voice input. System continues listening during silence without errors.

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T011 [P] [US1] Contract test for AudioStream interface in tests/contract/test_audio_stream_contract.py (verify start/stop/state transitions)
- [ ] T012 [P] [US1] Contract test for AudioBuffer interface in tests/contract/test_audio_buffer_contract.py (verify buffer operations and clearance)
- [ ] T013 [P] [US1] Unit test for AudioStream in tests/unit/test_audio_capture.py (test microphone initialization, state management, error handling, device selection)
- [ ] T014 [P] [US1] Unit test for AudioBuffer in tests/unit/test_audio_buffer.py (test buffer creation, population, validation, clearance, privacy compliance)
- [ ] T015 [US1] Integration test for audio capture pipeline in tests/integration/test_audio_capture_pipeline.py (end-to-end: mic → stream → buffer)

### Implementation for User Story 1

- [ ] T016 [P] [US1] Create AudioStream model in src/audio/capture.py (attributes: stream_id, sample_rate, channels, buffer_size, audio_format, state, device_index, started_at, stopped_at)
- [ ] T017 [P] [US1] Create AudioBuffer model in src/audio/buffer.py (attributes: buffer_id, audio_data, sample_rate, duration_seconds, captured_at, frame_count, is_processed)
- [ ] T018 [US1] Implement AudioStream.start() method using sounddevice with callback-based streaming at 16kHz
- [ ] T019 [US1] Implement AudioStream.stop() method with graceful shutdown and state transition
- [ ] T020 [US1] Implement AudioBuffer.create_from_stream() method to populate buffer from audio stream
- [ ] T021 [US1] Implement AudioBuffer.clear() method with explicit zeroing and memory release (privacy requirement)
- [ ] T022 [US1] Add validation methods to AudioStream (validate sample_rate 8000-48000Hz, channels=1, buffer_size power of 2)
- [ ] T023 [US1] Add validation methods to AudioBuffer (validate audio_data dtype=int16, max duration 30s)
- [ ] T024 [US1] Implement state transition logic for AudioStream (stopped → listening → stopped/error)
- [ ] T025 [US1] Add error handling for microphone access denial and device failures
- [ ] T026 [US1] Add privacy-aware logging for audio capture events (metadata only: session_id, state, duration, no audio data)

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently

---

## Phase 4: User Story 2 - Speech-to-Text Conversion (Priority: P1) 🎯 MVP

**Goal**: The system processes captured audio through the Tiny Whisper model and converts speech into accurate text transcription.

**Independent Test**: Audio samples (or live speech) are provided and accurate text transcriptions are produced. System handles errors gracefully.

### Tests for User Story 2 ⚠️

- [ ] T027 [P] [US2] Contract test for Whisper model interface in tests/contract/test_transcription_contract.py (verify model input/output format, error handling)
- [ ] T028 [P] [US2] Unit test for WhisperEngine in tests/unit/test_whisper_engine.py (test model loading, inference, confidence scoring, language detection, error cases)
- [ ] T029 [P] [US2] Unit test for Transcription model in tests/unit/test_transcription.py (test validation, state transitions, word count computation)
- [ ] T030 [US2] Integration test for audio-to-text pipeline in tests/integration/test_audio_to_text_pipeline.py (end-to-end: AudioBuffer → Transcription)

### Implementation for User Story 2

- [ ] T031 [P] [US2] Create Transcription model in src/transcription/transcriber.py (attributes: transcription_id, text, language, confidence, created_at, processing_duration_ms, word_count, status, error_message)
- [ ] T032 [US2] Implement WhisperEngine in src/transcription/whisper_engine.py (load model, configure device CPU/GPU)
- [ ] T033 [US2] Implement WhisperEngine.transcribe() method to process AudioBuffer and return Transcription
- [ ] T034 [US2] Implement audio preprocessing in WhisperEngine using librosa (resampling, normalization per research.md R4)
- [ ] T035 [US2] Add validation methods to Transcription (text length 0-10000 chars, confidence 0.0-1.0, word_count computation)
- [ ] T036 [US2] Implement state transition logic for Transcription (pending → completed/failed)
- [ ] T037 [US2] Add error handling for model failures, poor audio quality, and out-of-memory conditions
- [ ] T038 [US2] Implement graceful degradation when audio quality is very poor (log error, return empty transcription with status=failed)
- [ ] T039 [US2] Add privacy-aware logging for transcription events (metadata only: transcription_id, duration_ms, word_count, status, no text content)
- [ ] T040 [US2] Integrate AudioBuffer clearance after transcription completes (call buffer.clear() immediately)

**Checkpoint**: At this point, User Stories 1 AND 2 should both work independently (MVP complete - audio capture + transcription)

---

## Phase 5: User Story 3 - Continuous Listening Mode (Priority: P2)

**Goal**: The system operates in a continuous listening mode where it automatically processes voice input without requiring manual activation for each command.

**Independent Test**: System runs and multiple commands can be spoken in sequence without manual intervention. System automatically resumes listening after each transcription.

### Tests for User Story 3 ⚠️

- [ ] T041 [P] [US3] Unit test for VoiceSession in tests/unit/test_voice_session.py (test session lifecycle, error tracking, duration computation, state transitions)
- [ ] T042 [US3] Integration test for continuous listening in tests/integration/test_continuous_listening.py (multi-command sequence without manual start/stop)

### Implementation for User Story 3

- [ ] T043 [US3] Create VoiceSession model in src/session/voice_session.py (attributes: session_id, stream_id, buffer_id, transcription_id, started_at, ended_at, audio_duration_seconds, total_duration_ms, status, error_type, error_message)
- [ ] T044 [US3] Implement VoiceSession lifecycle management (create, start, complete, fail, track references to AudioStream/AudioBuffer/Transcription)
- [ ] T045 [US3] Add validation methods to VoiceSession (validate timestamps, duration calculations, entity references)
- [ ] T046 [US3] Implement continuous listening coordinator in src/session/voice_session.py (auto-resume after transcription)
- [ ] T047 [US3] Add session cleanup logic to clear AudioBuffer and Transcription after processing (privacy requirement)
- [ ] T048 [US3] Implement maximum retention enforcement (AudioBuffer: 0s after processing, Transcription: max 60s, VoiceSession: max 5 minutes per data-model.md)
- [ ] T049 [US3] Add memory leak prevention (gc.collect() after buffer clearance)
- [ ] T050 [US3] Add privacy-aware logging for session events (metadata only: session_id, durations, status, no audio/text)
- [ ] T051 [US3] Implement continuous mode loop with automatic restart after transcription completion

**Checkpoint**: All user stories (P1 + P2) should now be independently functional

---

## Phase 6: Application Integration & Entry Point

**Purpose**: Tie all components together in a runnable application

- [ ] T052 Implement main application entry point in src/main.py
- [ ] T053 Add command-line argument parsing in src/main.py (--mode continuous|manual, --device-index, --config-file)
- [ ] T054 Implement graceful shutdown handler (Ctrl+C) to stop audio stream and clean up resources
- [ ] T055 Add startup sequence (load config → initialize logging → load Whisper model → start audio stream)
- [ ] T056 Implement main execution loop coordinating AudioStream → AudioBuffer → Transcription → VoiceSession
- [ ] T057 Add console output for transcriptions (display text with timestamp)
- [ ] T058 Verify startup time <10s per success criteria SC-006
- [ ] T059 Verify transcription latency <3s per success criteria SC-001

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Improvements that affect multiple user stories

- [ ] T060 [P] Add comprehensive docstrings to all classes and methods following Google style
- [ ] T061 [P] Create developer documentation in docs/ (architecture.md, api-reference.md)
- [ ] T062 Run full test suite and verify 60% minimum coverage per constitution
- [ ] T063 Verify success criteria SC-002 (85% word accuracy for clear English speech)
- [ ] T064 Verify success criteria SC-003 (no network calls - inspect network traffic)
- [ ] T065 Verify success criteria SC-004 (30 min continuous operation without memory leaks - use memory profiler)
- [ ] T066 Verify success criteria SC-005 (90% transcription success rate with good audio quality)
- [ ] T067 Verify success criteria SC-007 (no audio persistence - inspect memory and filesystem)
- [ ] T068 [P] Performance optimization: Reduce model loading time if >10s
- [ ] T069 [P] Performance optimization: Optimize buffer size for latency vs accuracy
- [ ] T070 Run quickstart.md validation (follow setup steps, verify all commands work)
- [ ] T071 Security review: Verify no PII logging, secrets externalized to .env
- [ ] T072 Code cleanup: Remove debug code, unused imports, TODO comments

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational completion
- **User Story 2 (Phase 4)**: Depends on Foundational completion AND User Story 1 (needs AudioBuffer from US1)
- **User Story 3 (Phase 5)**: Depends on User Story 1 AND User Story 2 (coordinates capture + transcription)
- **Application Integration (Phase 6)**: Depends on User Story 1 AND User Story 2 (minimum for MVP)
- **Polish (Phase 7)**: Depends on all user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational (Phase 2) - No dependencies on other stories
- **User Story 2 (P1)**: DEPENDS on User Story 1 - Needs AudioBuffer entity from US1
- **User Story 3 (P2)**: DEPENDS on User Story 1 AND 2 - Coordinates both to enable continuous mode

**NOTE**: Unlike typical independent user stories, this feature has sequential dependencies because:
- US2 (transcription) requires US1 (audio capture) to have something to transcribe
- US3 (continuous mode) requires US1+US2 to coordinate them in a loop

### Within Each User Story

- Tests MUST be written and FAIL before implementation (Test-First principle)
- Models before services
- Services before integration
- Core implementation before error handling
- Story complete before moving to next priority

### Parallel Opportunities

**Phase 1 (Setup)**: T003, T004, T005, T006 can run in parallel

**Phase 2 (Foundational)**: T008, T009 can run in parallel (T007 must complete first, T010 can run anytime)

**Phase 3 (US1) Tests**: T011, T012, T013, T014 can ALL run in parallel (write tests together)

**Phase 3 (US1) Models**: T016, T017 can run in parallel (different files, independent entities)

**Phase 4 (US2) Tests**: T027, T028, T029 can ALL run in parallel (write tests together)

**Phase 4 (US2) Implementation**: T031, T032 can run in parallel (Transcription model and WhisperEngine are independent)

**Phase 5 (US3) Tests**: T041, T042 can run in parallel (write tests together)

**Phase 7 (Polish)**: T060, T061, T068, T069, T071 can all run in parallel (different concerns)

---

## Parallel Example: User Story 1 (Audio Capture)

```bash
# Step 1: Write all tests in parallel (Test-First)
# Developer 1:
git checkout -b us1-audio-stream-tests
# Create T011, T013 (AudioStream contract + unit tests)

# Developer 2:
git checkout -b us1-audio-buffer-tests
# Create T012, T014 (AudioBuffer contract + unit tests)

# Developer 3:
git checkout -b us1-integration-test
# Create T015 (integration test)

# All tests should FAIL at this point (red)

# Step 2: Implement models in parallel
# Developer 1:
git checkout -b us1-audio-stream-impl
# Create T016, T018, T019, T022, T024 (AudioStream implementation)

# Developer 2:
git checkout -b us1-audio-buffer-impl
# Create T017, T020, T021, T023 (AudioBuffer implementation)

# Step 3: Add cross-cutting concerns sequentially
# Complete T025 (error handling)
# Complete T026 (logging)

# Result: User Story 1 complete, all tests green
```

---

## MVP Definition

**Minimum Viable Product = User Story 1 + User Story 2**

This delivers the core value proposition:
- ✅ Audio capture from microphone (US1)
- ✅ Speech-to-text transcription (US2)
- ✅ Privacy compliance (0-day retention)
- ✅ Local processing (no cloud)

**NOT included in MVP**:
- ❌ Continuous listening mode (US3) - Nice to have, but manual start/stop is acceptable for MVP

**MVP Implementation Path**:
1. Complete Phase 1 (Setup) - T001 to T006
2. Complete Phase 2 (Foundational) - T007 to T010
3. Complete Phase 3 (US1) - T011 to T026
4. Complete Phase 4 (US2) - T027 to T040
5. Complete Phase 6 (Integration) - T052 to T059 (partial - skip continuous mode)
6. Validate MVP: Can speak into mic, see transcription output

**Total MVP Tasks**: 49 tasks (excluding US3 and Polish)

---

## Summary

- **Total Tasks**: 72
- **User Story 1 (P1)**: 16 tasks (5 tests + 11 implementation)
- **User Story 2 (P1)**: 14 tasks (4 tests + 10 implementation)
- **User Story 3 (P2)**: 9 tasks (2 tests + 7 implementation)
- **Setup + Foundational**: 10 tasks
- **Integration**: 8 tasks
- **Polish**: 13 tasks
- **Parallel Opportunities**: 20+ tasks can be parallelized within phases
- **MVP Scope**: User Story 1 + User Story 2 (49 tasks)
- **Estimated MVP Completion**: 3-4 developer days with 2 developers working in parallel

---

## Format Validation ✅

All tasks follow the required checklist format:
- ✅ Checkbox `- [ ]` present on every task
- ✅ Sequential Task IDs (T001 - T072)
- ✅ [P] markers on parallelizable tasks
- ✅ [Story] labels on user story tasks (US1, US2, US3)
- ✅ Exact file paths in descriptions
- ✅ Clear, actionable descriptions
