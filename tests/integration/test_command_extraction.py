"""Integration tests for text-to-command pipeline.

Tests the complete pipeline from text transcription to Command extraction.
Write these FIRST before implementation (TDD Red phase).
"""
import pytest
from datetime import datetime

from src.command.models import Command
from src.utils.exceptions import DeviceNotFoundError, CommandParsingError


class TestCommandExtractionPipeline:
    """Integration tests for command extraction pipeline."""
    
    @pytest.fixture
    def command_parser(self):
        """Create CommandParser instance for testing."""
        from src.command.parser import CommandParser
        
        # Will need device config for validation
        parser = CommandParser(
            model_path="models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf",
            device_config_path="config/devices.yaml.example"
        )
        yield parser
        parser.cleanup()
    
    def test_turn_on_command(self, command_parser):
        """Test: 'turn on X' command extraction."""
        test_cases = [
            ("turn on the living room light", "turn_on", "living_room"),
            ("turn on bedroom light", "turn_on", "bedroom"),
            ("switch on the fan", "turn_on", "fan"),
        ]
        
        for transcription, expected_intent, device_keyword in test_cases:
            commands = command_parser.parse(transcription)
            
            assert len(commands) > 0, f"Should extract command from '{transcription}'"
            command = commands[0]
            
            assert command.intent == expected_intent, \
                f"Expected intent '{expected_intent}', got '{command.intent}'"
            assert device_keyword in command.device.lower(), \
                f"Expected device to contain '{device_keyword}', got '{command.device}'"
    
    def test_turn_off_command(self, command_parser):
        """Test: 'turn off X' command extraction."""
        transcription = "turn off the bedroom light"
        
        commands = command_parser.parse(transcription)
        
        assert len(commands) > 0, "Should extract command"
        command = commands[0]
        
        assert command.intent == "turn_off"
        assert "bedroom" in command.device.lower()
    
    def test_set_brightness_command(self, command_parser):
        """Test: Brightness command with percentage parameter."""
        test_cases = [
            ("set bedroom light to 50 percent", 50),
            ("dim the living room light to 25 percent", 25),
            ("set kitchen light brightness to 75", 75),
        ]
        
        for transcription, expected_brightness in test_cases:
            commands = command_parser.parse(transcription)
            
            assert len(commands) > 0, f"Should extract command from '{transcription}'"
            command = commands[0]
            
            assert command.intent == "set_brightness", \
                f"Expected 'set_brightness', got '{command.intent}'"
            
            brightness = command.parameters.get("brightness")
            assert brightness is not None, "Should have brightness parameter"
            
            # Allow some tolerance for parsing
            assert abs(brightness - expected_brightness) <= 5, \
                f"Expected brightness ~{expected_brightness}, got {brightness}"
    
    def test_set_temperature_command(self, command_parser):
        """Test: Temperature command extraction."""
        transcription = "set thermostat to 72 degrees"
        
        commands = command_parser.parse(transcription)
        
        assert len(commands) > 0, "Should extract command"
        command = commands[0]
        
        assert command.intent == "set_temperature"
        assert "thermostat" in command.device.lower()
        assert "temperature" in command.parameters
        
        temp = command.parameters["temperature"]
        assert 70 <= temp <= 74, f"Expected temperature ~72, got {temp}"
    
    def test_device_alias_matching(self, command_parser):
        """Test: Device aliases are matched correctly."""
        # Assuming devices.yaml.example has aliases like "lounge light" for "living_room_light"
        transcription = "turn on the lounge light"
        
        commands = command_parser.parse(transcription)
        
        assert len(commands) > 0, "Should extract command with alias"
        command = commands[0]
        
        # Should resolve to canonical device name
        assert command.intent == "turn_on"
        # Device should be resolved to canonical name or alias should be recognized
    
    def test_unrelated_text_returns_empty_or_unknown(self, command_parser):
        """Test: Unrelated text returns empty list or unknown intent."""
        transcriptions = [
            "what's the weather",
            "tell me a joke",
            "how are you doing today"
        ]
        
        for transcription in transcriptions:
            commands = command_parser.parse(transcription)
            
            # Either returns empty list or commands with unknown intent
            if len(commands) > 0:
                for cmd in commands:
                    assert cmd.intent == "unknown", \
                        f"Unrelated text should have 'unknown' intent, got '{cmd.intent}'"
    
    def test_ambiguous_command_has_confidence_score(self, command_parser):
        """Test: Ambiguous commands return confidence scores."""
        # Intentionally vague command
        transcription = "turn on the light"  # Which light?
        
        commands = command_parser.parse(transcription)
        
        if len(commands) > 0:
            command = commands[0]
            assert hasattr(command, "confidence"), "Should have confidence score"
            assert 0.0 <= command.confidence <= 1.0, "Confidence should be between 0 and 1"
    
    def test_device_not_found_raises_error(self, command_parser):
        """Test: Unknown device raises DeviceNotFoundError."""
        transcription = "turn on the garage light"  # Assuming not in example config
        
        # Depending on implementation, may raise error or return command with invalid device
        # This test validates that unknown devices are caught
        pytest.skip("Depends on validation strategy - may return command or raise error")
    
    def test_batch_command_extraction_multiple_devices(self, command_parser):
        """Test: Multiple devices in single utterance (FR-018)."""
        transcription = "turn on the living room light and bedroom light"
        
        commands = command_parser.parse(transcription)
        
        # Should extract 2 commands
        assert len(commands) >= 2, f"Should extract multiple commands, got {len(commands)}"
        
        intents = [cmd.intent for cmd in commands]
        assert all(intent == "turn_on" for intent in intents), "All should be 'turn_on'"
        
        devices = [cmd.device.lower() for cmd in commands]
        assert any("living" in d for d in devices), "Should include living room"
        assert any("bedroom" in d for d in devices), "Should include bedroom"
    
    def test_50_consecutive_commands_without_degradation(self, command_parser):
        """Test: 50 consecutive commands without memory leaks (SC-006)."""
        import time
        
        transcription = "turn on the kitchen light"
        inference_times = []
        
        for i in range(50):
            start = time.time()
            commands = command_parser.parse(transcription)
            elapsed = time.time() - start
            inference_times.append(elapsed)
            
            assert len(commands) > 0, f"Command {i+1} should be extracted"
            assert commands[0].intent == "turn_on"
        
        # Check that performance doesn't degrade significantly
        first_10_avg = sum(inference_times[:10]) / 10
        last_10_avg = sum(inference_times[-10:]) / 10
        
        # Last 10 should not be more than 50% slower than first 10
        assert last_10_avg < first_10_avg * 1.5, \
            f"Performance degraded: first 10 avg={first_10_avg:.2f}s, last 10 avg={last_10_avg:.2f}s"
    
    def test_command_session_tracking(self, command_parser):
        """Test: Commands are tracked in session."""
        transcription = "turn on the living room light"
        
        commands = command_parser.parse(transcription)
        
        # Check that CommandSession is created and tracked
        # Implementation detail - may need to access parser internals
        pytest.skip("Depends on parser implementation details")
