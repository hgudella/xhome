"""Data models for command processing."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import json


@dataclass
class Command:
    """Represents a parsed user intent extracted from transcribed text."""
    
    intent: str
    device: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    timestamp: datetime = field(default_factory=datetime.utcnow)
    raw_transcription: Optional[str] = None  # Cleared after processing per FR-014
    
    # Valid intent types
    VALID_INTENTS = {
        'turn_on', 'turn_off', 'set_brightness', 'set_temperature',
        'set_color', 'set_mode', 'unknown'
    }
    
    def __post_init__(self):
        """Validate command after initialization."""
        if self.intent not in self.VALID_INTENTS:
            raise ValueError(
                f"Invalid intent: {self.intent}. "
                f"Must be one of: {', '.join(self.VALID_INTENTS)}"
            )
    
    def to_mqtt_payload(self) -> Dict[str, Any]:
        """Convert to MQTT message payload.
        
        Returns:
            Dictionary suitable for MQTT JSON payload
        """
        if self.intent == 'turn_on':
            payload = {"state": "ON"}
        elif self.intent == 'turn_off':
            payload = {"state": "OFF"}
        elif self.intent == 'set_brightness':
            payload = {"state": "ON", "brightness": self.parameters.get('brightness', 100)}
        elif self.intent == 'set_temperature':
            payload = {"temperature": self.parameters.get('temperature')}
        elif self.intent == 'set_color':
            payload = {"state": "ON", "color": self.parameters.get('color')}
        elif self.intent == 'set_mode':
            payload = {"mode": self.parameters.get('mode')}
        else:
            payload = {}
        
        # Add any additional parameters
        for key, value in self.parameters.items():
            if key not in payload:
                payload[key] = value
        
        return payload
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging (without transcription).
        
        Returns:
            Dictionary representation excluding raw_transcription
        """
        return {
            'intent': self.intent,
            'device': self.device,
            'parameters': self.parameters,
            'confidence': self.confidence,
            'timestamp': self.timestamp.isoformat()
            # Explicitly exclude raw_transcription for privacy
        }
    
    def to_json(self) -> str:
        """Convert to JSON string for logging."""
        return json.dumps(self.to_dict())
    
    def clear_transcription(self) -> None:
        """Clear raw transcription for privacy (FR-014)."""
        self.raw_transcription = None
