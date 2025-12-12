"""Test with a larger Whisper model for better accuracy."""

import numpy as np
import soundfile as sf
from src.transcription.whisper_engine import WhisperEngine

print("=" * 70)
print("🎯 Testing Whisper with Recorded Audio")
print("=" * 70)
print()

# Load the saved recording
filename = "test_recording.wav"
try:
    audio_data, sample_rate = sf.read(filename)
    print(f"✓ Loaded {filename}")
    print(f"  Duration: {len(audio_data) / sample_rate:.1f}s")
    print(f"  Sample rate: {sample_rate} Hz")
    print()
except FileNotFoundError:
    print(f"❌ File not found: {filename}")
    print("   Run: python test_record_save.py first")
    exit(1)

# Flatten if stereo
if audio_data.ndim > 1:
    audio_data = audio_data[:, 0]

# Calculate levels
audio_level = float(np.abs(audio_data).mean())
audio_max = float(np.abs(audio_data).max())
print(f"📊 Audio levels:")
print(f"   Mean: {audio_level:.4f}")
print(f"   Peak: {audio_max:.4f}")
print()

# Try with Whisper Tiny (current)
print("🤖 Testing with Whisper Tiny (current model)...")
engine_tiny = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
transcription_tiny = engine_tiny.transcribe(audio_data, sample_rate=sample_rate)
print(f"   Result: '{transcription_tiny.text}'")
print(f"   Length: {len(transcription_tiny.text)} chars")
print()

# Try with Whisper Base (larger, more accurate)
print("🤖 Testing with Whisper Base (larger model)...")
print("   (This will download ~150MB model on first run)")
engine_base = WhisperEngine(model_name="openai/whisper-base", device="cpu")
transcription_base = engine_base.transcribe(audio_data, sample_rate=sample_rate)
print(f"   Result: '{transcription_base.text}'")
print(f"   Length: {len(transcription_base.text)} chars")
print()

print("=" * 70)
print("📋 COMPARISON:")
print("=" * 70)
print(f"Tiny:  '{transcription_tiny.text}'")
print(f"Base:  '{transcription_base.text}'")
print("=" * 70)
print()

if len(transcription_base.text) > len(transcription_tiny.text):
    print("✅ Base model produced better results!")
    print("   Update main.py to use 'openai/whisper-base' instead of 'whisper-tiny'")
else:
    print("⚠️  Both models struggling with this audio")
    print("   Possible solutions:")
    print("   1. Increase Windows microphone boost to +30dB")
    print("   2. Speak MUCH louder")
    print("   3. Get closer to microphone")
    print("   4. Use a different microphone (not Remote Audio)")
