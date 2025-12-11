# Audio Transcription CLI

A Python CLI tool that transcribes audio from microphone input or files using OpenAI's Whisper tiny model.

## Features

- 🎤 **Microphone Recording**: Record and transcribe audio in real-time
- 📁 **File Transcription**: Transcribe pre-recorded audio files (WAV, MP3, FLAC)
- 📝 **Multiple Output Formats**: Text, JSON, SRT, VTT
- 🚀 **Lightweight**: Uses Whisper tiny model (~39MB)
- 🔌 **Offline Capable**: Works without internet after initial model download
- 🛡️ **Robust Error Handling**: Clear error messages and proper exit codes

## Installation

### System Requirements

- Python 3.9 or higher
- Working microphone (for recording features)

### System Dependencies

**Linux (Ubuntu/Debian)**:
```bash
sudo apt-get update
sudo apt-get install python3-dev portaudio19-dev ffmpeg
```

**macOS**:
```bash
brew install portaudio ffmpeg
```

**Windows**:
- Install Python from [python.org](https://python.org)
- Download FFmpeg from [ffmpeg.org](https://ffmpeg.org) and add to PATH
- PyAudio wheels available on PyPI (no compilation needed)

### Python Package Installation

```bash
# Clone the repository
git clone <repository-url>
cd audio-transcription-cli

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install system dependencies (Linux)
sudo apt-get update
sudo apt-get install portaudio19-dev python3-dev ffmpeg build-essential

# Install dependencies
pip install -r requirements.txt

# Install the package
pip install -e .
```

**Note**: PyAudio requires system audio libraries. On macOS: `brew install portaudio`. On Windows, PyAudio wheels are available via pip.
```

## Usage

### Quick Start

**Transcribe an audio file**:
```bash
transcribe input.wav
```

**Record 10 seconds from microphone**:
```bash
transcribe --duration 10
```

**Save transcription to file**:
```bash
transcribe input.mp3 --output transcript.txt
```

**Output as JSON**:
```bash
transcribe recording.wav --format json
```

### Command Reference

```
transcribe [OPTIONS] [INPUT_FILE]

Options:
  -d, --duration INTEGER      Recording duration in seconds (default: 30)
  -o, --output PATH          Output file path (default: stdout)
  -f, --format [text|json|srt|vtt]
                             Output format (default: text)
  --device INTEGER           Audio input device index
  --list-devices             List available audio devices
  -l, --language TEXT        Force specific language (ISO 639-1 code)
  --model-path PATH          Custom model cache directory
  -v, --verbose              Enable verbose logging
  --version                  Show version and exit
  -h, --help                 Show this message and exit
```

### Examples

**List available microphones**:
```bash
transcribe --list-devices
```

**Use specific microphone**:
```bash
transcribe --device 2 --duration 15
```

**Force language detection**:
```bash
transcribe audio.wav --language es
```

**Record and save with timestamps (SRT format)**:
```bash
transcribe --duration 30 --format srt --output subtitles.srt
```

**Verbose output for debugging**:
```bash
transcribe input.wav --verbose
```

## Microphone Permissions

### Linux
No special permissions typically needed. If you encounter issues:
```bash
# Add user to audio group
sudo usermod -a -G audio $USER
# Log out and log back in
```

### macOS
1. Go to **System Preferences** → **Security & Privacy** → **Privacy** → **Microphone**
2. Ensure **Terminal** (or your terminal app) has microphone access
3. You may need to restart your terminal after granting permission

### Windows
1. Go to **Settings** → **Privacy** → **Microphone**
2. Enable "Allow apps to access your microphone"
3. Enable "Allow desktop apps to access your microphone"

## Output Formats

### Text (Default)
Plain text transcription:
```
Hello, this is a test transcription from the audio file.
```

### JSON
Structured output with metadata and segments:
```json
{
  "text": "Hello, this is a test.",
  "language": "en",
  "language_probability": 0.98,
  "duration": 5.0,
  "segments": [...]
}
```

### SRT (SubRip Subtitles)
```
1
00:00:00,000 --> 00:00:03,500
Hello, this is a test

2
00:00:03,500 --> 00:00:05,000
transcription.
```

### VTT (WebVTT)
```
WEBVTT

00:00:00.000 --> 00:00:03.500
Hello, this is a test
```

## Configuration

### Environment Variables

- `WHISPER_MODEL_PATH`: Custom directory for model cache (default: `~/.cache/whisper/`)
- `WHISPER_MODEL`: Model name override (default: `tiny`)
- `WHISPER_LANGUAGE`: Default language code

Example:
```bash
export WHISPER_MODEL_PATH=/custom/path/to/models
export WHISPER_LANGUAGE=en
transcribe input.wav
```

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Audio device or file error |
| 3 | Model loading or inference error |
| 4 | Invalid configuration or arguments |

## Troubleshooting

### PyAudio installation fails

**Linux**:
```bash
sudo apt-get install python3-dev portaudio19-dev
pip install pyaudio
```

**macOS**:
```bash
brew install portaudio
pip install pyaudio
```

**Windows**:
```bash
pip install pipwin
pipwin install pyaudio
```

### Whisper model download fails

The Whisper tiny model (~39MB) is automatically downloaded on first use. If download fails:

```bash
# Manual download
mkdir -p ~/.cache/whisper
cd ~/.cache/whisper
wget https://openaipublic.azureedge.net/main/whisper/models/65147644a518d12f04e32d6f3b26facc3f8dd46e5390956a9424a650c0ce22b9/tiny.pt
```

### Microphone not detected

**Linux**:
```bash
# Check ALSA devices
arecord -l

# Test recording
arecord -d 5 test.wav
```

**macOS**: Check System Preferences → Security & Privacy → Microphone permissions

### Audio quality issues

For better quality, ensure:
- Microphone is not muted
- Recording environment is quiet
- Microphone is positioned correctly
- Audio file format is supported (WAV, MP3, FLAC)

## Performance

- **Transcription Speed**: ~2-5x realtime on modern CPUs (2020+)
- **Memory Usage**: ~200MB during inference
- **Model Size**: ~39MB (Whisper tiny)
- **Maximum Audio Length**: 30 minutes per transcription

## Development

See `specs/001-audio-transcription-cli/quickstart.md` for development setup.

## License

MIT License - see LICENSE file for details

## Acknowledgments

- Built with [OpenAI Whisper](https://github.com/openai/whisper)
- Uses [PyAudio](http://people.csail.mit.edu/hubert/pyaudio/) for audio capture
- CLI powered by [Click](https://click.palletsprojects.com/)

## Support

For issues, questions, or contributions, please open an issue on GitHub.
