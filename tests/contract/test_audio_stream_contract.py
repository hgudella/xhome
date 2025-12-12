"""Contract tests for AudioStream interface."""

import pytest
from uuid import UUID


class TestAudioStreamContract:
    """
    Contract tests for AudioStream to verify the interface compliance.
    These tests define the expected behavior before implementation.
    """
    
    def test_audio_stream_initialization(self):
        """AudioStream should initialize with valid configuration."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream(
            sample_rate=16000,
            channels=1,
            buffer_size=1024
        )
        
        assert isinstance(stream.stream_id, UUID)
        assert stream.sample_rate == 16000
        assert stream.channels == 1
        assert stream.buffer_size == 1024
        assert stream.audio_format == "int16"
        assert stream.state == "stopped"
        assert stream.device_index is None
        assert stream.started_at is None
        assert stream.stopped_at is None
    
    def test_audio_stream_state_transitions(self):
        """AudioStream should transition through states correctly."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream()
        
        # Initial state
        assert stream.state == "stopped"
        
        # Start should transition to listening
        stream.start()
        assert stream.state == "listening"
        assert stream.started_at is not None
        
        # Stop should transition back to stopped
        stream.stop()
        assert stream.state == "stopped"
        assert stream.stopped_at is not None
    
    def test_audio_stream_validation(self):
        """AudioStream should validate configuration parameters."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import ValidationError
        
        # Invalid sample rate
        with pytest.raises(ValidationError):
            stream = AudioStream(sample_rate=1000)  # Too low
            stream.validate()
        
        # Invalid channels
        with pytest.raises(ValidationError):
            stream = AudioStream(channels=2)  # Must be mono
            stream.validate()
        
        # Invalid buffer size (not power of 2)
        with pytest.raises(ValidationError):
            stream = AudioStream(buffer_size=1000)
            stream.validate()
    
    def test_audio_stream_device_selection(self):
        """AudioStream should handle device selection."""
        from src.audio.capture import AudioStream
        
        # Default device
        stream1 = AudioStream()
        assert stream1.device_index is None
        
        # Specific device
        stream2 = AudioStream(device_index=0)
        assert stream2.device_index == 0
    
    def test_audio_stream_error_state(self):
        """AudioStream should transition to error state on failures."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream()
        stream.start()
        
        # Simulate error
        stream._set_error_state("Test error")
        assert stream.state == "error"
