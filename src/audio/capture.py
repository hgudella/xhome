"""AudioStream implementation for real-time audio capture."""

import sounddevice as sd
import numpy as np
from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional, Callable
from ..utils.exceptions import AudioCaptureError, ValidationError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class AudioStream:
    """
    Represents continuous audio stream from microphone input device.
    
    Manages audio capture using sounddevice library with callback-based streaming.
    Implements state transitions and validation per data-model.md.
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        buffer_size: int = 1024,
        device_index: Optional[int] = None
    ):
        """
        Initialize AudioStream.
        
        Args:
            sample_rate: Audio sample rate in Hz (default: 16000 for Whisper)
            channels: Number of audio channels (default: 1 for mono)
            buffer_size: Size of audio buffer in frames (default: 1024)
            device_index: Audio input device index (None = default device)
        """
        self.stream_id: UUID = uuid4()
        self.sample_rate: int = sample_rate
        self.channels: int = channels
        self.buffer_size: int = buffer_size
        self.audio_format: str = "int16"
        self.state: str = "stopped"
        self.device_index: Optional[int] = device_index
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        
        self._sd_stream: Optional[sd.InputStream] = None
        self._audio_callback: Optional[Callable] = None
        
        logger.debug(
            "AudioStream initialized",
            stream_id=str(self.stream_id),
            sample_rate=self.sample_rate,
            channels=self.channels,
            buffer_size=self.buffer_size
        )
    
    def start(self, audio_callback: Optional[Callable] = None) -> None:
        """
        Start audio capture.
        
        Args:
            audio_callback: Optional callback function(indata, frames, time, status)
        
        Raises:
            AudioCaptureError: If stream already running or device access fails
        """
        if self.state == "listening":
            raise AudioCaptureError(
                f"Stream {self.stream_id} is already running"
            )
        
        try:
            self._audio_callback = audio_callback
            
            self._sd_stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.audio_format,
                blocksize=self.buffer_size,
                device=self.device_index,
                callback=self._internal_callback if audio_callback else None
            )
            
            self._sd_stream.start()
            self.state = "listening"
            self.started_at = datetime.utcnow()
            
            logger.info(
                "AudioStream started",
                stream_id=str(self.stream_id),
                device_index=self.device_index,
                timestamp=self.started_at.isoformat()
            )
            
        except Exception as e:
            self._set_error_state(str(e))
            
            if "permission" in str(e).lower() or "access" in str(e).lower():
                raise AudioCaptureError(
                    f"Microphone access denied: {e}"
                )
            elif "device" in str(e).lower():
                raise AudioCaptureError(
                    f"Invalid audio device (index={self.device_index}): {e}"
                )
            else:
                raise AudioCaptureError(
                    f"Failed to start audio stream: {e}"
                )
    
    def stop(self) -> None:
        """
        Stop audio capture.
        
        Raises:
            AudioCaptureError: If stop operation fails
        """
        if self.state != "listening":
            logger.warning(
                "Attempted to stop non-running stream",
                stream_id=str(self.stream_id),
                current_state=self.state
            )
            return
        
        try:
            if self._sd_stream:
                self._sd_stream.stop()
                self._sd_stream.close()
                self._sd_stream = None
            
            self.state = "stopped"
            self.stopped_at = datetime.utcnow()
            
            duration = (self.stopped_at - self.started_at).total_seconds()
            
            logger.info(
                "AudioStream stopped",
                stream_id=str(self.stream_id),
                duration_seconds=duration,
                timestamp=self.stopped_at.isoformat()
            )
            
        except Exception as e:
            self._set_error_state(str(e))
            raise AudioCaptureError(f"Failed to stop audio stream: {e}")
    
    def validate(self) -> None:
        """
        Validate stream configuration.
        
        Raises:
            ValidationError: If configuration is invalid
        """
        # Validate sample rate
        if not (8000 <= self.sample_rate <= 48000):
            raise ValidationError(
                f"sample_rate must be between 8000 and 48000 Hz, got {self.sample_rate}"
            )
        
        # Validate channels
        if self.channels != 1:
            raise ValidationError(
                f"channels must be 1 (mono), got {self.channels}"
            )
        
        # Validate buffer size is power of 2
        if not (self.buffer_size > 0 and (self.buffer_size & (self.buffer_size - 1)) == 0):
            raise ValidationError(
                f"buffer_size must be a power of 2, got {self.buffer_size}"
            )
        
        # Validate audio format
        if self.audio_format != "int16":
            raise ValidationError(
                f"audio_format must be 'int16', got {self.audio_format}"
            )
    
    def _set_error_state(self, error_message: str) -> None:
        """
        Transition to error state.
        
        Args:
            error_message: Description of the error
        """
        self.state = "error"
        
        logger.error(
            "AudioStream entered error state",
            stream_id=str(self.stream_id),
            error=error_message
        )
    
    def _internal_callback(self, indata, frames, time_info, status):
        """
        Internal callback for sounddevice stream.
        
        Args:
            indata: Audio data from microphone
            frames: Number of frames
            time_info: Timing information
            status: Status flags
        """
        if status:
            logger.warning(
                "Audio callback status warning",
                stream_id=str(self.stream_id),
                status=str(status)
            )
        
        if self._audio_callback:
            self._audio_callback(indata, frames, time_info, status)
