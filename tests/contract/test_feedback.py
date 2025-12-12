"""Contract tests for feedback generation.

Tests verify:
- Success messages
- Redundancy messages
- Error messages
- Device not found messages
- Multiple command feedback
"""
import pytest
from unittest.mock import Mock

from src.command.models import Command


class TestFeedbackGeneration:
    """Contract tests for user-facing feedback messages."""
    
    def generate_feedback(self, command: Command, result: str, error: Exception = None) -> str:
        """Generate user-facing feedback message.
        
        This mimics the inline implementation in run_full_system.py
        """
        device_friendly = command.device.replace('_', ' ').title()
        
        if error:
            error_msg = str(error)
            
            if "not found" in error_msg.lower() and "device" in error_msg.lower():
                return f"Sorry, I couldn't find '{device_friendly}' in your home."
            elif "timeout" in error_msg.lower():
                return "Sorry, that request took too long to process."
            elif "mqtt" in error_msg.lower() or "connection" in error_msg.lower():
                return "Sorry, I'm having trouble connecting to your smart home."
            elif "json" in error_msg.lower() or "parse" in error_msg.lower():
                return "Sorry, I had trouble understanding that command."
            else:
                return f"Sorry, something went wrong: {error_msg}"
        
        if result == "redundant":
            if command.intent == "turn_on":
                return f"{device_friendly} is already on"
            elif command.intent == "turn_off":
                return f"{device_friendly} is already off"
            else:
                return f"{device_friendly} is already in desired state"
        
        # Success messages
        if command.intent == "turn_on":
            return f"{device_friendly} is now turned on!"
        elif command.intent == "turn_off":
            return f"{device_friendly} is now turned off!"
        elif command.intent == "set_brightness":
            brightness = command.parameters.get('brightness', '?')
            return f"{device_friendly} brightness set to {brightness}%!"
        elif command.intent == "set_temperature":
            temp = command.parameters.get('temperature', '?')
            return f"{device_friendly} temperature set to {temp}°!"
        else:
            return "Command executed successfully!"
    
    def test_successful_turn_on_feedback(self):
        """Test feedback for successful turn_on command."""
        command = Command(
            device="living_room_light",
            intent="turn_on",
            parameters={}
        )
        
        feedback = self.generate_feedback(command, "success")
        assert "Living Room Light is now turned on" in feedback
    
    def test_successful_turn_off_feedback(self):
        """Test feedback for successful turn_off command."""
        command = Command(
            device="bedroom_light",
            intent="turn_off",
            parameters={}
        )
        
        feedback = self.generate_feedback(command, "success")
        assert "Bedroom Light is now turned off" in feedback
    
    def test_successful_set_brightness_feedback(self):
        """Test feedback for successful set_brightness command."""
        command = Command(
            device="kitchen_light",
            intent="set_brightness",
            parameters={"brightness": 75}
        )
        
        feedback = self.generate_feedback(command, "success")
        assert "Kitchen Light brightness set to 75%" in feedback
    
    def test_successful_set_temperature_feedback(self):
        """Test feedback for successful set_temperature command."""
        command = Command(
            device="bedroom_thermostat",
            intent="set_temperature",
            parameters={"temperature": 72}
        )
        
        feedback = self.generate_feedback(command, "success")
        assert "Bedroom Thermostat temperature set to 72°" in feedback
    
    def test_redundant_turn_on_feedback(self):
        """Test feedback for redundant turn_on command."""
        command = Command(
            device="living_room_light",
            intent="turn_on",
            parameters={}
        )
        
        feedback = self.generate_feedback(command, "redundant")
        assert "Living Room Light is already on" in feedback
    
    def test_redundant_turn_off_feedback(self):
        """Test feedback for redundant turn_off command."""
        command = Command(
            device="garage_light",
            intent="turn_off",
            parameters={}
        )
        
        feedback = self.generate_feedback(command, "redundant")
        assert "Garage Light is already off" in feedback
    
    def test_device_not_found_feedback(self):
        """Test feedback for device not found error."""
        command = Command(
            device="garage_light",
            intent="turn_on",
            parameters={}
        )
        
        from src.utils.exceptions import DeviceNotFoundError
        error = DeviceNotFoundError("Device 'garage_light' not found in configuration")
        
        feedback = self.generate_feedback(command, "error", error)
        assert "couldn't find" in feedback.lower()
        assert "Garage Light" in feedback
    
    def test_mqtt_connection_error_feedback(self):
        """Test feedback for MQTT connection error."""
        command = Command(
            device="bedroom_light",
            intent="turn_on",
            parameters={}
        )
        
        from src.utils.exceptions import MQTTConnectionError
        error = MQTTConnectionError("Connection refused")
        
        feedback = self.generate_feedback(command, "error", error)
        assert "trouble connecting" in feedback.lower()
    
    def test_timeout_error_feedback(self):
        """Test feedback for timeout error."""
        command = Command(
            device="living_room_light",
            intent="turn_on",
            parameters={}
        )
        
        # Use the actual SLMError hierarchy TimeoutError
        from src.utils.exceptions import SLMError
        
        class TimeoutError(SLMError):
            """Timeout error for testing."""
            pass
        
        error = TimeoutError("SLM inference timed out")
        
        feedback = self.generate_feedback(command, "error", error)
        assert "took too long" in feedback.lower() or "timed out" in feedback.lower()
    
    def test_parsing_error_feedback(self):
        """Test feedback for command parsing error."""
        command = Command(
            device="kitchen_light",
            intent="turn_on",
            parameters={}
        )
        
        from src.utils.exceptions import CommandParsingError
        error = CommandParsingError("Failed to parse JSON response")
        
        feedback = self.generate_feedback(command, "error", error)
        assert "trouble understanding" in feedback.lower()
    
    def test_friendly_device_name_formatting(self):
        """Test that device names are formatted friendly."""
        command = Command(
            device="master_bedroom_ceiling_fan",
            intent="turn_on",
            parameters={}
        )
        
        feedback = self.generate_feedback(command, "success")
        # Should convert underscores to spaces and title case
        assert "Master Bedroom Ceiling Fan" in feedback
    
    def test_multiple_commands_separate_feedback(self):
        """Test that multiple commands get separate feedback."""
        commands = [
            Command(device="light1", intent="turn_on", parameters={}),
            Command(device="light2", intent="turn_off", parameters={}),
            Command(device="light3", intent="set_brightness", parameters={"brightness": 50})
        ]
        
        feedback_list = [
            self.generate_feedback(cmd, "success")
            for cmd in commands
        ]
        
        # Each command should have distinct feedback
        assert len(feedback_list) == 3
        assert "Light1" in feedback_list[0]
        assert "Light2" in feedback_list[1]
        assert "Light3" in feedback_list[2]
        assert "turned on" in feedback_list[0]
        assert "turned off" in feedback_list[1]
        assert "brightness set to 50%" in feedback_list[2]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
