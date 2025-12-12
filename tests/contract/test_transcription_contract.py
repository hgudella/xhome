"""Contract tests for Transcription and WhisperEngine interfaces."""

import pytest
import numpy as np
from uuid import UUID
from datetime import datetime


class TestTranscriptionContract:
    """Contract tests for Transcription model."""
    
    def test_transcription_initialization(self):
        """Test Transcription initializes with required fields per data-model.md."""
        from src.transcription.transcriber import Transcription
        
        transcription = Transcription(
            text="Hello world",
            confidence=0.95,
            audio_duration_seconds=2.5,
            language="en"
        )
        
        # Required fields from data-model.md
        assert isinstance(transcription.transcription_id, UUID)
        assert transcription.text == "Hello world"
        assert transcription.confidence == 0.95
        assert transcription.audio_duration_seconds == 2.5
        assert isinstance(transcription.created_at, datetime)
        assert transcription.language == "en"
        assert transcription.model_name == "openai/whisper-tiny"
    
    def test_transcription_validation(self):
        """Test Transcription validation enforces data-model.md constraints."""
        from src.transcription.transcriber import Transcription
        from src.utils.exceptions import ValidationError
        
        # Confidence must be 0.0-1.0
        with pytest.raises(ValidationError, match="confidence"):
            t = Transcription(
                text="Test",
                confidence=1.5,  # Invalid
                audio_duration_seconds=1.0,
                language="en"
            )
            t.validate()
        
        # Audio duration must be positive
        with pytest.raises(ValidationError, match="audio_duration_seconds"):
            t = Transcription(
                text="Test",
                confidence=0.9,
                audio_duration_seconds=-1.0,  # Invalid
                language="en"
            )
            t.validate()
        
        # Text cannot be empty
        with pytest.raises(ValidationError, match="text"):
            t = Transcription(
                text="",  # Invalid
                confidence=0.9,
                audio_duration_seconds=1.0,
                language="en"
            )
            t.validate()


class TestWhisperEngineContract:
    """Contract tests for WhisperEngine interface."""
    
    def test_whisper_engine_initialization(self):
        """Test WhisperEngine initializes with model loading."""
        from src.transcription.whisper_engine import WhisperEngine
        
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        assert engine.model_name == "openai/whisper-tiny"
        assert engine.device == "cpu"
        assert engine.model is not None
        assert engine.processor is not None
    
    def test_whisper_engine_transcribe_interface(self):
        """Test WhisperEngine.transcribe() interface contract."""
        from src.transcription.whisper_engine import WhisperEngine
        from src.transcription.transcriber import Transcription
        
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        # Create dummy audio (1 second of silence at 16kHz)
        audio_data = np.zeros(16000, dtype=np.int16)
        
        result = engine.transcribe(audio_data, sample_rate=16000)
        
        # Must return Transcription object
        assert isinstance(result, Transcription)
        assert isinstance(result.text, str)
        assert 0.0 <= result.confidence <= 1.0
        assert result.audio_duration_seconds > 0
        assert result.language is not None
    
    def test_whisper_engine_preprocessing(self):
        """Test WhisperEngine handles audio preprocessing."""
        from src.transcription.whisper_engine import WhisperEngine
        
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        # Test different sample rates (should resample to 16kHz)
        audio_48khz = np.zeros(48000, dtype=np.int16)  # 1 second at 48kHz
        result = engine.transcribe(audio_48khz, sample_rate=48000)
        
        assert isinstance(result.text, str)
        assert result.audio_duration_seconds == pytest.approx(1.0, abs=0.1)
    
    def test_whisper_engine_empty_audio_handling(self):
        """Test WhisperEngine handles empty or silent audio gracefully."""
        from src.transcription.whisper_engine import WhisperEngine
        from src.utils.exceptions import TranscriptionError
        
        engine = WhisperEngine(model_name="openai/whisper-tiny", device="cpu")
        
        # Empty audio
        empty_audio = np.array([], dtype=np.int16)
        
        with pytest.raises(TranscriptionError, match="audio"):
            engine.transcribe(empty_audio, sample_rate=16000)
