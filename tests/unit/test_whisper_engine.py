"""Unit tests for WhisperEngine implementation."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock


class TestWhisperEngine:
    """Unit tests for WhisperEngine Whisper model wrapper."""
    
    def test_default_initialization(self):
        """Test WhisperEngine initializes with default values."""
        from src.transcription.whisper_engine import WhisperEngine
        
        with patch('src.transcription.whisper_engine.AutoModelForSpeechSeq2Seq'):
            with patch('src.transcription.whisper_engine.AutoProcessor'):
                engine = WhisperEngine()
                
                assert engine.model_name == "openai/whisper-tiny"
                assert engine.device == "cpu"
    
    def test_custom_initialization(self):
        """Test WhisperEngine initializes with custom values."""
        from src.transcription.whisper_engine import WhisperEngine
        
        with patch('src.transcription.whisper_engine.AutoModelForSpeechSeq2Seq'):
            with patch('src.transcription.whisper_engine.AutoProcessor'):
                engine = WhisperEngine(
                    model_name="openai/whisper-base",
                    device="cuda"
                )
                
                assert engine.model_name == "openai/whisper-base"
                assert engine.device == "cuda"
    
    def test_model_loading(self):
        """Test WhisperEngine loads model and processor."""
        from src.transcription.whisper_engine import WhisperEngine
        
        with patch('src.transcription.whisper_engine.AutoModelForSpeechSeq2Seq') as mock_model:
            with patch('src.transcription.whisper_engine.AutoProcessor') as mock_processor:
                mock_model.from_pretrained.return_value = Mock()
                mock_processor.from_pretrained.return_value = Mock()
                
                engine = WhisperEngine()
                
                mock_model.from_pretrained.assert_called_once()
                mock_processor.from_pretrained.assert_called_once()
    
    def test_audio_normalization(self):
        """Test WhisperEngine normalizes int16 to float32."""
        from src.transcription.whisper_engine import WhisperEngine
        
        engine = WhisperEngine()
        
        # Max int16 value
        audio_int16 = np.array([32767, -32768, 0], dtype=np.int16)
        normalized = engine._normalize_audio(audio_int16)
        
        assert normalized.dtype == np.float32
        assert normalized[0] == pytest.approx(1.0, abs=0.01)
        assert normalized[1] == pytest.approx(-1.0, abs=0.01)
        assert normalized[2] == 0.0
    
    def test_audio_resampling(self):
        """Test WhisperEngine resamples audio to 16kHz."""
        from src.transcription.whisper_engine import WhisperEngine
        
        with patch('src.transcription.whisper_engine.librosa.resample') as mock_resample:
            mock_resample.return_value = np.zeros(16000, dtype=np.float32)
            
            engine = WhisperEngine()
            
            # 48kHz audio
            audio_48khz = np.zeros(48000, dtype=np.float32)
            resampled = engine._resample_audio(audio_48khz, source_sr=48000)
            
            mock_resample.assert_called_once()
            assert resampled.shape[0] == 16000
    
    def test_transcribe_success(self):
        """Test WhisperEngine transcribes audio successfully."""
        from src.transcription.whisper_engine import WhisperEngine
        from src.transcription.transcriber import Transcription
        
        with patch('src.transcription.whisper_engine.AutoModelForSpeechSeq2Seq') as mock_model_class:
            with patch('src.transcription.whisper_engine.AutoProcessor') as mock_processor_class:
                # Mock model and processor
                mock_model = Mock()
                mock_processor = Mock()
                mock_model_class.from_pretrained.return_value = mock_model
                mock_processor_class.from_pretrained.return_value = mock_processor
                
                # Mock processor output with .to() method
                mock_inputs = Mock()
                mock_inputs.to.return_value = mock_inputs
                mock_inputs.__getitem__ = Mock(return_value=np.zeros((1, 80, 3000), dtype=np.float32))
                mock_processor.return_value = mock_inputs
                
                # Mock model output
                mock_output = Mock()
                mock_output.sequences = [[1, 2, 3]]
                mock_model.generate.return_value = mock_output
                
                # Mock decode
                mock_processor.batch_decode.return_value = ["Hello world"]
                
                engine = WhisperEngine()
                
                audio_data = np.zeros(16000, dtype=np.int16)
                result = engine.transcribe(audio_data, sample_rate=16000)
                
                assert isinstance(result, Transcription)
                assert result.text == "Hello world"
    
    def test_transcribe_empty_audio_raises_error(self):
        """Test WhisperEngine raises error for empty audio."""
        from src.transcription.whisper_engine import WhisperEngine
        from src.utils.exceptions import TranscriptionError
        
        engine = WhisperEngine()
        
        empty_audio = np.array([], dtype=np.int16)
        
        with pytest.raises(TranscriptionError, match="audio"):
            engine.transcribe(empty_audio, sample_rate=16000)
    
    def test_transcribe_invalid_sample_rate_raises_error(self):
        """Test WhisperEngine raises error for invalid sample rate."""
        from src.transcription.whisper_engine import WhisperEngine
        from src.utils.exceptions import TranscriptionError
        
        engine = WhisperEngine()
        
        audio_data = np.zeros(16000, dtype=np.int16)
        
        with pytest.raises(TranscriptionError, match="sample_rate"):
            engine.transcribe(audio_data, sample_rate=0)
    
    def test_confidence_calculation(self):
        """Test WhisperEngine calculates confidence score."""
        from src.transcription.whisper_engine import WhisperEngine
        
        with patch('src.transcription.whisper_engine.AutoModelForSpeechSeq2Seq'):
            with patch('src.transcription.whisper_engine.AutoProcessor'):
                engine = WhisperEngine()
                
                # Mock logits for confidence calculation
                mock_logits = np.array([[0.1, 0.8, 0.1]])  # High confidence on middle token
                confidence = engine._calculate_confidence(mock_logits)
                
                assert 0.0 <= confidence <= 1.0
    
    def test_logging_on_transcription(self):
        """Test WhisperEngine logs metadata (not transcription text)."""
        from src.transcription.whisper_engine import WhisperEngine
        import logging
        import io
        
        # Capture logs
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.INFO)
        
        try:
            with patch('src.transcription.whisper_engine.AutoModelForSpeechSeq2Seq'):
                with patch('src.transcription.whisper_engine.AutoProcessor'):
                    engine = WhisperEngine()
                    
                    logs = log_capture.getvalue()
                    
                    # Should log model initialization
                    assert "Loading Whisper model" in logs or "Whisper model loaded" in logs
        finally:
            logging.root.removeHandler(handler)
