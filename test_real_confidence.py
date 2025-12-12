"""Test continuous listening with real mic for 30 seconds"""
import sys
sys.path.insert(0, 'c:/Users/hgudella/source/personal/xhome')

from src.audio.continuous import ContinuousListener
from src.transcription.whisper_engine import WhisperEngine
from src.vad.silero import VoiceActivityDetector
from src.audio.capture import AudioStream
import time

# Create components
print("Loading models...")
whisper = WhisperEngine(model_name="openai/whisper-base")
vad = VoiceActivityDetector()
audio = AudioStream()

# Create listener
listener = ContinuousListener(
    whisper_engine=whisper,
    vad=vad,
    audio_stream=audio,
    vad_threshold=0.7,
    silence_duration=0.5
)

# Start listening
print("\n🎤 Listening for 30 seconds... Speak something!\n")
listener.start()

# Wait
time.sleep(30)

# Stop
listener.stop()
print("\n✅ Done! Check the output above for varying confidence scores.")
