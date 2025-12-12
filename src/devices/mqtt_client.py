"""MQTT client for smart home device communication.

This module provides the MQTT client interface for publishing commands
and subscribing to device state updates.
"""
import json
import logging
import time
from typing import List, Callable, Optional, Dict, Any

import paho.mqtt.client as mqtt

from src.devices.mqtt_config import MQTTConfig
from src.devices.models import MQTTMessage
from src.command.models import Command
from src.utils.exceptions import MQTTConnectionError, MQTTPublishError

logger = logging.getLogger(__name__)


class MQTTClient:
    """MQTT client for publishing commands and receiving state updates.
    
    Enforces QoS 1 for all messages per FR-020.
    Handles connection management, publishing, and subscriptions.
    """
    
    def __init__(self, config: MQTTConfig):
        """Initialize MQTT client.
        
        Args:
            config: MQTT broker configuration
        """
        self.config = config
        self._client = mqtt.Client(client_id=f"xhome_{int(time.time())}")
        self._connected = False
        self._message_callback: Optional[Callable[[str, Dict], None]] = None
        
        # Set up callbacks
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message
        
        # Set up authentication if provided
        if self.config.username:
            self._client.username_pw_set(
                self.config.username,
                self.config.password
            )
        
        logger.info(f"MQTT client initialized for {self.config.host}:{self.config.port}")
    
    def connect(self, timeout: int = 10) -> None:
        """Connect to MQTT broker.
        
        Args:
            timeout: Connection timeout in seconds (default: 10)
            
        Raises:
            MQTTConnectionError: If connection fails
        """
        try:
            logger.info(f"Connecting to MQTT broker at {self.config.host}:{self.config.port}")
            
            self._client.connect(
                self.config.host,
                self.config.port,
                keepalive=60
            )
            
            # Start network loop in background
            self._client.loop_start()
            
            # Wait for connection
            start_time = time.time()
            while not self._connected:
                if time.time() - start_time > timeout:
                    raise MQTTConnectionError(
                        f"Connection timeout after {timeout}s"
                    )
                time.sleep(0.1)
            
            logger.info("Successfully connected to MQTT broker")
            
        except Exception as e:
            logger.error(f"Failed to connect to MQTT broker: {e}")
            raise MQTTConnectionError(f"Connection failed: {e}") from e
    
    def disconnect(self) -> None:
        """Disconnect from MQTT broker and clean up."""
        if self._connected:
            logger.info("Disconnecting from MQTT broker")
            self._client.loop_stop()
            self._client.disconnect()
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if client is connected to broker.
        
        Returns:
            True if connected, False otherwise
        """
        return self._connected
    
    def publish(self, message: MQTTMessage) -> None:
        """Publish MQTT message to broker.
        
        Args:
            message: MQTTMessage to publish
            
        Raises:
            MQTTPublishError: If publish fails or not connected
        """
        if not self._connected:
            raise MQTTPublishError("Not connected to MQTT broker")
        
        try:
            # Convert payload to JSON
            payload_json = message.to_json()
            
            logger.debug(
                f"Publishing to {message.topic}: {payload_json} "
                f"(QoS {message.qos})"
            )
            
            result = self._client.publish(
                message.topic,
                payload_json,
                qos=message.qos,
                retain=False
            )
            
            # Wait for publish to complete (QoS 1)
            result.wait_for_publish()
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                raise MQTTPublishError(
                    f"Publish failed with code {result.rc}"
                )
            
            logger.info(f"Published message to {message.topic}")
            
        except Exception as e:
            logger.error(f"Failed to publish message: {e}")
            raise MQTTPublishError(f"Publish failed: {e}") from e
    
    def publish_command(self, command: Command, topic: str) -> None:
        """Publish command as MQTT message.
        
        Convenience method that converts Command to MQTTMessage.
        
        Args:
            command: Command to publish
            topic: MQTT topic to publish to
            
        Raises:
            MQTTPublishError: If publish fails
        """
        # Create MQTT message from command
        message = MQTTMessage.from_command(command, topic)
        
        # Publish the message
        self.publish(message)
        
        logger.info(
            f"Published command {command.intent} for {command.device} to {topic}"
        )
    
    def subscribe(self, topics: List[str]) -> None:
        """Subscribe to MQTT topics.
        
        Args:
            topics: List of topic patterns to subscribe to
            
        Raises:
            MQTTConnectionError: If not connected
        """
        if not self._connected:
            raise MQTTConnectionError("Not connected to MQTT broker")
        
        # Subscribe to all topics with QoS 1
        for topic in topics:
            logger.debug(f"Subscribing to {topic}")
            result, _ = self._client.subscribe(topic, qos=1)
            
            if result != mqtt.MQTT_ERR_SUCCESS:
                logger.error(f"Failed to subscribe to {topic}")
            else:
                logger.info(f"Subscribed to {topic}")
    
    def set_message_callback(
        self,
        callback: Callable[[str, Dict[str, Any]], None]
    ) -> None:
        """Set callback for received messages.
        
        Args:
            callback: Function to call with (topic, payload) when message received
        """
        self._message_callback = callback
        logger.debug("Message callback registered")
    
    def _on_connect(
        self,
        client,
        userdata,
        flags,
        rc,
        properties=None
    ) -> None:
        """Callback for successful connection."""
        if rc == 0:
            self._connected = True
            logger.info("MQTT connection established")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def _on_disconnect(self, client, userdata, rc, properties=None) -> None:
        """Callback for disconnection."""
        self._connected = False
        if rc != 0:
            logger.warning(f"Unexpected MQTT disconnection (code {rc})")
        else:
            logger.info("MQTT disconnected")
    
    def _on_message(self, client, userdata, msg) -> None:
        """Callback for received messages."""
        try:
            # Parse JSON payload
            payload = json.loads(msg.payload.decode('utf-8'))
            
            logger.debug(f"Received message on {msg.topic}: {payload}")
            
            # Call user callback if set
            if self._message_callback:
                self._message_callback(msg.topic, payload)
                
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse message payload: {e}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
