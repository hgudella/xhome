"""Integration tests for end-to-end audio-to-text pipeline."""

import pytest
import numpy as np
import time
from unittest.mock import patch, Mock


class TestAudioToTextPipeline:
    """Integration tests for complete audio capture to transcription flow."""
    
    @patch('sounddevice.InputStream')
    def test_complete_audio_to_text_pipeline(self, mock_input_stream):
        """Test complete pipeline: AudioStream → AudioBuffer → Transcription."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        
        # Mock audio stream
        mock_stream = Mock()
        mock_input_stream.return_value = mock_stream
        
        # Step 1: Capture audio
        stream = AudioStream(sample_rate=16000)
        
        captured_audio = []
        def audio_callback(indata, frames, time_info, status):
            captured_audio.append(indata.copy())
        
        stream.start(audio_callback=audio_callback)
        
        # Simulate audio capture
        fake_audio = np.random.randint(-1000, 1000, size=(1024, 1), dtype=np.int16)
        audio_callback(fake_audio, 1024, None, None)
        
        stream.stop()
        
        # Step 2: Create buffer from captured audio
        combined_audio = np.concatenate(captured_audio, axis=0).flatten()
        buffer = AudioBuffer.create_from_stream(stream, combined_audio)
        
        assert buffer is not None
        assert buffer.audio_data.shape[0] > 0
        assert buffer.sample_rate == 16000
        
        # Step 3: Transcribe audio
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
        
        assert transcription is not None
        assert isinstance(transcription.text, str)
        assert 0.0 <= transcription.confidence <= 1.0
        
        # Step 4: Clear buffer (privacy compliance)
        buffer.clear()
        
        assert np.all(buffer.audio_data == 0)
        assert buffer.is_processed is True
    
    @patch('sounddevice.InputStream')
    def test_continuous_transcription_loop(self, mock_input_stream):
        """Test continuous capture-transcribe-clear loop."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        
        mock_stream = Mock()
        mock_input_stream.return_value = mock_stream
        
        stream = AudioStream(sample_rate=16000)
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        transcriptions = []
        
        for cycle in range(2):
            # Capture
            captured_audio = []
            def audio_callback(indata, frames, time_info, status):
                captured_audio.append(indata.copy())
            
            stream.start(audio_callback=audio_callback)
            
            # Simulate capture
            fake_audio = np.random.randint(-1000, 1000, size=(1024, 1), dtype=np.int16)
            audio_callback(fake_audio, 1024, None, None)
            
            stream.stop()
            
            # Buffer
            combined_audio = np.concatenate(captured_audio, axis=0).flatten()
            buffer = AudioBuffer.create_from_stream(stream, combined_audio)
            
            # Transcribe
            transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
            transcriptions.append(transcription)
            
            # Clear
            buffer.clear()
        
        assert len(transcriptions) == 2
        assert all(isinstance(t.text, str) for t in transcriptions)
    
    @patch('sounddevice.InputStream')
    def test_transcription_latency_requirement(self, mock_input_stream):
        """Test transcription completes within 3 seconds (requirement)."""
        from src.audio.capture import AudioStream
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        
        mock_stream = Mock()
        mock_input_stream.return_value = mock_stream
        
        # Capture audio
        stream = AudioStream(sample_rate=16000)
        fake_audio = np.random.randint(-1000, 1000, size=(16000,), dtype=np.int16)  # 1 second
        buffer = AudioBuffer(audio_data=fake_audio, sample_rate=16000)
        
        # Measure transcription time
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        start_time = time.time()
        transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
        elapsed_time = time.time() - start_time
        
        # Must complete within 3 seconds
        assert elapsed_time < 3.0, f"Transcription took {elapsed_time:.2f}s, exceeds 3s requirement"
    
    def test_buffer_to_transcription_integration(self):
        """Test AudioBuffer integrates seamlessly with WhisperEngine."""
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        
        # Create buffer with known audio
        audio_data = np.random.randint(-5000, 5000, size=16000, dtype=np.int16)
        buffer = AudioBuffer(
            audio_data=audio_data,
            sample_rate=16000
        )
        
        # Validate buffer
        buffer.validate()
        
        # Transcribe
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
        
        # Verify
        assert isinstance(transcription.text, str)
        assert transcription.audio_duration_seconds == pytest.approx(1.0, abs=0.1)
        
        # Clear buffer
        buffer.clear()
        assert buffer.is_processed is True
    
    def test_privacy_compliance_no_audio_retention(self):
        """Test audio is cleared immediately after transcription (0-day retention)."""
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        
        audio_data = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)
        buffer = AudioBuffer(audio_data=audio_data, sample_rate=16000)
        
        # Transcribe
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
        
        # Verify transcription exists
        assert len(transcription.text) >= 0
        
        # Clear audio immediately (0-day retention)
        buffer.clear()
        
        # Verify audio is zeroed
        assert np.all(buffer.audio_data == 0)
        assert buffer.is_processed is True
    
    def test_error_handling_invalid_audio(self):
        """Test pipeline handles invalid audio gracefully."""
        from src.transcription.whisper_engine import WhisperEngine
        from src.utils.exceptions import TranscriptionError
        
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        # Empty audio
        empty_audio = np.array([], dtype=np.int16)
        
        with pytest.raises(TranscriptionError):
            engine.transcribe(empty_audio, sample_rate=16000)
    
    def test_logging_full_pipeline(self):
        """Test full pipeline logs metadata only (no audio, no text)."""
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        import logging
        import io
        
        # Capture logs
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.INFO)
        
        try:
            # Run pipeline
            audio_data = np.random.randint(-1000, 1000, size=16000, dtype=np.int16)
            buffer = AudioBuffer(audio_data=audio_data, sample_rate=16000)
            
            engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
            transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
            
            buffer.clear()
            
            logs = log_capture.getvalue()
            
            # Should log events
            assert "AudioBuffer" in logs or "Transcription" in logs or "WhisperEngine" in logs
            
            # Should NOT log audio data
            assert "audio_data" not in logs
            assert "samples" not in logs
            
            # Should NOT log transcription text
            assert transcription.text not in logs
            
        finally:
            logging.root.removeHandler(handler)
