"""Command session tracking."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Dict
from uuid import uuid4, UUID
import json

from .models import Command


@dataclass
class CommandSession:
    """Represents the lifecycle of a voice command from transcription to MQTT."""
    
    session_id: UUID = field(default_factory=uuid4)
    transcription: Optional[str] = None
    commands: List[Command] = field(default_factory=list)
    mqtt_messages: List[Dict] = field(default_factory=list)  # Simplified for tracking
    errors: List[str] = field(default_factory=list)
    feedback: List[str] = field(default_factory=list)
    start_time: datetime = field(default_factory=datetime.utcnow)
    end_time: Optional[datetime] = None
    
    @property
    def duration_ms(self) -> Optional[int]:
        """Calculate session duration in milliseconds.
        
        Returns:
            Duration in milliseconds, or None if session not ended
        """
        if self.end_time:
            delta = self.end_time - self.start_time
            return int(delta.total_seconds() * 1000)
        return None
    
    def add_command(self, command: Command) -> None:
        """Add a parsed command to the session."""
        self.commands.append(command)
    
    def add_mqtt_message(self, topic: str, payload: dict) -> None:
        """Record an MQTT message publication."""
        self.mqtt_messages.append({
            'topic': topic,
            'payload': payload,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    def add_error(self, error: str) -> None:
        """Add an error message to the session."""
        self.errors.append(error)
    
    def add_feedback(self, message: str) -> None:
        """Add user feedback message to the session."""
        self.feedback.append(message)
    
    def complete(self) -> None:
        """Mark session as complete and clear sensitive data."""
        self.end_time = datetime.utcnow()
        self.clear()
    
    def clear(self) -> None:
        """Clear transcription and command raw data for privacy (FR-014)."""
        # Clear transcription (PII)
        self.transcription = None
        
        # Clear raw transcriptions from commands
        for command in self.commands:
            command.clear_transcription()
    
    def to_dict(self, include_transcription: bool = False) -> dict:
        """Convert to dictionary for logging.
        
        Args:
            include_transcription: If True, include transcription (use only for debugging)
            
        Returns:
            Dictionary representation without sensitive data by default
        """
        data = {
            'session_id': str(self.session_id),
            'command_count': len(self.commands),
            'commands': [cmd.to_dict() for cmd in self.commands],
            'mqtt_messages': self.mqtt_messages,
            'errors': self.errors,
            'feedback': self.feedback,
            'duration_ms': self.duration_ms,
            'start_time': self.start_time.isoformat()
        }
        
        if self.end_time:
            data['end_time'] = self.end_time.isoformat()
        
        # Only include transcription if explicitly requested (debugging only)
        if include_transcription and self.transcription:
            data['transcription'] = self.transcription
        
        return data
    
    def to_json(self, include_transcription: bool = False) -> str:
        """Convert to JSON string for logging."""
        return json.dumps(self.to_dict(include_transcription=include_transcription))
