"""Transcription model for speech-to-text results."""

from uuid import uuid4, UUID
from datetime import datetime
from typing import Optional
from ..utils.exceptions import ValidationError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class Transcription:
    """
    Represents transcription result from speech-to-text processing.
    
    Stores transcribed text, confidence score, and metadata.
    Implements validation per data-model.md.
    """
    
    def __init__(
        self,
        text: str,
        confidence: float,
        audio_duration_seconds: float,
        language: str,
        model_name: str = "openai/whisper-tiny"
    ):
        """
        Initialize Transcription with speech-to-text results.
        
        Args:
            text: Transcribed text from audio
            confidence: Model confidence score (0.0-1.0)
            audio_duration_seconds: Duration of source audio
            language: Detected language code (e.g., "en")
            model_name: Whisper model used for transcription
        """
        self.transcription_id: UUID = uuid4()
        self.text: str = text
        self.confidence: float = confidence
        self.audio_duration_seconds: float = audio_duration_seconds
        self.language: str = language
        self.model_name: str = model_name
        self.created_at: datetime = datetime.utcnow()
        
        logger.info(
            "Transcription created",
            transcription_id=str(self.transcription_id),
            confidence=confidence,
            audio_duration_seconds=audio_duration_seconds,
            language=language,
            model_name=model_name,
            timestamp=self.created_at.isoformat()
        )
    
    def validate(self) -> None:
        """
        Validate transcription data per data-model.md constraints.
        
        Raises:
            ValidationError: If validation fails
        """
        # Confidence must be 0.0-1.0
        if not (0.0 <= self.confidence <= 1.0):
            raise ValidationError(
                f"Transcription {self.transcription_id}: confidence must be 0.0-1.0, got {self.confidence}"
            )
        
        # Audio duration must be positive
        if self.audio_duration_seconds <= 0:
            raise ValidationError(
                f"Transcription {self.transcription_id}: audio_duration_seconds must be positive, got {self.audio_duration_seconds}"
            )
        
        # Audio duration max 30 seconds (buffer constraint)
        if self.audio_duration_seconds > 30.0:
            raise ValidationError(
                f"Transcription {self.transcription_id}: audio_duration_seconds cannot exceed 30.0 seconds, got {self.audio_duration_seconds}"
            )
        
        # Text cannot be empty
        if not self.text or len(self.text.strip()) == 0:
            raise ValidationError(
                f"Transcription {self.transcription_id}: text cannot be empty"
            )
        
        logger.debug(
            "Transcription validation passed",
            transcription_id=str(self.transcription_id)
        )
