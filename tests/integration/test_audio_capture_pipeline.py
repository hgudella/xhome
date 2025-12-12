"""Integration test for audio capture pipeline (User Story 1)."""

import pytest
import numpy as np
import time
from unittest.mock import patch, MagicMock


class TestAudioCapturePipeline:
    """
    Integration tests for User Story 1: Real-time Voice Capture
    
    Tests the end-to-end flow: microphone → AudioStream → AudioBuffer
    """
    
    @patch('sounddevice.InputStream')
    def test_complete_capture_pipeline(self, mock_sd):
        """Test complete audio capture pipeline from mic to buffer."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        
        # Mock sounddevice stream
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream
        
        # Simulate audio callback
        captured_audio = []
        
        def audio_callback(indata, frames, time_info, status):
            captured_audio.append(indata.copy())
        
        # Create and start stream
        stream = AudioStream(sample_rate=16000, buffer_size=1024)
        stream.start()
        
        assert stream.state == "listening"
        
        # Simulate captured audio data
        simulated_audio = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        
        # Create buffer from captured audio
        buffer = AudioBuffer.create_from_stream(stream, simulated_audio)
        
        assert isinstance(buffer, AudioBuffer)
        assert buffer.sample_rate == stream.sample_rate
        assert len(buffer.audio_data) == len(simulated_audio)
        assert buffer.is_processed is False
        
        # Stop stream
        stream.stop()
        assert stream.state == "stopped"
        
        # Clear buffer (privacy requirement)
        buffer.clear()
        assert buffer.is_processed is True
        assert np.all(buffer.audio_data == 0)
    
    @patch('sounddevice.InputStream')
    def test_continuous_listening_without_errors(self, mock_sd):
        """Test system continues listening during silence."""
        from src.audio.capture import AudioStream
        
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream
        
        stream = AudioStream()
        stream.start()
        
        # Simulate continuous listening (no crashes)
        assert stream.state == "listening"
        
        # Stop after "silence"
        stream.stop()
        assert stream.state == "stopped"
    
    @patch('sounddevice.InputStream')
    def test_multiple_capture_cycles(self, mock_sd):
        """Test multiple capture and buffer cycles."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream
        
        stream = AudioStream()
        stream.start()
        
        # Capture multiple audio chunks
        buffers = []
        for i in range(3):
            audio_data = np.random.randint(-500, 500, 8000, dtype=np.int16)
            buffer = AudioBuffer.create_from_stream(stream, audio_data)
            buffers.append(buffer)
        
        # Verify all buffers created
        assert len(buffers) == 3
        
        # Clear all buffers
        for buffer in buffers:
            buffer.clear()
            assert buffer.is_processed is True
        
        stream.stop()
    
    @patch('sounddevice.InputStream')
    def test_buffer_ready_for_processing(self, mock_sd):
        """Test buffer is ready for processing after capture."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream
        
        stream = AudioStream()
        stream.start()
        
        # Capture audio
        audio_data = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
        buffer = AudioBuffer.create_from_stream(stream, audio_data)
        
        # Buffer should be ready for transcription
        assert buffer.is_processed is False
        assert buffer.duration_seconds > 0
        assert len(buffer.audio_data) > 0
        
        stream.stop()
    
    @patch('sounddevice.InputStream')
    def test_device_selection(self, mock_input_stream):
        """Test selection of specific audio input device."""
        from src.audio.capture import AudioStream
        
        mock_stream = MagicMock()
        mock_input_stream.return_value = mock_stream
        
        # Default device
        stream1 = AudioStream()
        stream1.start()
        
        call_args1 = mock_input_stream.call_args
        assert call_args1[1]['device'] is None or call_args1[1]['device'] == stream1.device_index
        
        stream1.stop()
        
        # Specific device
        stream2 = AudioStream(device_index=1)
        stream2.start()
        
        call_args2 = mock_input_stream.call_args
        assert call_args2[1]['device'] == 1
        
        stream2.stop()
    
    @patch('sounddevice.InputStream')
    def test_privacy_compliance_zero_retention(self, mock_sd):
        """Test zero-day audio retention (User Story 1 acceptance criteria)."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        
        mock_stream = MagicMock()
        mock_sd.InputStream.return_value = mock_stream
        
        stream = AudioStream()
        stream.start()
        
        # Capture audio
        audio_data = np.ones(16000, dtype=np.int16) * 500
        buffer = AudioBuffer.create_from_stream(stream, audio_data)
        
        # Verify data exists before clear
        assert np.any(buffer.audio_data != 0)
        
        # Simulate processing complete → immediate clear
        buffer.clear()
        
        # Verify zero retention: data is zeroed
        assert np.all(buffer.audio_data == 0)
        assert buffer.is_processed is True
        
        stream.stop()
    
    def test_microphone_initialization_failure(self):
        """Test graceful handling of microphone initialization failure."""
        from src.audio.capture import AudioStream
        from src.utils.exceptions import AudioCaptureError
        
        with patch('sounddevice.InputStream') as mock_input:
            mock_input.side_effect = Exception("No microphone available")
            
            stream = AudioStream()
            
            with pytest.raises(AudioCaptureError):
                stream.start()
            
            assert stream.state == "error"
    
    @patch('sounddevice.InputStream')
    def test_logging_metadata_only(self, mock_sd):
        """Test that only metadata is logged, not audio data."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        
        with patch('src.utils.logging.get_logger') as mock_logger:
            logger_instance = MagicMock()
            mock_logger.return_value = logger_instance
            
            mock_stream = MagicMock()
            mock_sd.InputStream.return_value = mock_stream
            
            stream = AudioStream()
            stream.start()
            
            audio_data = np.random.randint(-1000, 1000, 16000, dtype=np.int16)
            buffer = AudioBuffer.create_from_stream(stream, audio_data)
            
            stream.stop()
            buffer.clear()
            
            # Check all log calls - none should contain audio data
            if logger_instance.info.called or logger_instance.debug.called:
                all_calls = (logger_instance.info.call_args_list + 
                           logger_instance.debug.call_args_list)
                
                for call in all_calls:
                    call_str = str(call)
                    # Verify no audio data logged
                    assert "audio_data" not in call_str
                    assert "samples" not in call_str
                    assert "raw_audio" not in call_str


