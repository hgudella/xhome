"""Configuration management for the voice-to-text application."""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from .exceptions import ConfigurationError


class Config:
    """Application configuration loaded from environment variables."""
    
    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize configuration from environment variables.
        
        Args:
            env_file: Path to .env file (default: .env in project root)
        """
        if env_file is None:
            # Look for .env in project root
            project_root = Path(__file__).parent.parent.parent
            env_file = project_root / ".env"
        
        if Path(env_file).exists():
            load_dotenv(env_file)
        
        # Audio configuration
        self.audio_sample_rate = self._get_int("AUDIO_SAMPLE_RATE", 16000)
        self.audio_channels = self._get_int("AUDIO_CHANNELS", 1)
        self.audio_buffer_size = self._get_int("AUDIO_BUFFER_SIZE", 1024)
        self.audio_device_index = self._get_optional_int("AUDIO_DEVICE_INDEX")
        
        # Whisper model configuration
        self.whisper_model_name = os.getenv("WHISPER_MODEL_NAME", "openai/whisper-base")
        self.whisper_device = os.getenv("WHISPER_DEVICE", "cpu")
        
        # Logging configuration
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.log_format = os.getenv("LOG_FORMAT", "json")
        
        # Privacy configuration
        self.audio_retention_seconds = self._get_int("AUDIO_RETENTION_SECONDS", 0)
        
        # Validate configuration
        self._validate()
    
    def _get_int(self, key: str, default: int) -> int:
        """Get integer value from environment variable."""
        value = os.getenv(key)
        if value is None:
            return default
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(f"Invalid integer value for {key}: {value}")
    
    def _get_optional_int(self, key: str) -> Optional[int]:
        """Get optional integer value from environment variable."""
        value = os.getenv(key)
        if value is None or value.strip() == "":
            return None
        try:
            return int(value)
        except ValueError:
            raise ConfigurationError(f"Invalid integer value for {key}: {value}")
    
    def _validate(self):
        """Validate configuration values."""
        # Validate audio sample rate
        if not (8000 <= self.audio_sample_rate <= 48000):
            raise ConfigurationError(
                f"audio_sample_rate must be between 8000 and 48000 Hz, got {self.audio_sample_rate}"
            )
        
        # Validate audio channels
        if self.audio_channels != 1:
            raise ConfigurationError(
                f"audio_channels must be 1 (mono), got {self.audio_channels}"
            )
        
        # Validate buffer size is power of 2
        if not (self.audio_buffer_size > 0 and (self.audio_buffer_size & (self.audio_buffer_size - 1)) == 0):
            raise ConfigurationError(
                f"audio_buffer_size must be a power of 2, got {self.audio_buffer_size}"
            )
        
        # Validate privacy requirement
        if self.audio_retention_seconds != 0:
            raise ConfigurationError(
                f"audio_retention_seconds must be 0 per privacy requirements, got {self.audio_retention_seconds}"
            )
        
        # Validate log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level.upper() not in valid_log_levels:
            raise ConfigurationError(
                f"log_level must be one of {valid_log_levels}, got {self.log_level}"
            )
        
        # Validate Whisper device
        if self.whisper_device not in ["cpu", "cuda"]:
            raise ConfigurationError(
                f"whisper_device must be 'cpu' or 'cuda', got {self.whisper_device}"
            )


# Global configuration instance
_config: Optional[Config] = None


def get_config(env_file: Optional[str] = None) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        env_file: Path to .env file (only used on first call)
    
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(env_file)
    return _config
