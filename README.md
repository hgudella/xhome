# XHOME - Voice-Controlled Smart Home System

Local voice-controlled smart home automation combining voice capture, speech-to-text transcription, AI command understanding, and MQTT device control.

## 🌟 Features

### Feature 001: Voice-to-Text
- **Real-time Voice Capture**: Continuous microphone listening with sounddevice
- **Local Speech-to-Text**: Whisper model via Hugging Face Transformers (~150MB)
- **Voice Activity Detection**: Silero VAD for automatic speech boundary detection
- **Continuous Listening**: VAD-based mode with no word loss between utterances
- **Privacy-First**: 0-day audio retention, local-only processing, metadata-only logging

### Feature 002: SLM Command Processing & MQTT Integration
- **AI Command Understanding**: Phi-4-Mini SLM for natural language command extraction
- **Device Management**: YAML-based device configuration with 6+ device types
- **MQTT Publishing**: QoS 1 message delivery to smart home devices
- **State Awareness**: Optional device state tracking with redundancy detection
- **Conversational AI**: Friendly responses and command confirmations

## 🚀 Quick Start

### Prerequisites

- Python 3.10+
- Microphone with system permissions
- 2GB+ available RAM (4GB+ recommended with SLM)
- MQTT broker (e.g., Mosquitto) for smart home control

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

# Configure devices
cp config/devices.yaml.example config/devices.yaml
# Edit config/devices.yaml with your device MQTT topics
```

### Download AI Models

```powershell
# Whisper model (auto-downloads on first run)
# No action needed - handled automatically

# Phi-4-Mini SLM (2GB - required for command processing)
# Download from: https://huggingface.co/bartowski/Phi-4-mini-instruct-GGUF
# Place in: models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf
```

### Usage

#### Full Voice-Controlled Smart Home

```powershell
# Basic usage (voice → command → MQTT)
python run_full_system.py

# With state awareness (redundancy detection)
python run_full_system.py --state-awareness

# Text-only mode (no command processing)
python run_full_system.py --text-only

# Custom MQTT broker
python run_full_system.py --mqtt-host 192.168.1.100 --mqtt-port 1883

# Disable commands (transcription only)
python run_full_system.py --no-commands

# Debug mode
python run_full_system.py --debug
```

#### Feature 001 Only (Voice-to-Text)

#### Feature 001 Only (Voice-to-Text)

```powershell
# Single capture (3 seconds, default)
python main.py

# Single capture (5 seconds)
python main.py --duration 5

# ⭐ Continuous mode with VAD (RECOMMENDED)
python main.py --continuous

# Use different model
python main.py --model openai/whisper-base

# Use GPU (if available)
python main.py --device cuda
```

## 🏗️ Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│  Microphone │────▶│   Whisper    │────▶│  SLM Model  │
│   (VAD)     │     │ Transcription│     │  (Phi-4)    │
└─────────────┘     └──────────────┘     └─────────────┘
                                                 │
                                                 ▼
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│Smart Devices│◀────│     MQTT     │◀────│   Device    │
│  (Lights,   │     │    Broker    │     │   Config    │
│  Thermostat)│     │              │     │             │
└─────────────┘     └──────────────┘     └─────────────┘
                           ▲
                           │
                    ┌──────────────┐
                    │ State Cache  │ (Optional)
                    │ Redundancy   │
                    └──────────────┘
```

## 📋 Configuration

### Device Configuration (config/devices.yaml)

```yaml
living_room_light:
  type: light
  friendly_name: "Living Room Light"
  command_topic: "home/lights/living_room/set"
  state_topic: "home/lights/living_room/state"
  capabilities:
    - turn_on
    - turn_off
    - set_brightness

bedroom_thermostat:
  type: thermostat
  friendly_name: "Bedroom Thermostat"
  command_topic: "home/climate/bedroom/set"
  state_topic: "home/climate/bedroom/state"
  capabilities:
    - set_temperature
```

### Environment Variables (.env)

```bash
# Whisper Model
WHISPER_MODEL=openai/whisper-base
WHISPER_DEVICE=cpu

# SLM Model
SLM_MODEL_PATH=models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf

# MQTT Configuration
MQTT_HOST=localhost
MQTT_PORT=1883
MQTT_USERNAME=
MQTT_PASSWORD=

# State Awareness
ENABLE_STATE_TRACKING=false
STATE_TTL_SECONDS=300

# Logging
LOG_LEVEL=INFO
```

## 💬 Example Commands

```
"Turn on the living room light"
"Set bedroom light to 75 percent"
"Turn off the kitchen light"
"Set thermostat to 72 degrees"
"Turn on ceiling fan"
"Dim bedroom light to 25 percent"
```

## ⚡ Performance

| Metric | Value | Notes |
|--------|-------|-------|
| Startup Time | ~5s | Model loading (Whisper + SLM) |
| Transcription | <3s | Whisper base model |
| SLM Inference | 2-10s | Command extraction |
| MQTT Publish | <100ms | QoS 1 with PUBACK |
| End-to-End | 3-12s | Voice → Device control |
| VAD Detection | ~300ms | Real-time speech detection |
| State Check | <10ms | Redundancy detection |

## 🔒 Privacy

- ✅ **Local Processing**: All AI runs on-device (no cloud APIs)
- ✅ **0-Day Retention**: Audio deleted immediately after transcription
- ✅ **Metadata Only**: Logs contain no PII or transcription text
- ✅ **No Persistence**: Transcriptions cleared after command extraction
- ✅ **Network Isolation**: Only MQTT messages leave the device

## 📚 Documentation

### Feature 001: Voice-to-Text
- [Feature Specification](specs/001-voice-to-text/spec.md)
- [Implementation Plan](specs/001-voice-to-text/plan.md)
- [Tasks Breakdown](specs/001-voice-to-text/tasks.md)
- [Quickstart Guide](specs/001-voice-to-text/quickstart.md)

### Feature 002: SLM & MQTT Integration
- [Feature Specification](specs/002-slm-mqtt-integration/spec.md)
- [Implementation Plan](specs/002-slm-mqtt-integration/plan.md)
- [Data Model](specs/002-slm-mqtt-integration/data-model.md)
- [Tasks Breakdown](specs/002-slm-mqtt-integration/tasks.md)
- [Quickstart Guide](specs/002-slm-mqtt-integration/quickstart.md)

## 🧪 Testing

```powershell
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test suites
pytest tests/unit/           # Unit tests
pytest tests/contract/       # Contract tests
pytest tests/integration/    # Integration tests

# Minimum coverage requirement: 60%
```

### Test Coverage

- **Contract Tests**: SLM interface, MQTT interface, VAD interface
- **Integration Tests**: Audio capture pipeline, command extraction, MQTT publishing
- **Unit Tests**: Audio buffer, transcription, VAD, Whisper engine

## 🛠️ Development

### Project Structure

```
xhome/
├── src/
│   ├── audio/              # Feature 001: Audio capture
│   │   ├── buffer.py       # Audio buffer management
│   │   ├── capture.py      # Single-shot capture
│   │   ├── continuous.py   # Continuous listening
│   │   └── vad.py          # Voice activity detection
│   ├── transcription/      # Feature 001: Speech-to-text
│   │   ├── transcriber.py  # Transcription models
│   │   └── whisper_engine.py # Whisper integration
│   ├── command/            # Feature 002: Command processing
│   │   ├── slm_engine.py   # SLM inference
│   │   ├── parser.py       # Command parsing
│   │   ├── router.py       # Pipeline orchestration
│   │   ├── models.py       # Data models
│   │   └── session.py      # Session tracking
│   ├── devices/            # Feature 002: Device management
│   │   ├── config.py       # Device configuration
│   │   ├── mqtt_client.py  # MQTT wrapper
│   │   ├── mqtt_config.py  # MQTT configuration
│   │   ├── state.py        # State cache
│   │   └── models.py       # Device models
│   └── utils/
│       ├── config.py       # Configuration loader
│       ├── exceptions.py   # Custom exceptions
│       └── logging.py      # Logging utilities
├── tests/
│   ├── contract/           # Interface contracts
│   ├── integration/        # Integration tests
│   └── unit/               # Unit tests
├── config/
│   └── devices.yaml.example # Device configuration template
├── main.py                 # Feature 001 CLI
└── run_full_system.py      # Full system CLI
```

## 🐛 Troubleshooting

### Common Issues

**MQTT Connection Failed**
```powershell
# Check if broker is running
# For Mosquitto:
mosquitto -v

# Test with mosquitto_pub:
mosquitto_pub -h localhost -t test -m "hello"
```

**SLM Timeout**
- Increase timeout in src/command/slm_engine.py
- Use smaller quantized model (Q4_K_M or Q4_0)
- Simplify command phrases

**Microphone Not Detected**
```powershell
# List available devices
python -c "import sounddevice; print(sounddevice.query_devices())"
```

**Model Download Issues**
- Whisper: Auto-downloads via Hugging Face (requires internet on first run)
- Phi-4-Mini: Manual download from https://huggingface.co/bartowski/Phi-4-mini-instruct-GGUF

## 📦 Dependencies

### Core Dependencies
- **torch** (2.0.0+): PyTorch for Whisper
- **transformers** (4.30.0+): Hugging Face Transformers
- **sounddevice** (0.4.6+): Audio capture
- **librosa** (0.10.0+): Audio processing
- **llama-cpp-python** (0.2.0+): SLM inference
- **paho-mqtt** (1.6.0): MQTT client
- **pyyaml** (6.0.0+): Configuration parsing

### Optional Dependencies
- **silero-vad**: Voice activity detection (auto-installed)
- **numpy**: Array operations

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- **OpenAI Whisper**: Speech recognition model
- **Microsoft Phi-4**: Small language model
- **Silero VAD**: Voice activity detection
- **Eclipse Mosquitto**: MQTT broker reference implementation

## 🚦 Status

- ✅ **Feature 001**: Voice-to-Text - **COMPLETE**
- ✅ **Feature 002**: SLM & MQTT - **COMPLETE** (MVP + State Awareness)
- 📝 CLI flags and documentation - **COMPLETE**

---

**Current Version**: 2.0.0  
**Last Updated**: December 12, 2025

Private project - © 2025 Harish Gudella
