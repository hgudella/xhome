# Feature Specification: Voice-to-Text Transcription

**Feature Branch**: `001-voice-to-text`  
**Created**: 2025-12-11  
**Status**: Draft  
**Input**: User description: "Add voice command processing for controlling lights via MQTT - For initial phase lets implement a feature where we listen to user voice from a mic and process audio stream from mic with tiny whisper LLM and convert into text"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Real-time Voice Capture (Priority: P1)

The user speaks into their microphone, and the system continuously listens and captures audio in real-time. This is the foundation for all voice interaction functionality.

**Why this priority**: This is the most critical capability - without audio capture, no other voice features can work. It establishes the basic input mechanism for the entire voice control system.

**Independent Test**: Can be fully tested by verifying that audio data is being captured from the microphone and audio levels respond to voice input. Delivers the core value of "the system hears me."

**Acceptance Scenarios**:

1. **Given** the system is running, **When** the user speaks into the microphone, **Then** audio data is captured and buffered in memory
2. **Given** the system is listening, **When** there is silence, **Then** the system continues listening without errors
3. **Given** audio is being captured, **When** the user stops speaking, **Then** the audio buffer is ready for processing
4. **Given** multiple audio input devices are available, **When** the system starts, **Then** the default or configured microphone is selected

---

### User Story 2 - Speech-to-Text Conversion (Priority: P1)

The system processes captured audio through the Whisper base model (openai/whisper-base) and converts speech into accurate text transcription. This enables the user to see what the system understood.

**Why this priority**: This is equally critical as audio capture - it's the second half of the MVP. Without transcription, captured audio has no value for command processing.

**Independent Test**: Can be fully tested by providing audio samples (or live speech) and verifying that accurate text transcriptions are produced. Delivers the value of "the system understands what I said."

**Acceptance Scenarios**:

1. **Given** audio has been captured, **When** the audio is sent to Whisper, **Then** text transcription is returned
2. **Given** clear speech is provided, **When** transcription occurs, **Then** the text accurately reflects the spoken words
3. **Given** audio contains ambient noise, **When** transcription occurs, **Then** the system still produces recognizable text for clear speech
4. **Given** transcription is in progress, **When** processing completes, **Then** the text is available for downstream use (command routing, display, etc.)
5. **Given** audio quality is very poor, **When** transcription attempts, **Then** the system handles the error gracefully and logs the issue

---

### User Story 3 - Continuous Listening Mode (Priority: P2)

The system operates in a continuous listening mode where it automatically processes voice input without requiring manual activation for each command. This provides a seamless hands-free experience.

**Why this priority**: While important for user experience, this is an enhancement over the core capture-and-transcribe functionality. The system can function with manual start/stop controls initially.

**Independent Test**: Can be fully tested by running the system and speaking multiple commands in sequence without manual intervention. Delivers the value of "I can speak naturally without pressing buttons."

**Acceptance Scenarios**:

1. **Given** the system is in continuous mode, **When** audio capture completes, **Then** the system automatically begins listening for the next input
2. **Given** continuous listening is active, **When** a transcription is processed, **Then** the system immediately resumes listening
3. **Given** the user speaks multiple commands, **When** each is transcribed, **Then** they are processed independently without interruption to listening

---

### Edge Cases

- What happens when no microphone is available or accessible?
- How does the system handle extremely loud or distorted audio input?
- What happens if the Whisper model fails to load or crashes during transcription?
- How does the system behave when multiple people speak simultaneously?
- What happens when the user speaks in a language not supported by the model?
- How does the system handle very long continuous speech (memory constraints)?
- What happens when audio input device is disconnected while listening?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST capture audio input from the default system microphone
- **FR-002**: System MUST support WAV audio format for processing
- **FR-003**: System MUST use Whisper model (openai/whisper-base or openai/whisper-tiny) for local speech-to-text inference
- **FR-004**: System MUST process audio entirely locally without any cloud API calls
- **FR-005**: System MUST convert captured audio to text transcription
- **FR-006**: System MUST handle continuous audio streaming from the microphone
- **FR-007**: System MUST buffer audio data in memory for processing
- **FR-008**: System MUST discard audio data immediately after transcription (0-day retention per constitution)
- **FR-009**: System MUST log transcription events without storing audio or full transcription text (privacy requirement)
- **FR-010**: System MUST provide clear error messages when microphone access is denied
- **FR-011**: System MUST handle microphone initialization failures gracefully
- **FR-012**: System MUST allow manual start/stop of voice capture
- **FR-013**: System MUST provide transcribed text output in plain text format
- **FR-014**: System MUST support configurable audio sample rate and buffer size
- **FR-015**: System MUST validate that required dependencies (torch, transformers, sounddevice, librosa) are available at startup. **Given** a required dependency is missing **When** the system starts **Then** display clear error message naming the missing dependency and required version **AND** exit with non-zero exit code **AND** log the validation failure. **Given** dependency versions are incompatible **When** validation runs **Then** display warning with current vs required versions.

### Key Entities

- **AudioStream**: Represents the continuous stream of audio data from the microphone. Attributes include sample rate, buffer size, audio format (WAV), and current recording state (listening/stopped).

- **AudioBuffer**: Temporary in-memory storage for captured audio data waiting to be transcribed. Contains raw audio samples, duration, and timestamp. Must be cleared after processing to comply with privacy requirements.

- **Transcription**: The text output produced by the Whisper model. Attributes include the transcribed text string, confidence score (if available), timestamp, and processing duration.

- **VoiceSession**: Represents a single voice interaction from start to transcription completion. Tracks session ID, start time, end time, audio duration, transcription result, and any errors encountered.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Users can speak into the microphone and see transcribed text within 3 seconds of finishing speaking
- **SC-002**: System accurately transcribes clear speech with at least 85% word accuracy for English language input (measured using Word Error Rate calculation: WER = (substitutions + deletions + insertions) / total_reference_words, where accuracy = 1 - WER)
- **SC-003**: System processes audio locally without any network calls to external services
- **SC-004**: System handles continuous operation for at least 30 minutes without memory leaks or performance degradation
- **SC-005**: 90% of transcription attempts complete successfully when audio quality is good (clear speech, minimal background noise)
- **SC-006**: System startup completes within 10 seconds including model loading
- **SC-007**: No audio data persists in storage after transcription (verified through memory inspection and file system checks)

## Assumptions *(if applicable)*

- The target environment has Python 3.10+ installed with access to create virtual environments
- The system has a functional microphone with appropriate permissions granted
- The user's hardware can support Tiny Whisper model inference (CPU or GPU)
- English is the primary language for initial implementation (model supports this)
- Audio input quality is reasonable (not extremely noisy environments)
- The user has approximately 1-2 GB of RAM available for model loading and inference

## Out of Scope *(if applicable)*

The following items are explicitly excluded from this feature:

- Command interpretation and intent classification (this is a future feature)
- MQTT message publishing (this is a future feature) 
- Light control functionality (this is a future feature)
- Multi-language support beyond what Tiny Whisper provides by default
- Voice activity detection (VAD) for automatic start/stop
- Audio preprocessing or enhancement (noise reduction, echo cancellation)
- Speaker identification or voice authentication
- Audio playback or text-to-speech capabilities
- Graphical user interface - this phase focuses on core functionality
- Configuration UI - settings will be environment variables or config files

## Dependencies *(if applicable)*

- **torch**: Required for running the Tiny Whisper model
- **transformers**: Provides access to the Hugging Face Tiny Whisper implementation
- **sounddevice**: Handles microphone audio capture
- **librosa**: Audio processing and format conversion utilities
- **Python 3.10+**: Runtime environment requirement

## Non-Functional Requirements *(if applicable)*

- **Performance**: Transcription latency should not exceed 3 seconds for typical 5-second voice clips
- **Reliability**: System should handle at least 100 consecutive transcriptions without failure
- **Resource Usage**: Peak memory usage should not exceed 2 GB during normal operation
- **Privacy**: Zero persistence of audio data; all processing must be ephemeral and in-memory only
- **Logging**: All logs must exclude audio content and transcription text; log only metadata (timestamps, durations, success/failure)
- **Error Handling**: All errors must be caught and logged; system should recover gracefully without crashing
