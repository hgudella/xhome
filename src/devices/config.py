"""Device configuration management."""
import yaml
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..utils.exceptions import ConfigurationError


@dataclass
class DeviceMapping:
    """Represents a device mapping from configuration."""
    
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


class DeviceConfig:
    """Manages device configuration from YAML file."""
    
    VALID_DEVICE_TYPES = {'light', 'switch', 'thermostat', 'fan', 'sensor'}
    VALID_CAPABILITIES = {
        'on_off', 'brightness', 'color_temp', 'color',
        'temperature', 'humidity', 'mode'
    }
    
    def __init__(self, config_path: str = "config/devices.yaml"):
        """Initialize device configuration.
        
        Args:
            config_path: Path to devices.yaml configuration file
            
        Raises:
            ConfigurationError: If configuration file is missing or invalid
        """
        self.config_path = Path(config_path)
        self.devices: Dict[str, DeviceMapping] = {}
        self.mqtt_config: Dict[str, Any] = {}
        self._load_config()
    
    def _load_config(self) -> None:
        """Load and parse YAML configuration."""
        if not self.config_path.exists():
            raise ConfigurationError(
                f"Configuration file not found: {self.config_path}"
            )
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ConfigurationError(f"Invalid YAML syntax: {e}")
        
        if not isinstance(config, dict):
            raise ConfigurationError("Configuration must be a dictionary")
        
        # Parse devices
        devices_config = config.get('devices', {})
        if not isinstance(devices_config, dict):
            raise ConfigurationError("'devices' must be a dictionary")
        
        for device_type, device_list in devices_config.items():
            if not isinstance(device_list, list):
                raise ConfigurationError(
                    f"Device type '{device_type}' must contain a list"
                )
            
            for device_data in device_list:
                self._parse_device(device_data, device_type)
        
        # Parse MQTT broker config
        self.mqtt_config = config.get('mqtt_broker', {})
        if not isinstance(self.mqtt_config, dict):
            raise ConfigurationError("'mqtt_broker' must be a dictionary")
    
    def _parse_device(self, device_data: Dict[str, Any], device_type: str) -> None:
        """Parse and validate a single device."""
        try:
            name = device_data['name']
            aliases = device_data.get('aliases', [])
            mqtt = device_data['mqtt']
            capabilities = device_data.get('capabilities', [])
            location = device_data.get('location')
            
            # Validation
            if not name or not isinstance(name, str):
                raise ConfigurationError(f"Device name is required and must be a string")
            
            if name in self.devices:
                raise ConfigurationError(f"Duplicate device name: {name}")
            
            if not isinstance(aliases, list) or not aliases:
                raise ConfigurationError(
                    f"Device '{name}' must have at least one alias"
                )
            
            if device_type not in self.VALID_DEVICE_TYPES:
                raise ConfigurationError(
                    f"Invalid device type '{device_type}' for device '{name}'. "
                    f"Must be one of: {', '.join(self.VALID_DEVICE_TYPES)}"
                )
            
            command_topic = mqtt.get('command_topic')
            state_topic = mqtt.get('state_topic')
            
            if not command_topic or not isinstance(command_topic, str):
                raise ConfigurationError(
                    f"Device '{name}' must have a valid command_topic"
                )
            
            if not state_topic or not isinstance(state_topic, str):
                raise ConfigurationError(
                    f"Device '{name}' must have a valid state_topic"
                )
            
            # Validate MQTT topic format (no wildcards in command topics)
            if '+' in command_topic or '#' in command_topic:
                raise ConfigurationError(
                    f"Command topic for '{name}' cannot contain wildcards"
                )
            
            # Validate capabilities
            invalid_caps = set(capabilities) - self.VALID_CAPABILITIES
            if invalid_caps:
                raise ConfigurationError(
                    f"Invalid capabilities for '{name}': {', '.join(invalid_caps)}. "
                    f"Valid capabilities: {', '.join(self.VALID_CAPABILITIES)}"
                )
            
            # Create device mapping
            device = DeviceMapping(
                name=name,
                aliases=aliases,
                device_type=device_type,
                command_topic=command_topic,
                state_topic=state_topic,
                capabilities=capabilities,
                location=location
            )
            
            self.devices[name] = device
            
        except KeyError as e:
            raise ConfigurationError(
                f"Missing required field in device configuration: {e}"
            )
    
    def get_device(self, device_name: str) -> Optional[DeviceMapping]:
        """Get device by exact name.
        
        Args:
            device_name: Exact device name
            
        Returns:
            DeviceMapping if found, None otherwise
        """
        return self.devices.get(device_name)
    
    def find_device(self, user_input: str) -> Optional[DeviceMapping]:
        """Find device by name or alias.
        
        Args:
            user_input: User's device reference (name or alias)
            
        Returns:
            DeviceMapping if found, None otherwise
        """
        for device in self.devices.values():
            if device.matches(user_input):
                return device
        return None
    
    def get_all_devices(self) -> List[DeviceMapping]:
        """Get all configured devices."""
        return list(self.devices.values())
    
    def get_devices_by_type(self, device_type: str) -> List[DeviceMapping]:
        """Get all devices of a specific type."""
        return [
            device for device in self.devices.values()
            if device.device_type == device_type
        ]
    
    def get_state_topics(self) -> List[str]:
        """Get all state topics for MQTT subscription."""
        return [device.state_topic for device in self.devices.values()]
