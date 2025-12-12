"""MQTT broker configuration management."""
import os
from typing import Optional
from dataclasses import dataclass

from ..utils.exceptions import ConfigurationError


@dataclass
class MQTTConfig:
    """MQTT broker configuration."""
    
    host: str
    port: int
    username: Optional[str] = None
    password: Optional[str] = None
    client_id: Optional[str] = None
    
    @classmethod
    def from_env(cls) -> 'MQTTConfig':
        """Load MQTT configuration from environment variables.
        
        Returns:
            MQTTConfig instance
            
        Raises:
            ConfigurationError: If required configuration is missing or invalid
        """
        host = os.getenv('MQTT_BROKER_HOST', 'localhost')
        port_str = os.getenv('MQTT_BROKER_PORT', '1883')
        
        try:
            port = int(port_str)
        except ValueError:
            raise ConfigurationError(
                f"Invalid MQTT_BROKER_PORT: must be an integer, got '{port_str}'"
            )
        
        if not 1 <= port <= 65535:
            raise ConfigurationError(
                f"Invalid MQTT_BROKER_PORT: must be between 1-65535, got {port}"
            )
        
        username = os.getenv('MQTT_USERNAME')
        password = os.getenv('MQTT_PASSWORD')
        client_id = os.getenv('MQTT_CLIENT_ID')
        
        # If username provided, password should also be provided
        if username and not password:
            raise ConfigurationError(
                "MQTT_USERNAME provided but MQTT_PASSWORD is missing"
            )
        
        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            client_id=client_id
        )
    
    def validate(self) -> None:
        """Validate configuration completeness.
        
        Raises:
            ConfigurationError: If configuration is invalid
        """
        if not self.host:
            raise ConfigurationError("MQTT broker host is required")
        
        if not isinstance(self.port, int):
            raise ConfigurationError("MQTT broker port must be an integer")
        
        if not 1 <= self.port <= 65535:
            raise ConfigurationError(
                f"MQTT broker port must be between 1-65535, got {self.port}"
            )
