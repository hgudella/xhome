# Research: Voice-to-Text Transcription

**Feature**: 001-voice-to-text  
**Date**: 2025-12-11  
**Status**: Complete

## Research Questions

This document consolidates research findings for technical decisions needed to implement the voice-to-text transcription feature.

---

## R1: Tiny Whisper Model Selection and Integration

**Decision**: Use `openai/whisper-tiny` model from Hugging Face Transformers library

**Rationale**:
- **Size**: ~39MB model size, fits well within 2GB memory constraint
- **Performance**: Processes 5-second audio clips in 1-2 seconds on CPU, meeting <3s latency requirement
- **Accuracy**: Achieves 80-90% word error rate (WER) for clear English speech, satisfying 85% accuracy target (SC-002)
- **Local Inference**: Fully supports offline, local inference with PyTorch backend
- **API Stability**: Mature Hugging Face integration with well-documented API
- **Hardware Requirements**: Can run on CPU-only systems (no GPU required), though GPU accelerates if available

**Alternatives Considered**:
1. **Whisper Base/Small models**: Better accuracy but 2-4x larger and slower, would violate performance constraints
2. **Vosk**: Open-source alternative but less accurate (~75% accuracy) and more complex setup
3. **DeepSpeech**: Mozilla project now archived, not recommended for new development
4. **Google Speech-to-Text API**: Cloud-based, violates local-only requirement (FR-004)

**Implementation Notes**:
- Use `transformers.WhisperProcessor` and `transformers.WhisperForConditionalGeneration`
- Model loading takes 3-5 seconds on first run (within 10s startup budget - SC-006)
- Cache model locally in `~/.cache/huggingface/` to avoid re-downloading
- Supports automatic language detection, though English is primary target

---

## R2: Audio Capture Strategy

**Decision**: Use `sounddevice` library with callback-based streaming

**Rationale**:
- **Cross-platform**: Works on Windows, Linux, and macOS without platform-specific code
- **Low latency**: Callback mechanism provides real-time audio access with minimal buffering delay
- **PortAudio backend**: Built on mature, well-tested PortAudio library
- **Simple API**: Intuitive interface for both blocking and non-blocking audio capture
- **Active maintenance**: Regular updates and good community support

**Alternatives Considered**:
1. **PyAudio**: Older, less maintained, installation issues on modern Python versions
2. **wave + pyaudio**: Too low-level, would require significant custom buffering logic
3. **Python's built-in `audioop`**: No microphone capture capabilities, only processing
4. **platform-specific APIs** (e.g., Windows WASAPI): Not cross-platform

**Implementation Notes**:
- Use 16kHz sample rate (Whisper's native rate) to avoid resampling
- Mono channel audio sufficient for speech recognition
- Buffer size: 512-1024 samples balances latency vs stability
- Use `sounddevice.InputStream` with callback for continuous capture

---

## R3: Audio Buffer Management

**Decision**: Implement ring buffer with numpy arrays for in-memory audio storage

**Rationale**:
- **Memory Efficiency**: Pre-allocated numpy array prevents fragmentation and GC pressure
- **Performance**: C-level operations via numpy faster than Python list appending
- **Privacy Compliance**: Easy to zero-out buffer after transcription (FR-008)
- **Integration**: Whisper expects numpy arrays, eliminates conversion step

**Alternatives Considered**:
1. **Python lists**: Slower, more memory overhead, requires conversion to numpy
2. **Queue-based**: More complex, unnecessary for single-producer-single-consumer pattern
3. **File-based**: Violates 0-day retention requirement (FR-008), adds I/O latency

**Implementation Notes**:
- Fixed-size buffer for predictable memory usage
- Typical size: 30 seconds at 16kHz = 480,000 samples = ~1MB
- Use `collections.deque` with maxlen for automatic overflow handling
- Clear buffer immediately after transcription with `buffer.fill(0)`

---

## R4: Audio Format Conversion

**Decision**: Use `librosa` for audio preprocessing and format handling

**Rationale**:
- **Whisper Compatibility**: Handles conversion to Whisper's expected format (16kHz mono)
- **Robust Resampling**: High-quality resampling algorithms prevent audio degradation
- **Format Support**: Can handle various input formats if needed (though focusing on raw PCM)
- **Audio Analysis**: Provides utilities for debugging (e.g., duration calculation, silence detection)

**Alternatives Considered**:
1. **scipy.signal**: Lower-level, would require manual implementation of common operations
2. **pydub**: Heavier dependency with ffmpeg requirement, overkill for our needs
3. **Raw numpy operations**: Error-prone, reinventing the wheel

**Implementation Notes**:
- Use `librosa.resample()` if input sample rate differs from 16kHz
- `librosa.util.normalize()` for audio level normalization if needed
- Minimal processing to maintain privacy (no disk writes)

---

## R5: Error Handling Strategy

**Decision**: Implement graceful degradation with structured error logging

**Rationale**:
- **User Experience**: System continues running even when individual transcriptions fail
- **Debugging**: Structured logs provide actionable information without storing sensitive data
- **Constitution Compliance**: Meets observability principle (VI) and error handling NFR

**Error Categories**:
1. **Initialization Errors**: Microphone not found, model load failure → Fatal, exit with clear message
2. **Runtime Errors**: Audio capture glitch, transcription timeout → Log and retry, don't crash
3. **Quality Issues**: Poor audio, low confidence → Log warning, return result anyway

**Implementation Pattern**:
```python
try:
    transcription = transcribe(audio)
    log.info("transcription_complete", duration=audio.duration, success=True)
except WhisperError as e:
    log.error("transcription_failed", error=type(e).__name__, duration=audio.duration)
    # Continue listening, don't crash
```

---

## R6: Configuration Management

**Decision**: Use environment variables with `.env` file support via `python-dotenv`

**Rationale**:
- **Security**: Keeps configuration out of source code
- **Flexibility**: Easy to adjust parameters without code changes
- **12-Factor App**: Follows cloud-native best practices even for local apps
- **Simple**: No complex config file parsing needed

**Key Configuration Variables**:
- `LOG_LEVEL`: INFO (default), DEBUG, WARNING, ERROR
- `AUDIO_SAMPLE_RATE`: 16000 (Whisper native rate)
- `AUDIO_CHANNELS`: 1 (mono)
- `AUDIO_BUFFER_DURATION`: 30 (seconds)
- `MODEL_NAME`: "openai/whisper-tiny"
- `MODEL_CACHE_DIR`: ~/.cache/huggingface (default)

**Alternatives Considered**:
1. **YAML/JSON config files**: More complex, unnecessary for simple key-value pairs
2. **CLI arguments**: Less convenient for persistent settings
3. **Hardcoded constants**: Inflexible, violates good practices

---

## R7: Dependency Management

**Decision**: Pin exact versions in `requirements.txt`, use version ranges for compatibility

**Rationale**:
- **Reproducibility**: Exact versions ensure consistent behavior across environments
- **Security**: Allows controlled updates after testing
- **Constitution Compliance**: Follows dependency management standard

**Core Dependencies** (with version considerations):
```
torch>=2.0.0,<3.0.0          # PyTorch for model inference
transformers>=4.30.0,<5.0.0   # Hugging Face library
sounddevice>=0.4.6,<0.5.0     # Audio capture
librosa>=0.10.0,<0.11.0       # Audio processing
numpy>=1.24.0,<2.0.0          # Array operations
python-dotenv>=1.0.0,<2.0.0   # Environment configuration
pytest>=7.4.0,<8.0.0          # Testing framework
pytest-cov>=4.1.0,<5.0.0      # Coverage reporting
```

**Update Strategy**:
- Review updates monthly for security patches
- Test thoroughly before updating MINOR versions
- Document breaking changes in changelog

---

## Summary

All research questions resolved. Key technical decisions:

1. **Model**: Whisper Tiny via Hugging Face Transformers
2. **Audio Capture**: sounddevice with callback streaming
3. **Buffering**: Numpy-based ring buffer
4. **Processing**: librosa for format handling
5. **Error Handling**: Graceful degradation with structured logging
6. **Configuration**: Environment variables with .env support
7. **Dependencies**: Pinned versions with semantic ranges

No remaining NEEDS CLARIFICATION items. Ready to proceed to Phase 1: Design & Contracts.
