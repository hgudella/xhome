# Quickstart: SLM Command Processing and MQTT Integration

**Feature**: 002-slm-mqtt-integration  
**Prerequisites**: Feature 001 (Voice-to-Text) must be implemented  
**Estimated Setup Time**: 15-20 minutes

## Overview

This guide walks you through setting up voice-controlled home automation using natural language commands. The system listens to your voice, understands your intent using Phi-4-Mini-GGUF, and controls devices via MQTT.

**What You'll Build**:
- Voice command understanding ("turn on the living room light")
- MQTT-based device control
- State-aware responses ("the light is already on")
- Real-time command feedback

---

## Prerequisites

### System Requirements

- **Python**: 3.10 or higher
- **RAM**: 4GB available (2GB for Whisper + 2GB for Phi-4-Mini)
- **Storage**: 3GB for models (Whisper + Phi-4-Mini-GGUF)
- **Network**: Access to local MQTT broker
- **Microphone**: With system permissions (from Feature 001)

### Required Software

1. **MQTT Broker** (choose one):
   - **Mosquitto** (recommended): `apt-get install mosquitto` (Linux) or download from [mosquitto.org](https://mosquitto.org/)
   - **HiveMQ**: Docker image `docker run -p 1883:1883 hivemq/hivemq-ce`
   - **EMQX**: Docker image `docker run -p 1883:1883 emqx/emqx`

2. **Home Automation Devices** (optional for testing):
   - Any MQTT-compatible smart devices
   - Or use MQTT test client to simulate devices

### Python Dependencies

Already installed from Feature 001:
- `torch`, `transformers`, `sounddevice`, `librosa`

New dependencies for this feature:
```bash
pip install llama-cpp-python paho-mqtt pyyaml
```

---

## Installation

### Step 1: Install Dependencies

```powershell
# Ensure virtual environment is activated (from Feature 001)
.\.venv\Scripts\Activate.ps1

# Install new dependencies
pip install llama-cpp-python paho-mqtt pyyaml

# Verify installation
python -c "import paho.mqtt.client as mqtt; print('MQTT OK')"
python -c "from llama_cpp import Llama; print('llama-cpp OK')"
```

### Step 2: Download Phi-4-Mini-GGUF Model

```powershell
# Create models directory
New-Item -ItemType Directory -Force -Path models/Phi-4-Mini-GGUF

# Download model (choose one method)

# Method 1: Using Hugging Face CLI (recommended)
pip install huggingface-hub
huggingface-cli download microsoft/Phi-4-Mini-GGUF phi-4-mini-q4_k_m.gguf --local-dir models/Phi-4-Mini-GGUF

# Method 2: Manual download
# Visit: https://huggingface.co/microsoft/Phi-4-Mini-GGUF
# Download: phi-4-mini-q4_k_m.gguf (~2GB)
# Place in: models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf
```

**Model Verification**:
```powershell
# Check file exists and size
Get-Item models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf
# Should be approximately 2GB
```

### Step 3: Configure MQTT Broker

```powershell
# Start Mosquitto broker (if using Mosquitto)
# Linux/Mac:
mosquitto -v

# Windows (if installed as service):
net start mosquitto

# Docker (alternative):
docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto
```

**Test MQTT Connection**:
```powershell
# Subscribe to test topic (in one terminal)
mosquitto_sub -h localhost -t test/topic

# Publish test message (in another terminal)
mosquitto_pub -h localhost -t test/topic -m "Hello MQTT"

# If message appears in subscriber terminal, MQTT is working ✓
```

### Step 4: Configure Devices

Create device configuration file:

```powershell
# Copy example configuration
Copy-Item config/devices.yaml.example config/devices.yaml

# Edit configuration
notepad config/devices.yaml
```

**Example Configuration** (`config/devices.yaml`):

```yaml
devices:
  lights:
    - name: living_room_light
      aliases:
        - "living room light"
        - "lounge light"
        - "main light"
      mqtt:
        command_topic: "home/light/living_room/set"
        state_topic: "home/light/living_room/state"
      capabilities:
        - on_off
        - brightness
    
    - name: bedroom_light
      aliases:
        - "bedroom light"
        - "bed light"
      mqtt:
        command_topic: "home/light/bedroom/set"
        state_topic: "home/light/bedroom/state"
      capabilities:
        - on_off
        - brightness
  
  switches:
    - name: ceiling_fan
      aliases:
        - "fan"
        - "ceiling fan"
        - "bedroom fan"
      mqtt:
        command_topic: "home/switch/fan/set"
        state_topic: "home/switch/fan/state"
      capabilities:
        - on_off

mqtt_broker:
  host: localhost
  port: 1883
```

### Step 5: Set Environment Variables

```powershell
# Option 1: Update .env file
Add-Content .env @"
# MQTT Configuration
MQTT_BROKER_HOST=localhost
MQTT_BROKER_PORT=1883
# MQTT_USERNAME=your_username  # Optional
# MQTT_PASSWORD=your_password  # Optional

# SLM Configuration
SLM_MODEL_PATH=models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf
SLM_TIMEOUT=10
"@

# Option 2: Set directly in PowerShell
$env:MQTT_BROKER_HOST="localhost"
$env:MQTT_BROKER_PORT="1883"
$env:SLM_MODEL_PATH="models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf"
```

---

## Usage

### Basic Command Processing

```powershell
# Start the home automation assistant
python main.py --enable-commands

# The system will:
# 1. Load Whisper model (~5 seconds)
# 2. Load Phi-4-Mini model (~10 seconds)
# 3. Connect to MQTT broker
# 4. Start listening for voice input
```

**Try saying**:
- "Turn on the living room light"
- "Set bedroom light to 50 percent"
- "Turn off the fan"

**Expected Output**:
```
[INFO] Whisper model loaded
[INFO] Phi-4-Mini model loaded
[INFO] Connected to MQTT broker at localhost:1883
[INFO] Subscribed to state topics
[INFO] Listening for voice commands... (Press Ctrl+C to stop)

You: "turn on the living room light"
[INFO] Transcribed: turn on the living room light
[INFO] Extracted intent: turn_on, device: living_room_light
[INFO] Published to home/light/living_room/set
Assistant: "Living room light turned on"
```

### Continuous Mode with Commands

```powershell
# Continuous listening with automatic voice detection
python main.py --continuous --enable-commands

# Benefits:
# - No gaps between commands
# - Automatic speech detection (VAD)
# - Seamless multi-command processing
```

### Command-Only Mode (No Voice)

For testing command processing without voice input:

```powershell
# Interactive text input mode
python main.py --text-only

# Type commands directly:
>>> turn on the living room light
Assistant: "Living room light turned on"

>>> set bedroom light to 75 percent brightness
Assistant: "Bedroom light brightness set to 75%"
```

---

## Testing Device Control

### Simulate Devices with MQTT Client

If you don't have physical devices, simulate them:

```powershell
# Terminal 1: Subscribe to command topic
mosquitto_sub -h localhost -t 'home/light/+/set' -v

# Terminal 2: Publish simulated state
mosquitto_pub -h localhost -t 'home/light/living_room/state' -m '{"state":"OFF","brightness":0}'

# Terminal 3: Run the assistant
python main.py --enable-commands
```

When you say "turn on the living room light", you'll see in Terminal 1:
```
home/light/living_room/set {"state":"ON"}
```

### Verify State Awareness

```powershell
# 1. Set device to ON state
mosquitto_pub -h localhost -t 'home/light/living_room/state' -m '{"state":"ON","brightness":100}'

# 2. Say "turn on the living room light"
# Expected response: "The living room light is already on"

# 3. Say "turn off the living room light"
# Expected: Command publishes, light turns off
```

---

## Common Commands

### Lights

| Voice Command | Intent | MQTT Payload |
|---------------|--------|--------------|
| "Turn on the living room light" | `turn_on` | `{"state":"ON"}` |
| "Turn off bedroom light" | `turn_off` | `{"state":"OFF"}` |
| "Set bedroom light to 50 percent" | `set_brightness` | `{"state":"ON","brightness":50}` |
| "Dim the living room light" | `set_brightness` | `{"state":"ON","brightness":30}` |

### Switches/Fans

| Voice Command | Intent | MQTT Payload |
|---------------|--------|--------------|
| "Turn on the fan" | `turn_on` | `{"state":"ON"}` |
| "Turn off ceiling fan" | `turn_off` | `{"state":"OFF"}` |

### Thermostats

| Voice Command | Intent | MQTT Payload |
|---------------|--------|--------------|
| "Set temperature to 22 degrees" | `set_temperature` | `{"temperature":22}` |
| "Set thermostat to 75" | `set_temperature` | `{"temperature":75}` |

---

## Troubleshooting

### Model Not Loading

**Symptom**: `FileNotFoundError: models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf`

**Solution**:
```powershell
# Verify model file exists
Test-Path models/Phi-4-Mini-GGUF/phi-4-mini-q4_k_m.gguf

# Re-download if missing
huggingface-cli download microsoft/Phi-4-Mini-GGUF phi-4-mini-q4_k_m.gguf --local-dir models/Phi-4-Mini-GGUF
```

### MQTT Connection Failed

**Symptom**: `MQTTConnectionError: Connection refused`

**Solution**:
```powershell
# Check if broker is running
Test-NetConnection -ComputerName localhost -Port 1883

# Start broker if not running
net start mosquitto  # Windows service
# OR
mosquitto -v  # Foreground mode

# Check firewall (Windows)
New-NetFirewallRule -DisplayName "MQTT" -Direction Inbound -Protocol TCP -LocalPort 1883 -Action Allow
```

### Device Not Found

**Symptom**: `Assistant: "I don't recognize a device called 'garage light'"`

**Solution**:
```powershell
# Check device configuration
Select-String -Path config/devices.yaml -Pattern "garage"

# Add device to config/devices.yaml if missing
# Restart assistant to reload configuration
```

### Command Not Understood

**Symptom**: `Assistant: "I didn't understand that command"`

**Solutions**:
- Speak more clearly (reduce background noise)
- Use simpler phrasing ("turn on light" instead of "could you please turn on the light")
- Check if device name is in configuration
- Try alternative device aliases

### State Awareness Not Working

**Symptom**: Light turns on when already on (no "already on" message)

**Solution**:
```powershell
# Verify state subscription
mosquitto_sub -h localhost -t 'home/+/+/state' -v

# Ensure devices are publishing state updates
# Check state_awareness is enabled
python main.py --enable-commands --state-awareness
```

---

## Performance Benchmarks

**Expected Performance**:
- Model load time: <20 seconds (both models)
- Command processing latency: <3 seconds
- MQTT publish latency: <100ms
- Memory usage: <4GB total

**If experiencing slowness**:
```powershell
# Enable GPU acceleration (if available)
$env:SLM_GPU_LAYERS="32"

# Reduce model context size
$env:SLM_CONTEXT_SIZE="1024"

# Monitor resource usage
# Task Manager (Windows) or htop (Linux)
```

---

## Next Steps

### Add More Devices

Edit `config/devices.yaml`:
```yaml
devices:
  lights:
    - name: kitchen_light
      aliases: ["kitchen light", "cooking light"]
      mqtt:
        command_topic: "home/light/kitchen/set"
        state_topic: "home/light/kitchen/state"
      capabilities: [on_off, brightness]
```

Restart the assistant to load new configuration.

### Integrate with Home Assistant

If using Home Assistant:

1. Configure MQTT integration in Home Assistant
2. Set same broker host/port in both systems
3. Use Home Assistant entity IDs as device names
4. Home Assistant will automatically handle MQTT commands

### Enable Logging

```powershell
# Detailed logging
$env:LOG_LEVEL="DEBUG"
python main.py --enable-commands

# Logs saved to: logs/assistant.log
```

---

## Command Reference

```powershell
# Basic usage
python main.py --enable-commands

# With continuous mode
python main.py --continuous --enable-commands

# Without state awareness
python main.py --enable-commands --no-state-awareness

# Text-only testing
python main.py --text-only

# Custom configuration
python main.py --enable-commands --config config/devices-custom.yaml

# Specify MQTT broker
python main.py --enable-commands --mqtt-host 192.168.1.100 --mqtt-port 1883

# Help
python main.py --help
```

---

## Architecture Overview

```
┌─────────────┐
│ Microphone  │
└──────┬──────┘
       │ audio
       ▼
┌─────────────┐
│   Whisper   │ (Feature 001)
│   (STT)     │
└──────┬──────┘
       │ text
       ▼
┌─────────────┐
│ Phi-4-Mini  │ ← This Feature (User Story 1)
│    (SLM)    │
└──────┬──────┘
       │ Command(intent, device, params)
       ▼
┌─────────────┐
│   Device    │
│  Validator  │
└──────┬──────┘
       │
       ├──→ ┌─────────────┐
       │    │ State Cache │ (User Story 3)
       │    └─────────────┘
       │           │
       ▼           ▼
┌─────────────┐   Already done?
│    MQTT     │ ← (User Story 2)
│   Client    │
└──────┬──────┘
       │ QoS 1
       ▼
┌─────────────┐
│    MQTT     │
│   Broker    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│   Smart     │
│  Devices    │
└─────────────┘
```

---

## Support

- **Issues**: Open an issue on the repository
- **Documentation**: See `/specs/002-slm-mqtt-integration/`
- **Logs**: Check `logs/assistant.log` for detailed information

---

**Status**: ✅ Quickstart Complete  
**Next**: Run tests with `/speckit.tasks` to generate task breakdown
