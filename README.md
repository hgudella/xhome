# Home Automation Assistant - Voice-to-Text

Local voice capture and speech-to-text transcription using Tiny Whisper.

## Quick Start

See [quickstart guide](specs/001-voice-to-text/quickstart.md) for detailed setup instructions.

### Prerequisites

- Python 3.10+
- Microphone with system permissions
- 2GB+ available RAM

### Installation

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env as needed
```

### Usage

```powershell
# Single capture (3 seconds, default)
python main.py

# Single capture (5 seconds)
python main.py --duration 5

# ⭐ Continuous mode with VAD (RECOMMENDED)
# - Automatically detects when you speak
# - No gaps between utterances
# - No word loss!
python main.py --continuous

# Legacy continuous mode (old chunk-based behavior)
python main.py --continuous --legacy --duration 5

# Use different model (larger = more accurate, slower)
python main.py --model openai/whisper-base

# Use GPU (if available)
python main.py --device cuda

# Verbose logging
python main.py --verbose
```

**Expected Performance:**
- Startup time: < 10 seconds (model loading)
- Transcription latency: < 3 seconds
- VAD detection: Real-time (~300ms chunks)
- Privacy: 0-day audio retention (immediate deletion after transcription)

**What's New in VAD Mode:**
- ✅ Always-on microphone (no gaps!)
- ✅ Automatic speech detection
- ✅ No word loss at boundaries
- ✅ Natural continuous speech
- ✅ Automatic silence detection

## Features

- **Real-time Voice Capture**: Continuous microphone listening with sounddevice
- **Local Speech-to-Text**: Whisper Tiny model via Hugging Face Transformers (~150MB)
- **Voice Activity Detection**: Silero VAD for automatic speech boundary detection
- **Continuous Listening**: VAD-based mode with no word loss between utterances
- **Privacy-First**: 0-day audio retention, local-only processing, metadata-only logging
- **Command-line Interface**: Simple CLI with single-shot, continuous VAD, and legacy modes

## Documentation

- [Feature Specification](specs/001-voice-to-text/spec.md)
- [Implementation Plan](specs/001-voice-to-text/plan.md)
- [Tasks Breakdown](specs/001-voice-to-text/tasks.md)
- [Quickstart Guide](specs/001-voice-to-text/quickstart.md)

## Testing

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Minimum coverage requirement: 60%
```

## License

Private project - © 2025 Harish Gudella
