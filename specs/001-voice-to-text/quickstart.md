# Quickstart Guide: Voice-to-Text Transcription

**Feature**: 001-voice-to-text  
**Created**: 2025-12-11  
**Audience**: Developers

## Overview

This guide will help you set up the development environment, install dependencies, configure the application, and run the voice-to-text transcription feature.

---

## Prerequisites

### Required Software

- **Python 3.10 or higher**: [Download Python](https://www.python.org/downloads/)
- **pip**: Package installer for Python (included with Python 3.10+)
- **Git**: Version control (for cloning the repository)

### Hardware Requirements

- **Microphone**: Any USB or built-in microphone with system permissions
- **RAM**: At least 2 GB available for model loading and inference
- **CPU/GPU**: CPU sufficient for Tiny Whisper (GPU optional for faster processing)

### Verify Prerequisites

```powershell
# Check Python version (must be 3.10+)
python --version

# Check pip is available
pip --version

# List available audio input devices
python -m sounddevice
```

---

## Installation

### 1. Clone the Repository

```powershell
git clone <repository-url>
cd home_automation_assistant
git checkout 001-voice-to-text
```

### 2. Create Virtual Environment

```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Activate virtual environment (Windows CMD)
.\.venv\Scripts\activate.bat

# Activate virtual environment (Linux/macOS)
source .venv/bin/activate
```

### 3. Install Dependencies

```powershell
# Upgrade pip
pip install --upgrade pip

# Install required packages
pip install torch>=2.0.0 transformers>=4.30.0 sounddevice>=0.4.6 librosa>=0.10.0 numpy>=1.24.0

# Install development dependencies (optional)
pip install pytest>=7.4.0 pytest-cov>=4.1.0 python-dotenv>=1.0.0
```

**Alternative**: Use `requirements.txt` (if available):

```powershell
pip install -r requirements.txt
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root directory:

```env
# Audio Configuration
AUDIO_SAMPLE_RATE=16000
AUDIO_CHANNELS=1
AUDIO_BUFFER_SIZE=1024
AUDIO_DEVICE_INDEX=  # Leave empty for default microphone

# Whisper Model Configuration
WHISPER_MODEL_NAME=openai/whisper-tiny
WHISPER_DEVICE=cpu  # Use "cuda" if GPU available

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json

# Privacy Configuration
AUDIO_RETENTION_SECONDS=0  # MUST be 0 per constitution
```

### Verify Microphone Access

Test that Python can access your microphone:

```powershell
# Run sounddevice test
python -c "import sounddevice as sd; print(sd.query_devices())"
```

You should see a list of audio devices. Identify the index of your microphone.

---

## Project Structure

```
home_automation_assistant/
├── src/
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── stream.py        # AudioStream implementation
│   │   └── buffer.py        # AudioBuffer implementation
│   ├── transcription/
│   │   ├── __init__.py
│   │   └── whisper.py       # Transcription logic
│   ├── session/
│   │   ├── __init__.py
│   │   └── manager.py       # VoiceSession management
│   └── utils/
│       ├── __init__.py
│       └── config.py        # Configuration loader
├── tests/
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── contract/            # Contract tests
├── .env                     # Environment variables (create this)
├── .env.example             # Example environment configuration
├── main.py                  # Application entry point
└── requirements.txt         # Python dependencies
```

---

## Running the Application

### Basic Usage

```powershell
# Activate virtual environment (if not already active)
.\.venv\Scripts\Activate.ps1

# Run the application
python main.py
```

### Expected Output

```
[INFO] Loading Whisper model: openai/whisper-tiny
[INFO] Model loaded successfully in 3.2s
[INFO] Initializing audio stream (sample_rate=16000, channels=1)
[INFO] Audio stream started (device_index=0)
[INFO] Listening... Speak into your microphone.
```

### Interactive Commands

While the application is running:

- **Speak**: Just talk into your microphone
- **Stop**: Press `Ctrl+C` to stop the application gracefully

### Viewing Transcriptions

Transcribed text will be displayed in the console:

```
[2025-12-11 14:23:45] Transcription: "turn on the living room lights"
[2025-12-11 14:23:52] Transcription: "set temperature to 72 degrees"
```

---

## Testing

### Run Unit Tests

```powershell
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/unit/test_audio_stream.py
```

### Run Integration Tests

```powershell
# Run integration tests only
pytest tests/integration/

# Run with verbose output
pytest tests/integration/ -v
```

### Minimum Coverage Requirement

Per the constitution, tests MUST achieve at least **60% code coverage**:

```powershell
# Check coverage (must be >= 60%)
pytest --cov=src --cov-report=term-missing
```

---

## Troubleshooting

### Issue: "No module named 'torch'"

**Solution**: Ensure virtual environment is activated and dependencies are installed:

```powershell
.\.venv\Scripts\Activate.ps1
pip install torch transformers
```

### Issue: "PortAudioError: Error opening audio stream"

**Solution**: Check microphone permissions and device availability:

```powershell
# List available devices
python -m sounddevice

# Test microphone access
python -c "import sounddevice as sd; sd.rec(16000, samplerate=16000, channels=1)"
```

On Windows, ensure microphone permissions are granted in Settings → Privacy → Microphone.

### Issue: "Model download fails"

**Solution**: The first run downloads the Whisper model (~39 MB). Ensure internet connection:

```powershell
# Manually download model (optional)
python -c "from transformers import WhisperProcessor, WhisperForConditionalGeneration; WhisperProcessor.from_pretrained('openai/whisper-tiny'); WhisperForConditionalGeneration.from_pretrained('openai/whisper-tiny')"
```

### Issue: High CPU usage

**Solution**: Tiny Whisper is optimized for CPU, but for better performance:

- Use GPU if available: Set `WHISPER_DEVICE=cuda` in `.env`
- Reduce sample rate: Set `AUDIO_SAMPLE_RATE=8000` (lower quality)
- Increase buffer size: Set `AUDIO_BUFFER_SIZE=2048`

### Issue: "Memory leak during continuous operation"

**Solution**: Verify buffer clearance implementation:

```python
# Ensure buffers are explicitly cleared
audio_buffer.clear()
gc.collect()
```

---

## Development Workflow

### 1. Make Code Changes

Edit files in `src/` directory following the project structure.

### 2. Run Tests

```powershell
pytest tests/
```

### 3. Check Coverage

```powershell
pytest --cov=src --cov-report=term-missing
```

### 4. Commit Changes

```powershell
git add .
git commit -m "feat: implement audio buffer clearance"
```

### 5. Push to Feature Branch

```powershell
git push origin 001-voice-to-text
```

---

## Next Steps

After successfully running the voice-to-text feature:

1. **Command Interpretation**: Add intent classification for voice commands
2. **MQTT Integration**: Connect transcriptions to MQTT message publishing
3. **Light Control**: Implement device control based on interpreted commands
4. **Voice Activity Detection**: Add automatic start/stop for hands-free operation

---

## Useful Commands

### Virtual Environment

```powershell
# Activate (Windows PowerShell)
.\.venv\Scripts\Activate.ps1

# Deactivate
deactivate
```

### Package Management

```powershell
# Install new package
pip install <package-name>

# Freeze dependencies
pip freeze > requirements.txt

# Install from requirements
pip install -r requirements.txt
```

### Audio Diagnostics

```powershell
# List audio devices
python -m sounddevice

# Record 5 seconds of audio test
python -c "import sounddevice as sd; import numpy as np; audio = sd.rec(int(5 * 16000), samplerate=16000, channels=1); sd.wait(); print('Recording complete')"
```

---

## Support & Resources

- **Whisper Documentation**: https://huggingface.co/docs/transformers/model_doc/whisper
- **sounddevice Documentation**: https://python-sounddevice.readthedocs.io/
- **PyTorch Installation**: https://pytorch.org/get-started/locally/
- **Project Issues**: <repository-issues-url>

---

## Change History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-12-11 | Initial quickstart guide |
