"""Command router for orchestrating voice-to-MQTT pipeline.

This module provides the main orchestration layer that connects:
- Voice transcription (from Feature 001)
- Command parsing (SLM)
- Device mapping
- MQTT publishing
"""
import logging
from typing import Optional, List
from pathlib import Path

from src.command.parser import CommandParser
from src.command.models import Command
from src.command.session import CommandSession
from src.devices.mqtt_client import MQTTClient
from src.devices.mqtt_config import MQTTConfig
from src.devices.config import DeviceConfig
from src.devices.state import DeviceState
from src.utils.exceptions import (
    DeviceNotFoundError,
    MQTTPublishError,
    CommandParsingError
)

logger = logging.getLogger(__name__)


class CommandRouter:
    """Orchestrates the complete voice-to-MQTT command pipeline.
    
    Integrates:
    - Command parsing (SLM)
    - Device name resolution
    - MQTT publishing
    - Session tracking
    """
    
    def __init__(
        self,
        model_path: str,
        device_config_path: str,
        mqtt_config: MQTTConfig,
        enable_state_tracking: bool = False
    ):
        """Initialize command router.
        
        Args:
            model_path: Path to SLM model file
            device_config_path: Path to devices.yaml
            mqtt_config: MQTT broker configuration
            enable_state_tracking: Whether to track device states (default: False)
        """
        # Initialize command parser (SLM + device config)
        self.command_parser = CommandParser(
            model_path=model_path,
            device_config_path=device_config_path
        )
        
        # Initialize MQTT client
        self.mqtt_client = MQTTClient(mqtt_config)
        
        # Device config for topic resolution
        self.device_config = self.command_parser.device_config
        
        # State tracking (for User Story 3)
        self.enable_state_tracking = enable_state_tracking
        self.device_states: dict[str, DeviceState] = {}
        
        logger.info("CommandRouter initialized")
    
    def connect_mqtt(self) -> None:
        """Connect to MQTT broker."""
        self.mqtt_client.connect()
        logger.info("MQTT connection established")
        
        # Subscribe to state topics if state tracking enabled
        if self.enable_state_tracking:
            self._subscribe_to_state_topics()
    
    def process_transcription(
        self,
        transcription: str,
        session: Optional[CommandSession] = None
    ) -> CommandSession:
        """Process voice transcription through complete pipeline.
        
        Main entry point for voice-to-MQTT flow:
        1. Parse transcription to Command(s)
        2. Resolve device names
        3. Publish to MQTT
        4. Track in session
        
        Args:
            transcription: Voice transcription from Feature 001
            session: Optional existing session (creates new if None)
            
        Returns:
            CommandSession with results and tracking info
            
        Raises:
            DeviceNotFoundError: If device not found in configuration
            MQTTPublishError: If MQTT publishing fails
        """
        # Create or use existing session
        if session is None:
            session = CommandSession(transcription=transcription)
        else:
            session.transcription = transcription
        
        try:
            # Parse transcription to commands
            commands = self.command_parser.parse(
                transcription,
                validate_devices=True,
                session=session
            )
            
            if not commands:
                logger.info("No commands extracted from transcription")
                return session
            
            # Process each command
            for command in commands:
                self._publish_command(command, session)
            
            # Mark session complete
            session.complete()
            
            logger.info(
                f"Processed transcription in {session.duration_ms}ms: "
                f"{len(commands)} command(s) published"
            )
            
        except Exception as e:
            logger.error(f"Failed to process transcription: {e}")
            session.errors.append(str(e))
            raise
        
        return session
    
    def _publish_command(
        self,
        command: Command,
        session: CommandSession
    ) -> None:
        """Publish command to MQTT.
        
        Args:
            command: Parsed and validated command
            session: Session for tracking
            
        Raises:
            DeviceNotFoundError: If device mapping not found
            MQTTPublishError: If publish fails
        """
        # Get device mapping for topic
        device = self.device_config.find_device(command.device)
        if device is None:
            raise DeviceNotFoundError(
                f"Device '{command.device}' not found in configuration"
            )
        
        # Publish to MQTT
        topic = device.command_topic
        
        try:
            self.mqtt_client.publish_command(command, topic)
            
            # Track in session
            session.mqtt_messages.append({
                "topic": topic,
                "payload": command.to_mqtt_payload(),
                "device": command.device
            })
            
            logger.info(
                f"Published {command.intent} for {command.device} to {topic}"
            )
            
        except MQTTPublishError as e:
            logger.error(f"Failed to publish command: {e}")
            session.errors.append(f"MQTT publish failed: {e}")
            raise
    
    def _subscribe_to_state_topics(self) -> None:
        """Subscribe to all device state topics for tracking."""
        if not self.enable_state_tracking:
            return
        
        state_topics = self.device_config.get_state_topics()
        
        if state_topics:
            logger.info(f"Subscribing to {len(state_topics)} state topics")
            
            # Set callback for state updates
            self.mqtt_client.set_message_callback(self._handle_state_update)
            
            # Subscribe to topics
            self.mqtt_client.subscribe(state_topics)
    
    def _handle_state_update(self, topic: str, payload: dict) -> None:
        """Handle incoming device state update.
        
        Args:
            topic: MQTT topic of state update
            payload: State payload from device
        """
        # Extract device name from topic (assuming pattern: home/{type}/{name}/state)
        parts = topic.split('/')
        if len(parts) >= 3:
            device_name = parts[2]
            
            # Update or create device state
            if device_name in self.device_states:
                self.device_states[device_name].update(payload)
            else:
                self.device_states[device_name] = DeviceState(
                    device_id=device_name,
                    state=payload
                )
            
            logger.debug(f"Updated state for {device_name}: {payload}")
    
    def get_device_state(self, device_name: str) -> Optional[DeviceState]:
        """Get current state of a device.
        
        Args:
            device_name: Name of device to query
            
        Returns:
            DeviceState if available, None otherwise
        """
        return self.device_states.get(device_name)
    
    def cleanup(self) -> None:
        """Clean up resources."""
        logger.info("Cleaning up CommandRouter")
        self.mqtt_client.disconnect()
        self.command_parser.cleanup()
