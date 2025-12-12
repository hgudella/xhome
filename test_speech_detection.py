"""Quick test script to verify speech detection and language parameter."""

import numpy as np
from src.audio.vad import VoiceActivityDetector
from src.transcription.whisper_engine import WhisperEngine

print("Testing VAD and Whisper with new changes...")
print()

# Test 1: VAD with synthetic audio
print("1. Testing VAD confidence scores...")
vad = VoiceActivityDetector(sample_rate=16000, threshold=0.7)

# Silent audio
silence = np.zeros(512, dtype=np.float32)
confidence_silence = vad.get_speech_confidence(silence, 16000)
print(f"   Silence confidence: {confidence_silence:.3f}")

# Random noise (simulating background)
noise = np.random.randn(512).astype(np.float32) * 0.01
confidence_noise = vad.get_speech_confidence(noise, 16000)
print(f"   Noise confidence: {confidence_noise:.3f}")

# Stronger signal (simulating speech)
speech_like = np.random.randn(512).astype(np.float32) * 0.5
confidence_speech = vad.get_speech_confidence(speech_like, 16000)
print(f"   Speech-like confidence: {confidence_speech:.3f}")
print()

# Test 2: Whisper with language='en'
print("2. Testing Whisper with language='en'...")
print("   (This should NOT show multilingual warnings)")
engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")

# Create 1 second of random audio
test_audio = np.random.randn(16000).astype(np.float32) * 0.1
transcription = engine.transcribe(test_audio, sample_rate=16000)

print(f"   Transcription completed: '{transcription.text}'")
print(f"   Language: {transcription.language}")
print(f"   Confidence: {transcription.confidence}")
print()

print("✅ All tests completed!")
print()
print("Now try running: python main.py --continuous --vad-threshold 0.7")
print("You should see:")
print("  🎤 Speech detected (confidence: X.XXX)")
print("  ⏸️  Speech ended (...)")
print("  📝 [N] <your actual words>")
