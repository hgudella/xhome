"""Test one transcription"""
import sys
sys.path.insert(0, 'c:/Users/hgudella/source/personal/xhome')

from src.transcription.whisper_engine import WhisperEngine
import numpy as np

# Create engine
engine = WhisperEngine(model_name="openai/whisper-base")

# Generate 2 seconds of silence (will detect as speech with VAD in real app)
audio = np.zeros(32000, dtype=np.float32)

# Transcribe
print("Transcribing...")
result = engine.transcribe(audio, sample_rate=16000)
print(f"\n✅ Text: '{result.text}'")
print(f"✅ Confidence: {result.confidence}")
print(f"✅ Duration: {result.audio_duration_seconds}s")
