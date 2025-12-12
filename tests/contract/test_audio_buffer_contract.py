"""Contract tests for AudioBuffer interface."""

import pytest
import numpy as np
from uuid import UUID
from datetime import datetime


class TestAudioBufferContract:
    """
    Contract tests for AudioBuffer to verify the interface compliance.
    These tests define the expected behavior before implementation.
    """
    
    def test_audio_buffer_initialization(self):
        """AudioBuffer should initialize with audio data."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(16000, dtype=np.int16)  # 1 second at 16kHz
        
        buffer = AudioBuffer(
            audio_data=audio_data,
            sample_rate=16000
        )
        
        assert isinstance(buffer.buffer_id, UUID)
        assert isinstance(buffer.audio_data, np.ndarray)
        assert buffer.audio_data.dtype == np.int16
        assert buffer.sample_rate == 16000
        assert buffer.duration_seconds == 1.0
        assert buffer.frame_count == 16000
        assert isinstance(buffer.captured_at, datetime)
        assert buffer.is_processed is False
    
    def test_audio_buffer_duration_calculation(self):
        """AudioBuffer should correctly calculate duration."""
        from src.audio.buffer import AudioBuffer
        
        # 2 seconds at 16kHz = 32000 frames
        audio_data = np.zeros(32000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        assert buffer.duration_seconds == 2.0
        assert buffer.frame_count == 32000
    
    def test_audio_buffer_validation(self):
        """AudioBuffer should validate audio data."""
        from src.audio.buffer import AudioBuffer
        from src.utils.exceptions import ValidationError
        
        # Invalid dtype
        with pytest.raises(ValidationError):
            audio_data = np.zeros(16000, dtype=np.float32)
            buffer = AudioBuffer(audio_data, sample_rate=16000)
            buffer.validate()
        
        # Too long (> 30 seconds)
        with pytest.raises(ValidationError):
            audio_data = np.zeros(16000 * 31, dtype=np.int16)  # 31 seconds
            buffer = AudioBuffer(audio_data, sample_rate=16000)
            buffer.validate()
        
        # Empty buffer
        with pytest.raises(ValidationError):
            audio_data = np.array([], dtype=np.int16)
            buffer = AudioBuffer(audio_data, sample_rate=16000)
            buffer.validate()
    
    def test_audio_buffer_clear(self):
        """AudioBuffer should clear data for privacy compliance."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.ones(16000, dtype=np.int16) * 100
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        # Verify data exists
        assert np.any(buffer.audio_data != 0)
        
        # Clear buffer
        buffer.clear()
        
        # Verify data is zeroed
        assert np.all(buffer.audio_data == 0)
        assert buffer.is_processed is True
    
    def test_audio_buffer_from_stream(self):
        """AudioBuffer should be created from AudioStream data."""
        from src.audio.buffer import AudioBuffer
        from src.audio.capture import AudioStream
        
        stream = AudioStream()
        
        # Simulate captured audio
        audio_data = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        
        buffer = AudioBuffer.create_from_stream(stream, audio_data)
        
        assert isinstance(buffer, AudioBuffer)
        assert buffer.sample_rate == stream.sample_rate
        assert len(buffer.audio_data) == len(audio_data)
    
    def test_audio_buffer_processing_lifecycle(self):
        """AudioBuffer should track processing lifecycle."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        # Initially not processed
        assert buffer.is_processed is False
        
        # Mark as processed
        buffer.mark_processed()
        assert buffer.is_processed is True
        
        # Should not allow reuse after processing
        with pytest.raises(ValueError):
            buffer.mark_processed()  # Already processed
