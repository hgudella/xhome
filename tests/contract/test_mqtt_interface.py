"""Contract tests for MQTT client interface.

These tests define the expected behavior of the MQTT client.
Write these FIRST before implementation (TDD Red phase).
"""
import pytest
import time
from pathlib import Path

from src.devices.models import MQTTMessage
from src.command.models import Command
from src.utils.exceptions import MQTTConnectionError, MQTTPublishError


class TestMQTTClientContract:
    """Contract tests for MQTT client interface."""
    
    @pytest.fixture
    def mqtt_config(self):
        """MQTT configuration for testing."""
        from src.devices.mqtt_config import MQTTConfig
        # Use test broker or localhost
        return MQTTConfig(
            host="localhost",
            port=1883,
            username=None,
            password=None
        )
    
    @pytest.fixture
    def mqtt_client(self, mqtt_config):
        """Create MQTT client instance for testing."""
        from src.devices.mqtt_client import MQTTClient
        
        client = MQTTClient(mqtt_config)
        yield client
        client.disconnect()
    
    def test_connect_to_broker_successfully(self, mqtt_client):
        """Test: Client connects to MQTT broker successfully."""
        mqtt_client.connect()
        
        assert mqtt_client.is_connected(), "Client should be connected"
    
    def test_connect_fails_with_invalid_broker(self):
        """Test: Connection fails with invalid broker address."""
        from src.devices.mqtt_client import MQTTClient
        from src.devices.mqtt_config import MQTTConfig
        
        config = MQTTConfig(
            host="invalid.broker.that.does.not.exist",
            port=1883
        )
        client = MQTTClient(config)
        
        with pytest.raises(MQTTConnectionError):
            client.connect(timeout=2)
    
    def test_publish_message_to_topic(self, mqtt_client):
        """Test: Client can publish message to topic."""
        mqtt_client.connect()
        
        message = MQTTMessage(
            topic="home/test/command",
            payload={"state": "ON"},
            qos=1
        )
        
        # Should not raise exception
        mqtt_client.publish(message)
    
    def test_publish_command_as_mqtt_message(self, mqtt_client):
        """Test: Can publish Command as MQTT message."""
        mqtt_client.connect()
        
        command = Command(
            intent="turn_on",
            device="living_room_light",
            confidence=0.95
        )
        
        # Should convert command to MQTT message and publish
        mqtt_client.publish_command(
            command=command,
            topic="home/light/living_room/set"
        )
    
    def test_publish_enforces_qos_1(self, mqtt_client):
        """Test: Publishing enforces QoS 1 (FR-020)."""
        mqtt_client.connect()
        
        message = MQTTMessage(
            topic="home/test/command",
            payload={"state": "ON"},
            qos=0  # Try to use QoS 0
        )
        
        # MQTTMessage should have forced qos=1
        assert message.qos == 1, "QoS should be forced to 1"
    
    def test_publish_fails_when_not_connected(self, mqtt_client):
        """Test: Publishing fails when not connected."""
        message = MQTTMessage(
            topic="home/test/command",
            payload={"state": "ON"}
        )
        
        with pytest.raises(MQTTPublishError):
            mqtt_client.publish(message)
    
    def test_disconnect_cleans_up_connection(self, mqtt_client):
        """Test: Disconnect cleans up connection."""
        mqtt_client.connect()
        assert mqtt_client.is_connected()
        
        mqtt_client.disconnect()
        assert not mqtt_client.is_connected()
    
    def test_subscribe_to_state_topics(self, mqtt_client):
        """Test: Client can subscribe to state topics."""
        mqtt_client.connect()
        
        topics = [
            "home/light/living_room/state",
            "home/light/bedroom/state"
        ]
        
        # Should not raise exception
        mqtt_client.subscribe(topics)
    
    def test_receive_state_update_message(self, mqtt_client):
        """Test: Client can receive state update messages."""
        mqtt_client.connect()
        
        received_messages = []
        
        def on_message(topic, payload):
            received_messages.append((topic, payload))
        
        mqtt_client.set_message_callback(on_message)
        mqtt_client.subscribe(["home/test/state"])
        
        # Publish a message to ourselves
        test_message = MQTTMessage(
            topic="home/test/state",
            payload={"state": "ON", "brightness": 100}
        )
        mqtt_client.publish(test_message)
        
        # Wait for message to arrive
        time.sleep(0.5)
        
        assert len(received_messages) > 0, "Should receive published message"
        topic, payload = received_messages[0]
        assert topic == "home/test/state"
        assert payload["state"] == "ON"
