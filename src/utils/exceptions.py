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


# Feature 002: SLM and MQTT exceptions

class SLMError(Exception):
    """Base exception for SLM-related errors."""
    pass


class ModelLoadError(SLMError):
    """Raised when model fails to load."""
    pass


class InferenceError(SLMError):
    """Raised when SLM inference fails."""
    pass


class TimeoutError(SLMError):
    """Raised when SLM inference exceeds timeout."""
    pass


class MQTTError(Exception):
    """Base exception for MQTT-related errors."""
    pass


class MQTTConnectionError(MQTTError):
    """Raised when MQTT connection fails."""
    pass


class MQTTPublishError(MQTTError):
    """Raised when MQTT publish operation fails."""
    pass


class DeviceNotFoundError(Exception):
    """Raised when device is not found in configuration."""
    pass


class CommandParsingError(Exception):
    """Raised when command structure is invalid."""
    pass
