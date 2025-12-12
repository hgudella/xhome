#!/usr/bin/env python3
"""
Home Automation Assistant - Voice-to-Text Entry Point

Captures voice input from microphone and transcribes to text using Whisper.
Implements 0-day audio retention for privacy compliance.

Modes:
- Single-shot: Capture for fixed duration, then transcribe
- Continuous: VAD-based continuous listening with automatic speech detection
"""

import argparse
import signal
import sys
import time
from typing import Optional

from src.audio.capture import AudioStream
from src.audio.buffer import AudioBuffer
from src.audio.continuous import ContinuousListener
from src.transcription.whisper_engine import WhisperEngine
from src.transcription.transcriber import Transcription
from src.utils.config import Config
from src.utils.logging import get_logger
from src.utils.exceptions import AudioCaptureError, TranscriptionError


logger = get_logger(__name__)


class VoiceToTextApp:
    """
    Main application for voice-to-text transcription.
    
    Coordinates audio capture and speech-to-text pipeline.
    """
    
    def __init__(
        self,
        config: Config,
        model_name: Optional[str] = None,
        device: Optional[str] = None
    ):
        """
        Initialize VoiceToTextApp.
        
        Args:
            config: Application configuration
            model_name: Override Whisper model name
            device: Override device (cpu/cuda)
        """
        self.config = config
        self.running = False
        
        # Initialize components
        logger.info("Initializing Voice-to-Text application")
        
        self.stream = AudioStream(
            sample_rate=config.audio_sample_rate,
            channels=config.audio_channels,
            buffer_size=config.audio_buffer_size
        )
        
        self.engine = WhisperEngine(
            model_name=model_name or config.whisper_model_name,
            device=device or config.whisper_device
        )
        
        self.captured_audio = []
        
        logger.info(
            "Application initialized",
            sample_rate=config.audio_sample_rate,
            model=self.engine.model_name,
            device=self.engine.device
        )
    
    def audio_callback(self, indata, frames, time_info, status):
        """
        Callback for audio stream capture.
        
        Args:
            indata: Audio data
            frames: Number of frames
            time_info: Timing information
            status: Stream status
        """
        if status:
            logger.warning("Audio stream status", status=str(status))
        
        # Store captured audio
        self.captured_audio.append(indata.copy())
    
    def capture_and_transcribe(self, duration_seconds: float = 3.0) -> str:
        """
        Capture audio for specified duration and transcribe.
        
        Args:
            duration_seconds: How long to capture audio
            
        Returns:
            Transcribed text
            
        Raises:
            AudioCaptureError: If capture fails
            TranscriptionError: If transcription fails
        """
        logger.info("Starting capture", duration_seconds=duration_seconds)
        
        # Clear previous audio
        self.captured_audio = []
        
        # Start capture
        self.stream.start(audio_callback=self.audio_callback)
        
        # Capture for duration
        time.sleep(duration_seconds)
        
        # Stop capture
        self.stream.stop()
        
        # Check if audio was captured
        if not self.captured_audio:
            raise AudioCaptureError("No audio captured")
        
        # Create buffer
        import numpy as np
        combined_audio = np.concatenate(self.captured_audio, axis=0).flatten()
        buffer = AudioBuffer.create_from_stream(self.stream, combined_audio)
        
        logger.info(
            "Audio captured",
            buffer_id=str(buffer.buffer_id),
            duration_seconds=buffer.duration_seconds,
            frame_count=buffer.frame_count
        )
        
        # Transcribe
        transcription = self.engine.transcribe(
            buffer.audio_data,
            buffer.sample_rate
        )
        
        logger.info(
            "Transcription completed",
            transcription_id=str(transcription.transcription_id),
            confidence=transcription.confidence,
            text_length=len(transcription.text)
        )
        
        # Clear buffer (0-day retention)
        buffer.clear()
        logger.info("Audio buffer cleared (0-day retention)")
        
        return transcription.text
    
    def run_single_capture(self, duration_seconds: float = 3.0):
        """
        Run single capture-transcribe cycle.
        
        Args:
            duration_seconds: How long to capture audio
        """
        try:
            print(f"\n🎤 Listening for {duration_seconds} seconds...")
            print("Speak now!\n")
            
            text = self.capture_and_transcribe(duration_seconds)
            
            print(f"📝 Transcription: {text}\n")
            
        except AudioCaptureError as e:
            logger.error("Audio capture failed", error=str(e))
            print(f"❌ Audio capture failed: {e}")
            
        except TranscriptionError as e:
            logger.error("Transcription failed", error=str(e))
            print(f"❌ Transcription failed: {e}")
            
        except Exception as e:
            logger.error("Unexpected error", error=str(e))
            print(f"❌ Unexpected error: {e}")
    
    def run_continuous(self, duration_seconds: float = 3.0, vad_threshold: float = 0.5):
        """
        Run continuous VAD-based listening mode.
        
        Uses Voice Activity Detection to automatically detect speech boundaries.
        No word loss between utterances.
        
        Args:
            duration_seconds: Ignored (kept for compatibility)
            vad_threshold: VAD sensitivity (0.0-1.0, higher = less sensitive)
        """
        print("\n🎙️  Continuous Voice-to-Text Mode (VAD-based)")
        print("Automatically detects when you speak")
        print("No gaps - speaks continuously without losing words!")
        print(f"VAD Threshold: {vad_threshold} (higher = less sensitive)")
        print("Press Ctrl+C to stop\n")
        
        transcription_count = 0
        
        def on_transcription(transcription: Transcription):
            """Callback for completed transcriptions."""
            nonlocal transcription_count
            transcription_count += 1
            
            print(f"📝 [{transcription_count}] {transcription.text}")
            print(f"   ⏱️  {transcription.audio_duration_seconds:.1f}s | 💯 {transcription.confidence:.2f}\n")
        
        # Create continuous listener
        listener = ContinuousListener(
            sample_rate=self.config.audio_sample_rate,
            vad_threshold=vad_threshold,
            model_name=self.config.whisper_model_name,
            device=self.config.whisper_device,
            on_transcription=on_transcription
        )
        
        try:
            listener.start()
            
            # Keep running until interrupted
            while True:
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Stopping...")
        
        finally:
            listener.stop()
            print(f"\n✅ Total transcriptions: {transcription_count}")
    
    def run_continuous_legacy(self, duration_seconds: float = 3.0):
        """
        Run continuous capture-transcribe loop (legacy chunk-based mode).
        
        This is the old implementation with fixed-duration chunks.
        Kept for compatibility. Use run_continuous() for better experience.
        
        Args:
            duration_seconds: How long to capture each cycle
        """
        self.running = True
        
        print("\n🎙️  Continuous Voice-to-Text Mode")
        print(f"Capturing {duration_seconds} second clips")
        print("Press Ctrl+C to stop\n")
        
        cycle = 0
        
        while self.running:
            cycle += 1
            
            try:
                print(f"🎤 Cycle {cycle}: Listening...")
                
                text = self.capture_and_transcribe(duration_seconds)
                
                print(f"📝 {text}\n")
                
            except AudioCaptureError as e:
                logger.error("Audio capture failed", error=str(e), cycle=cycle)
                print(f"❌ Capture failed: {e}\n")
                
            except TranscriptionError as e:
                logger.error("Transcription failed", error=str(e), cycle=cycle)
                print(f"❌ Transcription failed: {e}\n")
                
            except Exception as e:
                logger.error("Unexpected error", error=str(e), cycle=cycle)
                print(f"❌ Error: {e}\n")
                break
    
    def stop(self):
        """Stop continuous capture."""
        self.running = False
        if self.stream.state == "listening":
            self.stream.stop()
        logger.info("Application stopped")
        print("\n👋 Stopped")
    
    def cleanup(self):
        """Cleanup resources."""
        if self.stream.state == "listening":
            self.stream.stop()
        logger.info("Application cleanup complete")


def signal_handler(signum, frame):
    """Handle interrupt signal."""
    print("\n\n⚠️  Interrupt received...")
    sys.exit(0)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Home Automation Assistant - Voice-to-Text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Single capture (3 seconds)
  python main.py

  # Single capture (5 seconds)
  python main.py --duration 5

  # Continuous mode with VAD (recommended - no word loss!)
  python main.py --continuous

  # Legacy continuous mode (old chunk-based behavior)
  python main.py --continuous --legacy --duration 5

  # Use different model
  python main.py --model openai/whisper-base

  # Use GPU
  python main.py --device cuda
        """
    )
    
    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run in continuous VAD-based listening mode (automatic speech detection)"
    )
    
    parser.add_argument(
        "--legacy",
        action="store_true",
        help="Use legacy chunk-based continuous mode (old behavior)"
    )
    
    parser.add_argument(
        "--vad-threshold",
        type=float,
        default=0.5,
        help="VAD sensitivity (0.0-1.0, default: 0.5, higher = less sensitive)"
    )
    
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Capture duration in seconds (default: 3.0)"
    )
    
    parser.add_argument(
        "--model",
        type=str,
        default=None,
        help="Whisper model name (default: from config)"
    )
    
    parser.add_argument(
        "--device",
        type=str,
        choices=["cpu", "cuda"],
        default=None,
        help="Device for inference (default: from config)"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set up signal handler
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        # Load configuration
        config = Config()
        
        if args.verbose:
            import logging
            logging.root.setLevel(logging.DEBUG)
        
        # Create application
        app = VoiceToTextApp(
            config=config,
            model_name=args.model,
            device=args.device
        )
        
        print("\n" + "=" * 60)
        print("🏠 Home Automation Assistant - Voice-to-Text")
        print("=" * 60)
        print(f"Model: {app.engine.model_name}")
        print(f"Device: {app.engine.device}")
        print(f"Sample Rate: {app.stream.sample_rate} Hz")
        print("=" * 60)
        
        # Run application
        try:
            if args.continuous:
                if args.legacy:
                    print("\n⚠️  Using legacy chunk-based mode\n")
                    app.run_continuous_legacy(duration_seconds=args.duration)
                else:
                    app.run_continuous(
                        duration_seconds=args.duration,
                        vad_threshold=args.vad_threshold
                    )
            else:
                app.run_single_capture(duration_seconds=args.duration)
        
        except KeyboardInterrupt:
            print("\n\n⚠️  Keyboard interrupt received")
            app.stop()
        
        finally:
            app.cleanup()
        
        print("\n✅ Application exited successfully")
        return 0
        
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        print(f"\n❌ Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
