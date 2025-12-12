"""Unit tests for Transcription model."""

import pytest
from unittest.mock import Mock, patch
from uuid import UUID
from datetime import datetime


class TestTranscription:
    """Unit tests for Transcription data model."""
    
    def test_create_transcription(self):
        """Test Transcription creation with required fields."""
        from src.transcription.transcriber import Transcription
        
        t = Transcription(
            text="Test transcription",
            confidence=0.92,
            audio_duration_seconds=3.5,
            language="en"
        )
        
        assert isinstance(t.transcription_id, UUID)
        assert t.text == "Test transcription"
        assert t.confidence == 0.92
        assert t.audio_duration_seconds == 3.5
        assert isinstance(t.created_at, datetime)
        assert t.language == "en"
        assert t.model_name == "openai/whisper-tiny"
    
    def test_transcription_with_custom_model(self):
        """Test Transcription with custom model name."""
        from src.transcription.transcriber import Transcription
        
        t = Transcription(
            text="Test",
            confidence=0.9,
            audio_duration_seconds=1.0,
            language="en",
            model_name="openai/whisper-base"
        )
        
        assert t.model_name == "openai/whisper-base"
    
    def test_validation_confidence_range(self):
        """Test validation enforces confidence in 0.0-1.0 range."""
        from src.transcription.transcriber import Transcription
        from src.utils.exceptions import ValidationError
        
        # Too high
        t1 = Transcription(
            text="Test",
            confidence=1.5,
            audio_duration_seconds=1.0,
            language="en"
        )
        
        with pytest.raises(ValidationError, match="confidence"):
            t1.validate()
        
        # Too low
        t2 = Transcription(
            text="Test",
            confidence=-0.1,
            audio_duration_seconds=1.0,
            language="en"
        )
        
        with pytest.raises(ValidationError, match="confidence"):
            t2.validate()
    
    def test_validation_audio_duration_positive(self):
        """Test validation enforces positive audio duration."""
        from src.transcription.transcriber import Transcription
        from src.utils.exceptions import ValidationError
        
        t = Transcription(
            text="Test",
            confidence=0.9,
            audio_duration_seconds=-1.0,
            language="en"
        )
        
        with pytest.raises(ValidationError, match="audio_duration_seconds"):
            t.validate()
    
    def test_validation_text_not_empty(self):
        """Test validation enforces non-empty text."""
        from src.transcription.transcriber import Transcription
        from src.utils.exceptions import ValidationError
        
        t = Transcription(
            text="",
            confidence=0.9,
            audio_duration_seconds=1.0,
            language="en"
        )
        
        with pytest.raises(ValidationError, match="text"):
            t.validate()
    
    def test_validation_max_duration(self):
        """Test validation enforces max audio duration (30 seconds)."""
        from src.transcription.transcriber import Transcription
        from src.utils.exceptions import ValidationError
        
        t = Transcription(
            text="Test",
            confidence=0.9,
            audio_duration_seconds=35.0,  # Exceeds max
            language="en"
        )
        
        with pytest.raises(ValidationError, match="audio_duration_seconds"):
            t.validate()
    
    def test_logging_on_creation(self):
        """Test Transcription logs creation (metadata only, no text)."""
        from src.transcription.transcriber import Transcription
        import logging
        import io
        
        # Capture logs
        log_capture = io.StringIO()
        handler = logging.StreamHandler(log_capture)
        logging.root.addHandler(handler)
        logging.root.setLevel(logging.INFO)
        
        try:
            t = Transcription(
                text="Secret message",
                confidence=0.95,
                audio_duration_seconds=2.0,
                language="en"
            )
            
            logs = log_capture.getvalue()
            
            # Should log creation
            assert "Transcription created" in logs
            
            # Verify no transcription text in logs
            assert "Secret message" not in logs
        finally:
            logging.root.removeHandler(handler)
