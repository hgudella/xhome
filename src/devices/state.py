"""Device state tracking."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import threading
import logging

logger = logging.getLogger(__name__)


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


class DeviceStateCache:
    """Thread-safe cache for device states with TTL checking.
    
    Provides centralized management of device states from MQTT with:
    - Thread-safe access for concurrent operations
    - TTL-based staleness detection
    - Redundancy detection for duplicate commands
    - Automatic cleanup of stale entries
    """
    
    def __init__(self, default_ttl: int = 300):
        """Initialize state cache.
        
        Args:
            default_ttl: Default time-to-live for states in seconds (default: 5 minutes)
        """
        self._states: Dict[str, DeviceState] = {}
        self._lock = threading.RLock()
        self.default_ttl = default_ttl
        logger.info(f"DeviceStateCache initialized with TTL={default_ttl}s")
    
    def update(self, device_id: str, state_data: Dict[str, Any]) -> None:
        """Update or create device state.
        
        Thread-safe operation that updates existing state or creates new entry.
        
        Args:
            device_id: Unique device identifier
            state_data: State data from MQTT message
        """
        with self._lock:
            if device_id in self._states:
                self._states[device_id].update(state_data)
                logger.debug(f"Updated state for {device_id}")
            else:
                self._states[device_id] = DeviceState(
                    device_id=device_id,
                    state=state_data
                )
                logger.info(f"Created new state entry for {device_id}")
    
    def get(self, device_id: str) -> Optional[DeviceState]:
        """Get device state if available and not stale.
        
        Args:
            device_id: Device identifier to query
            
        Returns:
            DeviceState if available and fresh, None if not found or stale
        """
        with self._lock:
            state = self._states.get(device_id)
            
            if state is None:
                logger.debug(f"No state found for {device_id}")
                return None
            
            if state.is_stale(self.default_ttl):
                logger.warning(
                    f"State for {device_id} is stale "
                    f"(age: {(datetime.utcnow() - state.last_updated).total_seconds():.1f}s, "
                    f"TTL: {self.default_ttl}s)"
                )
                return None
            
            return state
    
    def get_all(self, include_stale: bool = False) -> Dict[str, DeviceState]:
        """Get all device states.
        
        Args:
            include_stale: Whether to include stale states (default: False)
            
        Returns:
            Dictionary of device_id to DeviceState
        """
        with self._lock:
            if include_stale:
                return self._states.copy()
            else:
                return {
                    device_id: state
                    for device_id, state in self._states.items()
                    if not state.is_stale(self.default_ttl)
                }
    
    def is_redundant(self, device_id: str, intent: str, parameters: Optional[Dict[str, Any]] = None) -> bool:
        """Check if command is redundant based on current state.
        
        A command is redundant if:
        - Device state is available and fresh
        - Desired state matches current state
        
        Examples:
        - "Turn on" when device is already on
        - "Set brightness to 50" when brightness is already 50
        - "Set temperature to 72" when temperature is already 72
        
        Args:
            device_id: Device identifier
            intent: Command intent (turn_on, turn_off, set_brightness, etc.)
            parameters: Optional command parameters
            
        Returns:
            True if command is redundant, False otherwise
        """
        state = self.get(device_id)
        if state is None:
            # No fresh state available, cannot determine redundancy
            return False
        
        current_on_state = state.is_on()
        
        # Check intent-specific redundancy
        if intent == "turn_on":
            if current_on_state is True:
                logger.info(f"Redundant command: {device_id} is already ON")
                return True
        
        elif intent == "turn_off":
            if current_on_state is False:
                logger.info(f"Redundant command: {device_id} is already OFF")
                return True
        
        elif intent == "set_brightness" and parameters:
            target_brightness = parameters.get('brightness')
            current_brightness = state.get_value('brightness')
            if target_brightness is not None and current_brightness == target_brightness:
                logger.info(
                    f"Redundant command: {device_id} brightness already at {target_brightness}%"
                )
                return True
        
        elif intent == "set_temperature" and parameters:
            target_temp = parameters.get('temperature')
            current_temp = state.get_value('temperature')
            if target_temp is not None and current_temp == target_temp:
                logger.info(
                    f"Redundant command: {device_id} temperature already at {target_temp}°"
                )
                return True
        
        return False
    
    def mark_unavailable(self, device_id: str) -> None:
        """Mark device as unavailable.
        
        Args:
            device_id: Device identifier to mark unavailable
        """
        with self._lock:
            if device_id in self._states:
                self._states[device_id].available = False
                logger.warning(f"Marked {device_id} as unavailable")
    
    def cleanup_stale(self) -> int:
        """Remove stale state entries.
        
        Returns:
            Number of states removed
        """
        with self._lock:
            stale_devices = [
                device_id
                for device_id, state in self._states.items()
                if state.is_stale(self.default_ttl)
            ]
            
            for device_id in stale_devices:
                del self._states[device_id]
            
            if stale_devices:
                logger.info(f"Cleaned up {len(stale_devices)} stale state(s): {stale_devices}")
            
            return len(stale_devices)
    
    def clear(self) -> None:
        """Clear all cached states."""
        with self._lock:
            count = len(self._states)
            self._states.clear()
            logger.info(f"Cleared {count} state(s) from cache")
