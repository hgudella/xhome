"""Save recorded audio to file for analysis."""

import numpy as np
import sounddevice as sd
import soundfile as sf
from datetime import datetime

print("=" * 70)
print("💾 Audio Recording & Save Test")
print("=" * 70)
print()
print("This will record 5 seconds and save to test_recording.wav")
print("You can play it back to verify your voice was captured.")
print()

sample_rate = 16000
duration = 5.0

input("Press ENTER to start recording...")
print()
print("🔴 RECORDING FOR 5 SECONDS...")
print("   SPEAK LOUDLY: 'Testing one two three four five'")
print("   COUNT TO TEN")
print("   SAY YOUR NAME")
print()

# Record
audio_data = sd.rec(
    int(duration * sample_rate),
    samplerate=sample_rate,
    channels=1,
    dtype=np.float32
)
sd.wait()

print("✓ Recording complete!")
print()

# Save to file
filename = "test_recording.wav"
sf.write(filename, audio_data, sample_rate)
print(f"💾 Saved to: {filename}")
print()

# Calculate statistics
audio_flat = audio_data.flatten()
audio_level = float(np.abs(audio_flat).mean())
audio_max = float(np.abs(audio_flat).max())
audio_rms = float(np.sqrt(np.mean(audio_flat**2)))

print(f"📊 Audio Statistics:")
print(f"   Mean level: {audio_level:.4f}")
print(f"   RMS level:  {audio_rms:.4f}")
print(f"   Peak level: {audio_max:.4f}")
print()

print("🎧 Next steps:")
print(f"   1. Open {filename} in Windows Media Player or VLC")
print("   2. Play it back - can you hear your voice?")
print()
print("   If YES: Voice is being captured, continue to step 3")
print(f"   If NO:  Microphone issue - check Windows Sound Settings")
print()
print("   3. If you can hear yourself, the issue is with Whisper processing")
print("      Try: python main.py --continuous --vad-threshold 0.7")
