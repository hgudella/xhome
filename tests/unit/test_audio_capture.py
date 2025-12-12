"""Unit tests for AudioStream implementation."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from uuid import UUID
from datetime import datetime


class TestAudioStream:
    """Unit tests for AudioStream audio capture functionality."""
    
    def test_default_initialization(self):
        """Test AudioStream initializes with default values."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream()
        
        assert stream.sample_rate == 16000
        assert stream.channels == 1
        assert stream.buffer_size == 1024
        assert stream.audio_format == "int16"
        assert stream.state == "stopped"
    
    def test_custom_initialization(self):
        """Test AudioStream initializes with custom values."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream(
            sample_rate=48000,
            channels=1,
            buffer_size=2048,
            device_index=1
        )
        
        assert stream.sample_rate == 48000
        assert stream.buffer_size == 2048
        assert stream.device_index == 1
    
    @patch('sounddevice.InputStream')
    def test_start_success(self, mock_input_stream):
        """Test successful stream start."""
        from src.audio.capture import AudioStream
        mock_stream_instance = Mock()
        mock_input_stream.return_value = mock_stream_instance
        
        stream = AudioStream()
        stream.start()
        
        assert stream.state == "listening"
        assert isinstance(stream.started_at, datetime)
        mock_input_stream.assert_called_once()
    
    @patch('sounddevice.InputStream')
    def test_stop_success(self, mock_input_stream):
        """Test successful audio stream stop."""
        from src.audio.capture import AudioStream
        
        mock_stream = MagicMock()
        mock_input_stream.return_value = mock_stream
        
        stream = AudioStream()
        stream.start()
        stream.stop()
        
        assert stream.state == "stopped"
        assert isinstance(stream.stopped_at, datetime)
        mock_stream.stop.assert_called_once()
        mock_stream.close.assert_called_once()
    
    def test_cannot_start_twice(self):
        """Test that starting an already running stream raises error."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import AudioCaptureError
        
        with patch('sounddevice.InputStream'):
            stream = AudioStream()
            stream.start()
            
            with pytest.raises(AudioCaptureError):
                stream.start()  # Already running
    
    def test_microphone_access_denied(self):
        """Test handling of microphone access denial."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import AudioCaptureError
        
        with patch('sounddevice.InputStream') as mock_input:
            mock_input.side_effect = Exception("Permission denied")
            
            stream = AudioStream()
            
            with pytest.raises(AudioCaptureError, match="Microphone access"):
                stream.start()
            
            assert stream.state == "error"
    
    def test_invalid_device_index(self):
        """Test handling of invalid audio device."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import AudioCaptureError
        
        with patch('sounddevice.InputStream') as mock_input:
            mock_input.side_effect = Exception("Invalid device")
            
            stream = AudioStream(device_index=999)
            
            with pytest.raises(AudioCaptureError, match="device"):
                stream.start()
    
    def test_validation_sample_rate_too_low(self):
        """Test validation fails for low sample rate."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import ValidationError
        
        stream = AudioStream(sample_rate=4000)
        
        with pytest.raises(ValidationError, match="sample_rate"):
            stream.validate()
    
    def test_validation_sample_rate_too_high(self):
        """Test validation fails for high sample rate."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import ValidationError
        
        stream = AudioStream(sample_rate=96000)
        
        with pytest.raises(ValidationError, match="sample_rate"):
            stream.validate()
    
    def test_validation_invalid_channels(self):
        """Test validation fails for non-mono channels."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import ValidationError
        
        stream = AudioStream(channels=2)
        
        with pytest.raises(ValidationError, match="channels"):
            stream.validate()
    
    def test_validation_buffer_size_not_power_of_two(self):
        """Test validation fails for non-power-of-2 buffer size."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import ValidationError
        
        stream = AudioStream(buffer_size=1000)
        
        with pytest.raises(ValidationError, match="buffer_size"):
            stream.validate()
    
    @patch('sounddevice.InputStream')
    def test_state_transition_stopped_to_listening(self, mock_input_stream):
        """Test state transition from stopped to listening."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream()
        assert stream.state == "stopped"
        
        stream.start()
        assert stream.state == "listening"
    
    @patch('sounddevice.InputStream')
    def test_state_transition_listening_to_stopped(self, mock_input_stream):
        """Test state transition from listening to stopped."""
        from src.audio.capture import AudioStream
        
        stream = AudioStream()
        stream.start()
        assert stream.state == "listening"
        
        stream.stop()
        assert stream.state == "stopped"
    
    def test_state_transition_to_error(self):
        """Test state transition to error on failure."""
        from src.audio.capture import AudioStream
        
        with patch('sounddevice.InputStream') as mock_input:
            mock_input.side_effect = Exception("Device error")
            
            stream = AudioStream()
            
            try:
                stream.start()
            except:
                pass
            
            assert stream.state == "error"
    
    @patch('sounddevice.InputStream')
    def test_logging_on_start(self, mock_input_stream):
        """Test that starting stream logs metadata (not audio)."""
        from src.audio.capture import AudioStream
        import logging
        
        # Capture log output
        with self._capture_logs() as log_capture:
            stream = AudioStream()
            stream.start()
            
            logs = log_capture.getvalue()
            
            # Should log start event
            assert "AudioStream started" in logs
            # Verify no audio data in logs
            assert "audio_data" not in logs
            assert "samples" not in logs
    
    def _capture_logs(self):
        """Helper to capture log output."""
        import io
        import logging
        
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.INFO)
        
        class LogCapture:
            def __enter__(self_inner):
                return log_capture
            def __exit__(self_inner, *args):
                logging.root.removeHandler(handler)
        
        return LogCapture()
    
    @patch('sounddevice.InputStream')
    def test_logging_on_stop(self, mock_input_stream):
        """Test that stopping stream logs metadata (not audio)."""
        from src.audio.capture import AudioStream
        import logging
        
        # Capture log output
        with self._capture_logs() as log_capture:
            stream = AudioStream()
            stream.start()
            stream.stop()
            
            logs = log_capture.getvalue()
            
            # Should log start and stop events
            assert "AudioStream started" in logs
            assert "AudioStream stopped" in logs
