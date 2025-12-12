#!/usr/bin/env python3
"""
Demo script showing main.py usage without requiring actual microphone.

Uses synthetic audio to demonstrate the pipeline.
"""

import numpy as np
from src.audio.buffer import AudioBuffer
from src.transcription.whisper_engine import WhisperEngine
from src.utils.config import Config
from src.utils.logging import get_logger


logger = get_logger(__name__)


def create_demo_audio(duration_seconds: float = 3.0, sample_rate: int = 16000) -> np.ndarray:
    """
    Create synthetic audio for demo purposes.
    
    Args:
        duration_seconds: Length of audio
        sample_rate: Sample rate in Hz
        
    Returns:
        Audio data as numpy array
    """
    # Create a simple sine wave (440 Hz - A4 note)
    t = np.linspace(0, duration_seconds, int(sample_rate * duration_seconds), dtype=np.float32)
    frequency = 440.0
    audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)
    
    return audio_data


def main():
    """Run demo without microphone."""
    print("\n" + "=" * 60)
    print("🏠 Home Automation Assistant - Voice-to-Text Demo")
    print("=" * 60)
    print("Using synthetic audio (no microphone required)")
    print("=" * 60 + "\n")
    
    # Load configuration
    config = Config()
    
    # Initialize engine
    print("🔧 Initializing Whisper engine...")
    engine = WhisperEngine(
        model_name=config.whisper_model_name,
        device=config.whisper_device
    )
    print(f"✅ Model loaded: {engine.model_name} on {engine.device}\n")
    
    # Create demo audio
    print("🎵 Creating synthetic audio (3 seconds)...")
    audio_data = create_demo_audio(duration_seconds=3.0, sample_rate=16000)
    
    # Create buffer
    buffer = AudioBuffer(
        audio_data=audio_data,
        sample_rate=16000
    )
    print(f"✅ Audio buffer created: {buffer.duration_seconds:.2f}s, {buffer.frame_count} frames\n")
    
    # Transcribe
    print("🔄 Transcribing audio...")
    try:
        transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
        
        print(f"✅ Transcription completed!\n")
        print(f"📝 Text: {transcription.text}")
        print(f"💯 Confidence: {transcription.confidence:.2f}")
        print(f"⏱️  Audio duration: {transcription.audio_duration_seconds:.2f}s")
        print(f"🌍 Language: {transcription.language}")
        print(f"🤖 Model: {transcription.model_name}\n")
        
    except Exception as e:
        print(f"❌ Transcription failed: {e}\n")
    
    # Clear buffer (privacy)
    buffer.clear()
    print("🔒 Audio buffer cleared (0-day retention)\n")
    
    print("=" * 60)
    print("Demo complete! To use with real microphone, run:")
    print("  python main.py")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
