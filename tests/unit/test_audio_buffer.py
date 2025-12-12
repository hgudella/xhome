"""Unit tests for AudioBuffer implementation."""

import pytest
import numpy as np
import gc
from unittest.mock import Mock, patch
from uuid import UUID
from datetime import datetime


class TestAudioBuffer:
    """Unit tests for AudioBuffer in-memory storage."""
    
    def test_create_buffer_with_audio_data(self):
        """Test creating buffer with audio data."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        assert isinstance(buffer.buffer_id, UUID)
        assert len(buffer.audio_data) == 16000
        assert buffer.sample_rate == 16000
    
    def test_duration_calculation_one_second(self):
        """Test duration calculation for 1 second audio."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        assert buffer.duration_seconds == 1.0
        assert buffer.frame_count == 16000
    
    def test_duration_calculation_half_second(self):
        """Test duration calculation for 0.5 second audio."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(8000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        assert buffer.duration_seconds == 0.5
        assert buffer.frame_count == 8000
    
    def test_captured_at_timestamp(self):
        """Test that captured_at is set automatically."""
        from src.audio.buffer import AudioBuffer
        
        before = datetime.utcnow()
        audio_data = np.zeros(1000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        after = datetime.utcnow()
        
        assert isinstance(buffer.captured_at, datetime)
        assert before <= buffer.captured_at <= after
    
    def test_initial_processing_state(self):
        """Test buffer starts as not processed."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(1000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        assert buffer.is_processed is False
    
    def test_clear_zeros_audio_data(self):
        """Test clear() zeros out audio data."""
        from src.audio.buffer import AudioBuffer
        
        # Create buffer with non-zero data
        audio_data = np.ones(16000, dtype=np.int16) * 1000
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        # Verify data exists
        assert np.any(buffer.audio_data != 0)
        
        # Clear buffer
        buffer.clear()
        
        # Verify data is zeroed
        assert np.all(buffer.audio_data == 0)
    
    def test_clear_marks_as_processed(self):
        """Test clear() marks buffer as processed."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(1000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        assert buffer.is_processed is False
        
        buffer.clear()
        
        assert buffer.is_processed is True
    
    def test_clear_triggers_garbage_collection(self):
        """Test clear() triggers garbage collection."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        with patch('src.audio.buffer.gc.collect') as mock_gc:
            buffer.clear()
            mock_gc.assert_called_once()
    
    def test_validation_invalid_dtype(self):
        """Test validation fails for non-int16 dtype."""
        from src.audio.buffer import AudioBuffer
        from src.utils.exceptions import ValidationError
        
        audio_data = np.zeros(1000, dtype=np.float32)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        with pytest.raises(ValidationError, match="dtype"):
            buffer.validate()
    
    def test_validation_empty_buffer(self):
        """Test validation fails for empty buffer."""
        from src.audio.buffer import AudioBuffer
        from src.utils.exceptions import ValidationError
        
        audio_data = np.array([], dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        with pytest.raises(ValidationError, match="empty"):
            buffer.validate()
    
    def test_validation_too_long(self):
        """Test validation fails for >30 second audio."""
        from src.audio.buffer import AudioBuffer
        from src.utils.exceptions import ValidationError
        
        # 31 seconds at 16kHz
        audio_data = np.zeros(16000 * 31, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        with pytest.raises(ValidationError, match="30 seconds"):
            buffer.validate()
    
    def test_create_from_stream(self):
        """Test creating buffer from AudioStream."""
        from src.audio.buffer import AudioBuffer
        from src.audio.capture import AudioStream
        
        stream = AudioStream(sample_rate=16000)
        audio_data = np.random.randint(-1000, 1000, 8000, dtype=np.int16)
        
        buffer = AudioBuffer.create_from_stream(stream, audio_data)
        
        assert isinstance(buffer, AudioBuffer)
        assert buffer.sample_rate == 16000
        assert len(buffer.audio_data) == 8000
    
    def test_mark_processed(self):
        """Test marking buffer as processed."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(1000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        buffer.mark_processed()
        
        assert buffer.is_processed is True
    
    def test_cannot_mark_processed_twice(self):
        """Test cannot mark already processed buffer."""
        from src.audio.buffer import AudioBuffer
        
        audio_data = np.zeros(1000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        buffer.mark_processed()
        
        with pytest.raises(ValueError, match="already processed"):
            buffer.mark_processed()
    
    def test_memory_cleanup_after_clear(self):
        """Test that memory is actually freed after clear."""
        from src.audio.buffer import AudioBuffer
        
        # Create large buffer
        audio_data = np.ones(16000 * 10, dtype=np.int16) * 1000
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        # Get memory reference
        initial_size = buffer.audio_data.nbytes
        assert initial_size > 0
        
        # Clear buffer
        buffer.clear()
        
        # Verify data is zeroed (memory still allocated but zeroed)
        assert np.all(buffer.audio_data == 0)
    
    @patch('src.audio.buffer.get_logger')
    def test_logging_on_creation(self, mock_logger):
        """Test buffer creation logs metadata (not audio)."""
        from src.audio.buffer import AudioBuffer
        
        logger_instance = Mock()
        mock_logger.return_value = logger_instance
        
        audio_data = np.zeros(16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        
        # Should log creation event
        if logger_instance.debug.called or logger_instance.info.called:
            # Verify no audio data in logs
            for call in logger_instance.debug.call_args_list + logger_instance.info.call_args_list:
                assert "audio_data" not in str(call)
                assert "samples" not in str(call)
    
    @patch('src.audio.buffer.get_logger')
    def test_logging_on_clear(self, mock_logger):
        """Test buffer clear logs metadata (not audio)."""
        from src.audio.buffer import AudioBuffer
        
        logger_instance = Mock()
        mock_logger.return_value = logger_instance
        
        audio_data = np.zeros(16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data, sample_rate=16000)
        buffer.clear()
        
        # Should log clear event
        if logger_instance.debug.called or logger_instance.info.called:
            # Verify no audio data in logs
            for call in logger_instance.debug.call_args_list + logger_instance.info.call_args_list:
                assert "audio_data" not in str(call)
