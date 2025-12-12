"""Diagnose Whisper transcription issues with real microphone audio."""

import numpy as np
import sounddevice as sd
from src.transcription.whisper_engine import WhisperEngine

print("=" * 70)
print("🔍 Whisper Transcription Diagnostic")
print("=" * 70)
print()
print("This will record 3 seconds of audio and show you what Whisper hears.")
print("When you see 'Recording...', SPEAK LOUDLY and CLEARLY:")
print("  Example: 'TESTING ONE TWO THREE FOUR FIVE'")
print()

sample_rate = 16000
duration = 3.0

input("Press ENTER when ready to record...")
print()
print("🔴 Recording for 3 seconds... SPEAK NOW!")

# Record audio
audio_data = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype=np.float32
)
sd.wait()

print("✓ Recording complete!")
print()

# Calculate audio statistics
audio_flat = audio_data.flatten()
audio_level = float(np.abs(audio_flat).mean())
audio_max = float(np.abs(audio_flat).max())
audio_rms = float(np.sqrt(np.mean(audio_flat**2)))

print(f"📊 Audio Statistics:")
print(f"   Mean level: {audio_level:.4f}")
print(f"   RMS level:  {audio_rms:.4f}")
print(f"   Peak level: {audio_max:.4f}")
print()

if audio_level < 0.01:
    print("⚠️  WARNING: Audio level very low (< 0.01)")
    print("   Microphone may be muted or volume too low")
    print("   Transcription will likely fail")
elif audio_level < 0.03:
    print("⚠️  CAUTION: Audio level low (< 0.03)")
    print("   Speak louder or increase microphone volume")
elif audio_level > 0.15:
    print("✅ EXCELLENT: Strong audio signal!")
else:
    print("✅ GOOD: Audio level acceptable")
print()

# Transcribe
print("🤖 Loading Whisper model...")
engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
print()

print("🎯 Transcribing audio...")
transcription = engine.transcribe(audio_flat, sample_rate=sample_rate)
print()

print("=" * 70)
print("📝 TRANSCRIPTION RESULT:")
print("=" * 70)
print(f"Text: '{transcription.text}'")
print(f"Length: {len(transcription.text)} characters")
print(f"Confidence: {transcription.confidence}")
print(f"Language: {transcription.language}")
print("=" * 70)
print()

if len(transcription.text) < 5:
    print("❌ PROBLEM: Transcription too short!")
    print()
    print("Possible causes:")
    print("  1. Microphone volume too low")
    print("  2. Not speaking during recording")
    print("  3. Microphone not selected as default input")
    print("  4. Audio not reaching Whisper correctly")
    print()
    print("Next steps:")
    print("  1. Run: python test_microphone.py")
    print("     - Verify levels are 0.02-0.10 when speaking")
    print("  2. Check Windows Sound Settings")
    print("     - Ensure correct microphone is selected")
    print("     - Increase input volume/boost")
    print("  3. Try again with LOUDER speech")
elif "you" in transcription.text.lower() and len(transcription.text) < 10:
    print("⚠️  ISSUE: Whisper defaulting to 'you'")
    print()
    print("This typically means:")
    print("  - Audio is present but too quiet")
    print("  - No clear speech detected in the audio")
    print()
    print("Solutions:")
    print("  1. Speak MUCH LOUDER")
    print("  2. Get closer to microphone")
    print("  3. Increase microphone boost to +20dB or +30dB")
else:
    print("✅ SUCCESS: Real transcription detected!")
    print()
    print("Your setup is working! Now try:")
    print("  python main.py --continuous --vad-threshold 0.7")
