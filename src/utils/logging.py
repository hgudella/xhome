"""Privacy-aware logging utilities."""

import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional
from pathlib import Path


class PrivacyAwareLogger:
    """
    Logger that ensures no PII (audio data or transcription text) is logged.
    Only metadata (timestamps, durations, IDs, status codes) is permitted.
    """
    
    def __init__(self, name: str, log_level: str = "INFO", log_format: str = "json"):
        """
        Initialize privacy-aware logger.
        
        Args:
            name: Logger name (typically module name)
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
            log_format: Output format ("json" or "text")
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.log_format = log_format
        
        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, log_level.upper()))
        
        if log_format == "json":
            console_handler.setFormatter(JsonFormatter())
        else:
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            console_handler.setFormatter(formatter)
        
        self.logger.addHandler(console_handler)
        
        # File handler (logs directory)
        try:
            log_dir = Path("logs")
            log_dir.mkdir(exist_ok=True)
            
            log_file = log_dir / f"{name}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(getattr(logging, log_level.upper()))
            
            if log_format == "json":
                file_handler.setFormatter(JsonFormatter())
            else:
                file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
        except Exception as e:
            # If file logging fails, continue with console only
            self.logger.warning(f"Could not set up file logging: {e}")
    
    def _sanitize_metadata(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensure metadata does not contain PII.
        
        Args:
            metadata: Dictionary of log metadata
        
        Returns:
            Sanitized metadata dictionary
        """
        # List of forbidden keys that might contain PII
        forbidden_keys = [
            "audio_data", "audio", "raw_audio", "samples",
            "text", "transcription", "transcription_text", "transcript",
            "speech", "words", "content"
        ]
        
        sanitized = {}
        for key, value in metadata.items():
            if key.lower() in forbidden_keys:
                sanitized[key] = "[REDACTED - PII]"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize_metadata(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    def debug(self, message: str, **metadata):
        """Log debug message with metadata."""
        sanitized = self._sanitize_metadata(metadata)
        self.logger.debug(message, extra={"metadata": sanitized})
    
    def info(self, message: str, **metadata):
        """Log info message with metadata."""
        sanitized = self._sanitize_metadata(metadata)
        self.logger.info(message, extra={"metadata": sanitized})
    
    def warning(self, message: str, **metadata):
        """Log warning message with metadata."""
        sanitized = self._sanitize_metadata(metadata)
        self.logger.warning(message, extra={"metadata": sanitized})
    
    def error(self, message: str, **metadata):
        """Log error message with metadata."""
        sanitized = self._sanitize_metadata(metadata)
        self.logger.error(message, extra={"metadata": sanitized})
    
    def critical(self, message: str, **metadata):
        """Log critical message with metadata."""
        sanitized = self._sanitize_metadata(metadata)
        self.logger.critical(message, extra={"metadata": sanitized})


class JsonFormatter(logging.Formatter):
    """Format log records as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON string."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add metadata if present
        if hasattr(record, "metadata"):
            log_data["metadata"] = record.metadata
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data)


def get_logger(name: str, log_level: Optional[str] = None, log_format: Optional[str] = None) -> PrivacyAwareLogger:
    """
    Get a privacy-aware logger instance.
    
    Args:
        name: Logger name (typically __name__)
        log_level: Optional log level (uses config if not provided)
        log_format: Optional log format (uses config if not provided)
    
    Returns:
        PrivacyAwareLogger instance
    """
    from .config import get_config
    
    if log_level is None or log_format is None:
        config = get_config()
        log_level = log_level or config.log_level
        log_format = log_format or config.log_format
    
    return PrivacyAwareLogger(name, log_level, log_format)
