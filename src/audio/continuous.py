"""
Continuous listening mode with Voice Activity Detection.

Listens continuously, detects speech boundaries, and transcribes complete utterances.
"""

import numpy as np
import threading
import queue
import time
from typing import Optional, Callable

from src.audio.capture import AudioStream
from src.audio.buffer import AudioBuffer
from src.audio.vad import VoiceActivityDetector
from src.transcription.whisper_engine import WhisperEngine
from src.transcription.transcriber import Transcription
from src.utils.logging import get_logger
from src.utils.exceptions import AudioCaptureError, TranscriptionError


logger = get_logger(__name__)


class ContinuousListener:
    """
    Continuous listening mode with VAD-based speech detection.
    
    Continuously captures audio, detects speech boundaries using VAD,
    and transcribes complete utterances without losing words.
    
    Features:
    - Always-on microphone (no gaps between utterances)
    - Automatic speech start/end detection
    - No word loss at boundaries
    - Privacy-compliant (0-day retention)
    
    Attributes:
        stream: Audio stream for capture
        vad: Voice activity detector
        engine: Whisper transcription engine
        is_running: Whether actively listening
        on_transcription: Callback for completed transcriptions
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        vad_threshold: float = 0.5,
        model_name: str = "openai/whisper-tiny",
        device: str = "cpu",
        on_transcription: Optional[Callable[[Transcription], None]] = None
    ):
        """
        Initialize ContinuousListener.
        
        Args:
            sample_rate: Audio sample rate (Hz)
            vad_threshold: VAD confidence threshold (0.0-1.0)
            model_name: Whisper model name
            device: Device for transcription (cpu/cuda)
            on_transcription: Callback for completed transcriptions
        """
        self.sample_rate = sample_rate
        self.is_running = False
        self.on_transcription = on_transcription
        
        logger.info(
            "Initializing ContinuousListener",
            sample_rate=sample_rate,
            vad_threshold=vad_threshold,
            model_name=model_name,
            device=device
        )
        
        # Initialize components
        self.stream = AudioStream(sample_rate=sample_rate)
        self.vad = VoiceActivityDetector(threshold=vad_threshold)
        self.engine = WhisperEngine(model_name=model_name, device=device)
        
        # Audio processing
        self.audio_queue = queue.Queue()
        self.processing_thread = None
        
        # Speech detection state
        self.is_speech_active = False
        self.speech_chunks = []
        self.silence_duration = 0.0
        self.silence_threshold = 0.5  # seconds of silence to end utterance
        
        logger.info("ContinuousListener initialized successfully")
    
    def start(self):
        """
        Start continuous listening mode.
        
        Starts microphone capture and speech detection.
        """
        if self.is_running:
            logger.warning("ContinuousListener already running")
            return
        
        logger.info("Starting continuous listening")
        
        self.is_running = True
        self.vad.reset()
        
        # Start processing thread
        self.processing_thread = threading.Thread(
            target=self._process_audio_loop,
            daemon=True
        )
        self.processing_thread.start()
        
        # Start audio capture
        self.stream.start(audio_callback=self._audio_callback)
        
        logger.info("Continuous listening started")
    
    def stop(self):
        """
        Stop continuous listening mode.
        
        Stops microphone capture and processing.
        """
        if not self.is_running:
            return
        
        logger.info("Stopping continuous listening")
        
        self.is_running = False
        
        # Stop audio capture
        if self.stream.state == "listening":
            self.stream.stop()
        
        # Wait for processing thread
        if self.processing_thread:
            self.processing_thread.join(timeout=2.0)
        
        logger.info("Continuous listening stopped")
    
    def _audio_callback(self, indata, frames, time_info, status):
        """
        Audio capture callback.
        
        Receives audio chunks from microphone and queues for processing.
        """
        if status:
            logger.warning("Audio stream status", status=str(status))
        
        # Queue audio for processing
        if self.is_running:
            self.audio_queue.put(indata.copy())
    
    def _process_audio_loop(self):
        """
        Audio processing loop (runs in separate thread).
        
        Processes audio chunks, detects speech boundaries, and triggers transcription.
        """
        logger.info("Audio processing loop started")
        
        # Silero VAD expects 512 samples for 16kHz (32ms chunks)
        chunk_size = 512 if self.sample_rate == 16000 else 256
        chunk_duration = chunk_size / self.sample_rate
        
        accumulated_audio = []
        
        while self.is_running:
            try:
                # Get audio chunk (with timeout to allow checking is_running)
                try:
                    audio_chunk = self.audio_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Flatten audio
                audio_data = audio_chunk.flatten().astype(np.float32)
                
                # Normalize if int16
                if audio_chunk.dtype == np.int16:
                    audio_data = audio_data / 32768.0
                
                # Accumulate audio for processing
                accumulated_audio.append(audio_data)
                
                # Process when we have enough samples
                total_samples = sum(len(chunk) for chunk in accumulated_audio)
                
                while total_samples >= chunk_size:
                    # Combine accumulated audio
                    combined = np.concatenate(accumulated_audio)
                    
                    # Extract one chunk for VAD
                    vad_chunk = combined[:chunk_size]
                    
                    # Keep remainder
                    if len(combined) > chunk_size:
                        accumulated_audio = [combined[chunk_size:]]
                        total_samples = len(combined) - chunk_size
                    else:
                        accumulated_audio = []
                        total_samples = 0
                    
                    # Detect speech
                    is_speech = self.vad.is_speech(vad_chunk, self.sample_rate)
                    confidence = self.vad.get_speech_confidence(vad_chunk, self.sample_rate)
                    
                    if is_speech:
                        # Speech detected
                        if not self.is_speech_active:
                            # Speech started
                            audio_level = float(np.abs(vad_chunk).mean())
                            audio_max = float(np.abs(vad_chunk).max())
                            print(f"🎤 Speech detected (confidence: {confidence:.3f}, level: {audio_level:.4f}, max: {audio_max:.4f})")
                            logger.info(f"Speech started (confidence: {confidence:.3f}, audio_level: {audio_level:.4f})")
                            self.is_speech_active = True
                            self.speech_chunks = []
                            self.silence_duration = 0.0
                        
                        # Accumulate speech
                        self.speech_chunks.append(vad_chunk)
                        self.silence_duration = 0.0
                    
                    else:
                        # Silence detected
                        if self.is_speech_active:
                            # Track silence duration
                            self.silence_duration += chunk_duration
                            
                            # Still accumulate (might be brief pause)
                            self.speech_chunks.append(vad_chunk)
                            
                            # Check if silence long enough to end utterance
                            if self.silence_duration >= self.silence_threshold:
                                # Speech ended - transcribe
                                print(f"⏸️  Speech ended ({len(self.speech_chunks)} chunks, {self.silence_duration:.1f}s silence)")
                                logger.info(
                                    f"Speech ended (silence: {self.silence_duration:.2f}s, "
                                    f"chunks: {len(self.speech_chunks)})"
                                )
                                self._transcribe_utterance()
                                
                                # Reset state
                                self.is_speech_active = False
                                self.speech_chunks = []
                                self.silence_duration = 0.0
            
            except Exception as e:
                logger.error("Error in audio processing loop", error=str(e))
        
        logger.info("Audio processing loop stopped")
    
    def _transcribe_utterance(self):
        """
        Transcribe accumulated speech chunks.
        
        Combines speech chunks, transcribes, and calls callback.
        """
        if not self.speech_chunks:
            return
        
        try:
            # Combine all speech chunks
            combined_audio = np.concatenate(self.speech_chunks)
            
            # Calculate audio statistics (convert to Python float for JSON serialization)
            audio_level = float(np.abs(combined_audio).mean())
            audio_max = float(np.abs(combined_audio).max())
            audio_rms = float(np.sqrt(np.mean(combined_audio**2)))
            
            # Create buffer
            buffer = AudioBuffer(
                audio_data=combined_audio,
                sample_rate=self.sample_rate
            )
            
            print(f"🎙️  Transcribing {buffer.duration_seconds:.1f}s audio (level: {audio_level:.4f}, rms: {audio_rms:.4f}, max: {audio_max:.4f})")
            logger.info(
                "Transcribing utterance",
                buffer_id=str(buffer.buffer_id),
                duration_seconds=buffer.duration_seconds,
                audio_level=audio_level,
                audio_rms=audio_rms
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
            
            # Clear buffer (privacy)
            buffer.clear()
            
            # Call callback
            if self.on_transcription:
                self.on_transcription(transcription)
        
        except TranscriptionError as e:
            logger.error("Transcription failed", error=str(e))
        
        except Exception as e:
            logger.error("Unexpected error during transcription", error=str(e))
