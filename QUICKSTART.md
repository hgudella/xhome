# XHOME Quick Start Guide

Complete setup instructions for running the voice-controlled smart home system locally.

## Prerequisites

### 1. Python Environment
```powershell
# Already done in your setup:
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Models

#### Whisper Model (Feature 001 - Voice Transcription)
```powershell
# Downloads automatically on first run
# Or manually download:
# Model: openai/whisper-base (~150MB)
```

#### Phi-4 SLM Model (Feature 002 - Command Understanding)
```powershell
# Already done in your setup:
# Located at: models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf
```

### 3. MQTT Broker (Required for Full System)

**Option A: Docker (Recommended)**
```powershell
# Install Docker Desktop from: https://www.docker.com/products/docker-desktop/

# Start Mosquitto MQTT broker
docker run -d -p 1883:1883 -p 9001:9001 --name mosquitto eclipse-mosquitto

# Verify it's running
docker ps
```

**Option B: Native Installation**
```powershell
# Download Mosquitto from: https://mosquitto.org/download/
# Install and run:
mosquitto -v
```

**Option C: Mock Mode (Testing Only)**
- The demo scripts can run without MQTT using mocks
- Full system requires actual broker

## Running Different Configurations

### Configuration 1: Full End-to-End System (Recommended)

**What it does:** Voice → Transcription → Command Understanding → MQTT Publishing

```powershell
# 1. Activate environment
.\.venv\Scripts\Activate.ps1

# 2. Ensure MQTT broker is running (see step 3 above)
docker ps  # Should show mosquitto container

# 3. Run full system
python run_full_system.py
```

**Expected output:**
```
🏠 XHOME - Voice-Controlled Smart Home System
✅ System Ready!
🎤 Listening for voice commands...
```

**Test it:**
- Speak: "Turn on the living room light"
- Should see: `✓ Command: turn_on → living_room_light`
- Should see: `📡 Published to: home/light/living_room/set`

---

### Configuration 2: Voice Transcription Only (Feature 001)

**What it does:** Voice → Transcription (no command understanding)

```powershell
.\.venv\Scripts\Activate.ps1
python main.py
```

**Expected output:**
```
🎤 Listening... Press Ctrl+C to stop
Transcription: "turn on the light"
```

---

### Configuration 3: Command Understanding Demo (Feature 002)

**What it does:** Hardcoded text → Command Understanding → MQTT Publishing (mocked)

```powershell
.\.venv\Scripts\Activate.ps1
python demo_voice_to_mqtt.py
```

**Expected output:**
```
✓ Intent: turn_on
✓ Device: living_room_light
📡 MQTT Topic: home/light/living_room/set
```

---

## Verify Each Component

### Test 1: Audio Capture
```powershell
.\.venv\Scripts\Activate.ps1
python test_microphone.py
```
Should show audio levels when you speak.

### Test 2: VAD (Voice Activity Detection)
```powershell
python test_speech_detection.py
```
Should detect when you start/stop speaking.

### Test 3: Transcription
```powershell
python test_one_transcription.py
```
Should transcribe a 5-second recording.

### Test 4: SLM Command Extraction
```powershell
pytest tests/integration/test_slm_integration.py -v
```
Should pass 3/3 tests.

### Test 5: MQTT Publishing
```powershell
# With MQTT broker running:
pytest tests/integration/test_mqtt_publishing.py -v
```
Should pass 5/5 tests (uses mocks, no broker needed).

### Test 6: End-to-End Pipeline
```powershell
pytest tests/integration/test_voice_to_mqtt.py -v
```
Should pass 5/5 tests.

---

## Troubleshooting

### Issue: "No module named 'llama_cpp'"
**Solution:** Activate virtual environment first
```powershell
.\.venv\Scripts\Activate.ps1
```

### Issue: "MQTT connection failed"
**Solution:** Start MQTT broker
```powershell
# Check if running
docker ps

# If not, start it
docker run -d -p 1883:1883 --name mosquitto eclipse-mosquitto
```

### Issue: "Microphone not detected"
**Solution:** Check audio input
```powershell
python test_microphone.py  # Should list available devices
```

### Issue: "Model loading takes too long"
**Solution:** Models load on first run
- Whisper base: ~10-15s first time
- Phi-4-Mini: ~2-5s first time
- Subsequent runs are faster (cached)

### Issue: "VAD not detecting speech"
**Solution:** Adjust sensitivity in code
```python
# In src/audio/vad.py
threshold=0.5  # Lower = more sensitive (try 0.3)
```

---

## Device Configuration

Edit `config/devices.yaml.example` to add your devices:

```yaml
devices:
  light:
    - name: my_bedroom_light
      location: bedroom
      mqtt_topic: home/light/bedroom/set
      aliases: ["bedroom lamp"]
      
  switch:
    - name: my_fan
      location: bedroom
      mqtt_topic: home/switch/bedroom_fan/set
      aliases: ["fan"]
```

Supported device types:
- `light`: turn_on, turn_off, set_brightness
- `switch`: turn_on, turn_off
- `thermostat`: set_temperature

---

## Performance Benchmarks

From your system:

| Component | Metric | Your Result | Requirement | Status |
|-----------|--------|-------------|-------------|--------|
| Model Load | Time | 2.04s | <15s | ✅ |
| SLM Inference | Time | 2-7s | <10s | ✅ |
| Command Confidence | Score | 85-95% | >80% | ✅ |
| VAD Detection | Latency | <300ms | <500ms | ✅ |
| Transcription | Latency | ~3-5s | <10s | ✅ |

---

## What's Next?

Currently implemented:
- ✅ Feature 001: Voice capture and transcription
- ✅ Feature 002: Command understanding and MQTT publishing

Coming soon (see `specs/001-voice-to-text/tasks.md`):
- ⏳ Phase 5: State awareness (redundancy detection)
- ⏳ Phase 6: Feedback generation
- ⏳ Phase 7: Comprehensive integration tests
- ⏳ Phase 8: CLI with configuration management

---

## Architecture Overview

```
[Microphone] 
    ↓
[Audio Buffer] → [VAD] → [Whisper] → [Transcription]
                                          ↓
                                     [SLM Engine] → [Command]
                                          ↓
                                   [Device Config] → [Device Mapping]
                                          ↓
                                    [MQTT Client] → [Smart Home Devices]
```

## Questions?

- Check logs in console output (INFO level)
- Run tests to isolate issues: `pytest tests/ -v`
- Review `specs/001-voice-to-text/spec.md` for requirements
