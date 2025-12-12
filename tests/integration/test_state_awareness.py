"""Integration tests for state-aware command processing.

Tests verify:
- Redundancy detection prevents duplicate commands
- Stale states don't block commands
- Unavailable states don't block commands
- Multiple devices with different states
"""
import pytest
from unittest.mock import Mock, patch

from src.command.router import CommandRouter
from src.devices.mqtt_config import MQTTConfig
from src.devices.state import DeviceStateCache


class TestStateAwarenessIntegration:
    """Integration tests for state-aware command processing."""
    
    @pytest.fixture
    def router_with_state_tracking(self):
        """Create CommandRouter with state tracking enabled."""
        mqtt_config = MQTTConfig(host="localhost", port=1883)
        
        with patch('src.command.parser.SLMEngine'):
            with patch('src.devices.mqtt_client.MQTTClient'):
                router = CommandRouter(
                    model_path="models/test.gguf",
                    device_config_path="config/devices.yaml.example",
                    mqtt_config=mqtt_config,
                    enable_state_tracking=True,
                    state_ttl=300
                )
                return router
    
    def test_redundant_turn_on_blocked(self, router_with_state_tracking):
        """Test that turn_on is blocked when device is already on."""
        router = router_with_state_tracking
        
        # Set device state to ON
        router.state_cache.update("living_room_light", {"state": "ON"})
        
        # Check redundancy
        is_redundant = router.state_cache.is_redundant(
            "living_room_light",
            "turn_on",
            {}
        )
        
        assert is_redundant is True
    
    def test_turn_on_proceeds_when_off(self, router_with_state_tracking):
        """Test that turn_on proceeds when device is off."""
        router = router_with_state_tracking
        
        # Set device state to OFF
        router.state_cache.update("living_room_light", {"state": "OFF"})
        
        # Check redundancy
        is_redundant = router.state_cache.is_redundant(
            "living_room_light",
            "turn_on",
            {}
        )
        
        assert is_redundant is False
    
    def test_stale_state_allows_command(self, router_with_state_tracking):
        """Test that stale states don't block commands."""
        router = router_with_state_tracking
        
        # Create stale state (beyond TTL)
        from datetime import datetime, timedelta
        router.state_cache.update("bedroom_light", {"state": "ON"})
        state = router.state_cache._states["bedroom_light"]
        state.last_updated = datetime.utcnow() - timedelta(seconds=400)
        
        # Get state should return None for stale
        current_state = router.state_cache.get("bedroom_light")
        assert current_state is None
        
        # Redundancy check should return False (no state available)
        is_redundant = router.state_cache.is_redundant(
            "bedroom_light",
            "turn_on",
            {}
        )
        assert is_redundant is False
    
    def test_unavailable_state_allows_command(self, router_with_state_tracking):
        """Test that unavailable states don't block commands."""
        router = router_with_state_tracking
        
        # No state for device
        is_redundant = router.state_cache.is_redundant(
            "unknown_device",
            "turn_on",
            {}
        )
        
        # Should allow command (no state to check)
        assert is_redundant is False
    
    def test_multiple_devices_different_states(self, router_with_state_tracking):
        """Test handling multiple devices with different states."""
        router = router_with_state_tracking
        
        # Set different states for multiple devices
        router.state_cache.update("living_room_light", {"state": "ON"})
        router.state_cache.update("bedroom_light", {"state": "OFF"})
        router.state_cache.update("kitchen_light", {"state": "ON", "brightness": 75})
        
        # Check each device independently
        assert router.state_cache.is_redundant("living_room_light", "turn_on", {}) is True
        assert router.state_cache.is_redundant("bedroom_light", "turn_off", {}) is True
        assert router.state_cache.is_redundant("kitchen_light", "set_brightness", {"brightness": 75}) is True
        
        # Non-redundant commands
        assert router.state_cache.is_redundant("living_room_light", "turn_off", {}) is False
        assert router.state_cache.is_redundant("bedroom_light", "turn_on", {}) is False
        assert router.state_cache.is_redundant("kitchen_light", "set_brightness", {"brightness": 50}) is False
    
    def test_get_device_state(self, router_with_state_tracking):
        """Test retrieving device state via CommandRouter."""
        router = router_with_state_tracking
        
        # Update state
        router.state_cache.update("ceiling_fan", {"state": "ON", "speed": "medium"})
        
        # Get state
        state = router.get_device_state("ceiling_fan")
        
        assert state is not None
        assert state.device_id == "ceiling_fan"
        assert state.state["state"] == "ON"
        assert state.state["speed"] == "medium"
    
    def test_state_tracking_disabled(self):
        """Test that state tracking can be disabled."""
        mqtt_config = MQTTConfig(host="localhost", port=1883)
        
        with patch('src.command.parser.SLMEngine'):
            with patch('src.devices.mqtt_client.MQTTClient'):
                router = CommandRouter(
                    model_path="models/test.gguf",
                    device_config_path="config/devices.yaml.example",
                    mqtt_config=mqtt_config,
                    enable_state_tracking=False
                )
                
                # State cache should be None
                assert router.state_cache is None
                
                # get_device_state should return None
                state = router.get_device_state("any_device")
                assert state is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
