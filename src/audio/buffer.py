"""AudioBuffer implementation for in-memory audio storage."""

import numpy as np
import gc
from uuid import uuid4, UUID
from datetime import datetime
from typing import TYPE_CHECKING
from ..utils.exceptions import ValidationError
from ..utils.logging import get_logger

if TYPE_CHECKING:
    from .capture import AudioStream

logger = get_logger(__name__)


class AudioBuffer:
    """
    Temporary in-memory storage for captured audio data.
    
    Must be cleared immediately after transcription per privacy requirements (0-day retention).
    """
    
    def __init__(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ):
        """
        Initialize AudioBuffer with audio data.
        
        Args:
            audio_data: Raw audio samples (1D numpy array of int16)
            sample_rate: Sample rate in Hz
        """
        self.buffer_id: UUID = uuid4()
        self.audio_data: np.ndarray = audio_data
        self.sample_rate: int = sample_rate
        self.captured_at: datetime = datetime.utcnow()
        self.is_processed: bool = False
        
        # Computed attributes
        self.frame_count: int = len(audio_data)
        self.duration_seconds: float = self.frame_count / sample_rate
        
        logger.debug(
            "AudioBuffer created",
            buffer_id=str(self.buffer_id),
            duration_seconds=self.duration_seconds,
            frame_count=self.frame_count,
            sample_rate=self.sample_rate
        )
    
    @classmethod
    def create_from_stream(cls, stream: 'AudioStream', audio_data: np.ndarray) -> 'AudioBuffer':
        """
        Create AudioBuffer from AudioStream captured data.
        
        Args:
            stream: AudioStream that captured the audio
            audio_data: Raw audio samples from stream
        
        Returns:
            AudioBuffer instance
        """
        buffer = cls(audio_data=audio_data, sample_rate=stream.sample_rate)
        
        logger.debug(
            "AudioBuffer created from stream",
            buffer_id=str(buffer.buffer_id),
            stream_id=str(stream.stream_id),
            duration_seconds=buffer.duration_seconds
        )
        
        return buffer
    
    def validate(self) -> None:
        """
        Validate buffer data.
        
        Raises:
            ValidationError: If buffer data is invalid
        """
        # Validate dtype
        if self.audio_data.dtype != np.int16:
            raise ValidationError(
                f"audio_data dtype must be int16, got {self.audio_data.dtype}"
            )
        
        # Validate not empty
        if len(self.audio_data) == 0:
            raise ValidationError("audio_data cannot be empty")
        
        # Validate max duration (30 seconds)
        if self.duration_seconds > 30.0:
            raise ValidationError(
                f"audio_data duration must be ≤ 30 seconds, got {self.duration_seconds:.2f}s"
            )
        
        # Validate 1D array
        if self.audio_data.ndim != 1:
            raise ValidationError(
                f"audio_data must be 1D array, got {self.audio_data.ndim}D"
            )
    
    def clear(self) -> None:
        """
        Clear audio data for privacy compliance (0-day retention).
        
        Zeros out the audio data and triggers garbage collection.
        """
        if self.is_processed:
            logger.warning(
                "Attempted to clear already processed buffer",
                buffer_id=str(self.buffer_id)
            )
            return
        
        # Zero out audio data
        self.audio_data.fill(0)
        self.is_processed = True
        
        logger.info(
            "AudioBuffer cleared",
            buffer_id=str(self.buffer_id),
            frame_count=self.frame_count
        )
        
        # Trigger garbage collection
        gc.collect()
    
    def mark_processed(self) -> None:
        """
        Mark buffer as processed.
        
        Raises:
            ValueError: If buffer is already processed
        """
        if self.is_processed:
            raise ValueError(
                f"Buffer {self.buffer_id} is already processed"
            )
        
        self.is_processed = True
        
        logger.debug(
            "AudioBuffer marked as processed",
            buffer_id=str(self.buffer_id)
        )
