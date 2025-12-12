"""Integration tests for MQTT command publishing pipeline.

Tests the complete pipeline from Command to MQTT message publishing.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from src.devices.mqtt_client import MQTTClient
from src.devices.mqtt_config import MQTTConfig
from src.devices.models import MQTTMessage
from src.command.models import Command


class TestMQTTPublishingPipeline:
    """Integration tests for MQTT publishing."""
    
    @pytest.fixture
    def mqtt_config(self):
        """Test MQTT configuration."""
        return MQTTConfig(
            host="localhost",
            port=1883
        )
    
    def test_mqtt_message_from_command_turn_on(self):
        """Test: Convert turn_on command to MQTT message."""
        command = Command(
            intent="turn_on",
            device="living_room_light",
            confidence=0.95
        )
        
        message = MQTTMessage.from_command(
            command,
            topic="home/light/living_room/set"
        )
        
        assert message.topic == "home/light/living_room/set"
        assert message.qos == 1  # Enforced
        assert message.payload == {"state": "ON"}
    
    def test_mqtt_message_from_command_set_brightness(self):
        """Test: Convert set_brightness command to MQTT message."""
        command = Command(
            intent="set_brightness",
            device="bedroom_light",
            parameters={"brightness": 75},
            confidence=0.9
        )
        
        message = MQTTMessage.from_command(
            command,
            topic="home/light/bedroom/set"
        )
        
        assert message.payload == {"state": "ON", "brightness": 75}
    
    def test_mqtt_client_initialization(self, mqtt_config):
        """Test: MQTT client initializes correctly."""
        client = MQTTClient(mqtt_config)
        
        assert client.config == mqtt_config
        assert not client.is_connected()
    
    @patch('paho.mqtt.client.Client')
    def test_mqtt_publish_command_mocked(self, mock_mqtt_class, mqtt_config):
        """Test: Publish command through MQTT client (mocked)."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mqtt_class.return_value = mock_client_instance
        mock_client_instance.publish.return_value = MagicMock(rc=0)
        
        # Create client
        client = MQTTClient(mqtt_config)
        client._connected = True  # Fake connection
        
        # Create command
        command = Command(
            intent="turn_on",
            device="kitchen_light",
            confidence=0.95
        )
        
        # Publish
        client.publish_command(command, "home/light/kitchen/set")
        
        # Verify publish was called
        assert mock_client_instance.publish.called
        
    @patch('paho.mqtt.client.Client')
    def test_qos_1_enforced_in_publishing(self, mock_mqtt_class, mqtt_config):
        """Test: QoS 1 is enforced in all publishes (FR-020)."""
        # Setup mock
        mock_client_instance = MagicMock()
        mock_mqtt_class.return_value = mock_client_instance
        mock_publish_result = MagicMock(rc=0)
        mock_client_instance.publish.return_value = mock_publish_result
        
        # Create client
        client = MQTTClient(mqtt_config)
        client._connected = True
        
        # Create message with wrong QoS
        message = MQTTMessage(
            topic="home/test/command",
            payload={"state": "ON"},
            qos=0  # Try QoS 0
        )
        
        # QoS should be forced to 1
        assert message.qos == 1
        
        # Publish
        client.publish(message)
        
        # Verify publish called with QoS 1
        call_args = mock_client_instance.publish.call_args
        assert call_args[1]['qos'] == 1
