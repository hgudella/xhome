"""Device state tracking."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional


@dataclass
class DeviceState:
    """Tracks the current state of a device based on MQTT state messages."""
    
    device_id: str
    state: Dict[str, Any] = field(default_factory=dict)
    last_updated: datetime = field(default_factory=datetime.utcnow)
    available: bool = True
    
    def is_stale(self, ttl_seconds: int = 300) -> bool:
        """Check if state is stale based on TTL.
        
        Args:
            ttl_seconds: Time-to-live in seconds (default: 5 minutes)
            
        Returns:
            True if state age exceeds TTL
        """
        age = datetime.utcnow() - self.last_updated
        return age > timedelta(seconds=ttl_seconds)
    
    def update(self, new_state: Dict[str, Any]) -> None:
        """Update device state with new data.
        
        Args:
            new_state: New state data from MQTT message
        """
        self.state = new_state
        self.last_updated = datetime.utcnow()
        self.available = True
    
    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a specific state value.
        
        Args:
            key: State key to retrieve
            default: Default value if key not found
            
        Returns:
            State value or default
        """
        return self.state.get(key, default)
    
    def is_on(self) -> Optional[bool]:
        """Check if device is in ON state.
        
        Returns:
            True if ON, False if OFF, None if unknown
        """
        state_val = self.state.get('state', '').upper()
        if state_val == 'ON':
            return True
        elif state_val == 'OFF':
            return False
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            'device_id': self.device_id,
            'state': self.state,
            'last_updated': self.last_updated.isoformat(),
            'available': self.available,
            'age_seconds': (datetime.utcnow() - self.last_updated).total_seconds()
        }
