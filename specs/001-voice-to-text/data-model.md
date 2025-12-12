# Data Model: Voice-to-Text Transcription

**Feature**: 001-voice-to-text  
**Created**: 2025-12-11  
**Status**: Draft

## Overview

This document defines the core data entities, their attributes, relationships, and validation rules for the voice-to-text transcription feature. All entities are designed to operate entirely in-memory with zero persistence to comply with privacy requirements (0-day audio retention).

---

## Entities

### 1. AudioStream

Represents the continuous stream of audio data from the microphone input device.

#### Attributes

| Attribute | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `stream_id` | UUID | Yes | Generated | Unique identifier for this audio stream |
| `sample_rate` | int | Yes | 16000 | Audio sample rate in Hz (16kHz for Whisper) |
| `channels` | int | Yes | 1 | Number of audio channels (mono) |
| `buffer_size` | int | Yes | 1024 | Size of audio buffer in frames |
| `audio_format` | str | Yes | "int16" | Audio data format (16-bit PCM) |
| `state` | enum | Yes | "stopped" | Current state: "listening", "stopped", "error" |
| `device_index` | int | No | None | Index of audio input device (None = default) |
| `started_at` | datetime | No | None | Timestamp when stream started |
| `stopped_at` | datetime | No | None | Timestamp when stream stopped |

#### Validation Rules

- `sample_rate` MUST be between 8000 and 48000 Hz
- `channels` MUST be 1 (mono audio only)
- `buffer_size` MUST be a power of 2 (e.g., 512, 1024, 2048)
- `audio_format` MUST be "int16"
- `state` transitions: stopped → listening → stopped (or error)
- `device_index` if provided MUST reference a valid audio input device

#### State Transitions

```
[stopped] --start()--> [listening]
[listening] --stop()--> [stopped]
[listening] --error()--> [error]
[error] --reset()--> [stopped]
```

#### Relationships

- ONE AudioStream produces MANY AudioBuffer instances
- ONE AudioStream is referenced by ONE VoiceSession

---

### 2. AudioBuffer

Temporary in-memory storage for captured audio data waiting to be transcribed. This buffer is **ephemeral** and MUST be cleared immediately after transcription.

#### Attributes

| Attribute | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `buffer_id` | UUID | Yes | Generated | Unique identifier for this buffer |
| `audio_data` | numpy.ndarray | Yes | Empty | Raw audio samples (1D array of int16 values) |
| `sample_rate` | int | Yes | 16000 | Sample rate matching the source stream |
| `duration_seconds` | float | Yes | Computed | Duration of audio in seconds |
| `captured_at` | datetime | Yes | Generated | Timestamp when buffer was created |
| `frame_count` | int | Yes | Computed | Number of audio frames in buffer |
| `is_processed` | bool | Yes | False | Whether this buffer has been transcribed |

#### Validation Rules

- `audio_data` MUST be a 1D numpy array with dtype=int16
- `duration_seconds` MUST be computed as `frame_count / sample_rate`
- `frame_count` MUST equal `len(audio_data)`
- `is_processed` MUST be set to True after transcription
- Buffer MUST be cleared (zeroed) and released after `is_processed = True`
- Maximum buffer size: 30 seconds of audio (480,000 frames at 16kHz)

#### Lifecycle

1. **Creation**: Allocated when audio stream has accumulated sufficient data
2. **Population**: Filled with audio samples from AudioStream
3. **Processing**: Passed to Tiny Whisper for transcription
4. **Clearance**: Zeroed out and released from memory immediately after transcription

#### Relationships

- MANY AudioBuffer instances come from ONE AudioStream
- ONE AudioBuffer produces ONE Transcription
- ONE AudioBuffer is part of ONE VoiceSession

---

### 3. Transcription

The text output produced by Tiny Whisper after processing an AudioBuffer.

#### Attributes

| Attribute | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `transcription_id` | UUID | Yes | Generated | Unique identifier for this transcription |
| `text` | str | Yes | "" | The transcribed text from speech |
| `language` | str | No | "en" | Detected language code (ISO 639-1) |
| `confidence` | float | No | None | Confidence score if available (0.0-1.0) |
| `created_at` | datetime | Yes | Generated | Timestamp when transcription completed |
| `processing_duration_ms` | int | Yes | Measured | Time taken to transcribe in milliseconds |
| `word_count` | int | Yes | Computed | Number of words in transcription |
| `status` | enum | Yes | "pending" | Status: "pending", "completed", "failed" |
| `error_message` | str | No | None | Error details if status is "failed" |

#### Validation Rules

- `text` length MUST be between 0 and 10000 characters
- `confidence` if provided MUST be between 0.0 and 1.0
- `processing_duration_ms` MUST be a positive integer
- `word_count` MUST be computed as `len(text.split())`
- `status` transitions: pending → completed (or failed)
- `error_message` MUST only be set when status is "failed"

#### State Transitions

```
[pending] --transcribe()--> [completed]
[pending] --error()--> [failed]
```

#### Relationships

- ONE Transcription is produced by ONE AudioBuffer
- ONE Transcription is part of ONE VoiceSession

---

### 4. VoiceSession

Represents a single voice interaction from audio capture start to transcription completion. Used for tracking, logging, and debugging.

#### Attributes

| Attribute | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `session_id` | UUID | Yes | Generated | Unique identifier for this session |
| `stream_id` | UUID | Yes | Required | Reference to AudioStream used |
| `buffer_id` | UUID | No | None | Reference to AudioBuffer processed |
| `transcription_id` | UUID | No | None | Reference to Transcription produced |
| `started_at` | datetime | Yes | Generated | Session start timestamp |
| `ended_at` | datetime | No | None | Session end timestamp |
| `audio_duration_seconds` | float | No | None | Total audio captured in session |
| `total_duration_ms` | int | No | None | End-to-end session duration in ms |
| `status` | enum | Yes | "active" | Status: "active", "completed", "failed" |
| `error_type` | str | No | None | Error type if failed (e.g., "mic_error", "model_error") |
| `error_message` | str | No | None | Detailed error message if failed |

#### Validation Rules

- `stream_id` MUST reference an existing AudioStream
- `buffer_id` if set MUST reference a valid AudioBuffer
- `transcription_id` if set MUST reference a valid Transcription
- `ended_at` MUST be greater than `started_at`
- `audio_duration_seconds` MUST be positive if set
- `total_duration_ms` MUST be computed as `(ended_at - started_at).total_seconds() * 1000`
- `status` transitions: active → completed (or failed)
- `error_type` and `error_message` MUST only be set when status is "failed"

#### State Transitions

```
[active] --complete()--> [completed]
[active] --fail()--> [failed]
```

#### Relationships

- ONE VoiceSession references ONE AudioStream
- ONE VoiceSession references ONE AudioBuffer
- ONE VoiceSession references ONE Transcription

---

## Entity Relationships Diagram

```
AudioStream (1) ──< (n) AudioBuffer
     │                      │
     │                      │
     │                      ▼
     │                 Transcription (1)
     │                      
     ▼                      
VoiceSession ──────────────▶ references all entities
```

**Cardinalities**:
- One AudioStream produces many AudioBuffer instances over time
- One AudioBuffer produces exactly one Transcription
- One VoiceSession ties together one of each entity for tracking

---

## Privacy & Data Lifecycle

### Memory-Only Storage

ALL entities MUST reside in memory only. No entity data shall be persisted to disk except for:
- **Logging**: Metadata only (timestamps, durations, session IDs, status codes)
- **Prohibited**: Audio data, transcription text, error messages containing PII

### Data Clearance

1. **AudioBuffer**: Zeroed out and released immediately after transcription
2. **Transcription**: Cleared after being consumed by downstream modules
3. **VoiceSession**: Retained in memory for duration of continuous listening, then cleared
4. **AudioStream**: Cleared when stream is stopped

### Maximum Retention

- **AudioBuffer**: 0 seconds after `is_processed = True`
- **Transcription**: Maximum 60 seconds (time to process command)
- **VoiceSession**: Maximum 5 minutes (during continuous operation)

---

## Implementation Notes

### Technology Stack

- **numpy**: For `AudioBuffer.audio_data` (ndarray storage)
- **datetime**: For all timestamp attributes
- **uuid**: For all ID generation
- **enum**: For state management (AudioStream.state, Transcription.status, VoiceSession.status)

### Memory Management

- Use Python's `gc.collect()` after clearing buffers
- Implement explicit `clear()` methods on all entities
- Monitor memory usage via `psutil` during continuous operation

### Thread Safety

- AudioStream and AudioBuffer operations will be accessed from audio callback threads
- Implement thread-safe queues for passing buffers to transcription
- Use locks for state transitions on shared entities

---

## Validation Implementation

Each entity MUST implement a `validate()` method that checks all validation rules and raises `ValidationError` if any rule is violated. This ensures data integrity at entity boundaries.

Example validation:
```python
def validate(self):
    if not (8000 <= self.sample_rate <= 48000):
        raise ValidationError(f"Invalid sample_rate: {self.sample_rate}")
    if self.state not in ["listening", "stopped", "error"]:
        raise ValidationError(f"Invalid state: {self.state}")
```

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-11 | Initial data model definition |
