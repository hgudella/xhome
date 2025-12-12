"""Data models for device mapping and MQTT messages."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Union, List, Optional
import json


@dataclass
class DeviceMapping:
    """Links natural language device references to MQTT topics."""
    
    name: str
    aliases: List[str]
    device_type: str
    command_topic: str
    state_topic: str
    capabilities: List[str]
    location: Optional[str] = None
    
    def supports_capability(self, capability: str) -> bool:
        """Check if device supports a specific capability."""
        return capability in self.capabilities
    
    def matches(self, user_input: str) -> bool:
        """Check if user input matches this device."""
        normalized = user_input.lower().strip()
        return normalized == self.name or normalized in [a.lower() for a in self.aliases]


@dataclass
class MQTTMessage:
    """Represents a message to be published to the MQTT broker."""
    
    topic: str
    payload: Union[Dict[str, Any], str]
    qos: int = 1  # Fixed per FR-020 (at least once delivery)
    retain: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    device_id: Optional[str] = None
    
    def __post_init__(self):
        """Validate message after initialization."""
        if not self.topic:
            raise ValueError("MQTT topic cannot be empty")
        
        if self.qos not in (0, 1, 2):
            raise ValueError(f"Invalid QoS level: {self.qos}. Must be 0, 1, or 2")
        
        # Ensure QoS is 1 per FR-020
        if self.qos != 1:
            self.qos = 1
        
        # Validate no wildcards in topic (can't publish to wildcards)
        if '+' in self.topic or '#' in self.topic:
            raise ValueError("Cannot publish to topics with wildcards (+ or #)")
    
    def to_json(self) -> str:
        """Serialize payload to JSON string.
        
        Returns:
            JSON string representation of payload
        """
        if isinstance(self.payload, dict):
            return json.dumps(self.payload)
        return str(self.payload)
    
    @classmethod
    def from_command(cls, command, topic: str) -> 'MQTTMessage':
        """Create MQTT message from a Command.
        
        Args:
            command: Command object with intent and parameters
            topic: MQTT topic to publish to
            
        Returns:
            MQTTMessage ready for publishing
        """
        return cls(
            topic=topic,
            payload=command.to_mqtt_payload(),
            qos=1  # Fixed per FR-020
        )
