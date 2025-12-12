"""Custom exception classes for the voice-to-text application."""


class AudioCaptureError(Exception):
    """Raised when audio capture fails or encounters errors."""
    pass


class TranscriptionError(Exception):
    """Raised when speech-to-text transcription fails."""
    pass


class SessionError(Exception):
    """Raised when voice session management encounters errors."""
    pass


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class ConfigurationError(Exception):
    """Raised when configuration is invalid or missing."""
    pass
