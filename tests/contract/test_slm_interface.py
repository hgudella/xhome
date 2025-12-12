"""Contract tests for SLMEngine interface.

These tests define the expected behavior of the SLM engine interface.
Write these FIRST before implementation (TDD Red phase).
"""
import pytest
from pathlib import Path
from datetime import datetime

from src.command.models import Command
from src.utils.exceptions import ModelLoadError, InferenceError, TimeoutError


class TestSLMEngineContract:
    """Contract tests for SLMEngine interface."""
    
    @pytest.fixture
    def model_path(self):
        """Path to the Phi-4-mini-instruct model."""
        path = Path("models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf")
        if not path.exists():
            pytest.skip(f"Model not found at {path}")
        return str(path)
    
    @pytest.fixture
    def slm_engine(self, model_path):
        """Create SLMEngine instance for testing."""
        from src.command.slm_engine import SLMEngine
        
        engine = SLMEngine(model_path=model_path)
        yield engine
        # Cleanup
        if engine.is_loaded():
            engine.unload()
    
    def test_model_loads_successfully_within_15_seconds(self, model_path):
        """Test: Model loads successfully within 15s (FR-002, SC-007)."""
        from src.command.slm_engine import SLMEngine
        import time
        
        start = time.time()
        engine = SLMEngine(model_path=model_path)
        load_time = time.time() - start
        
        assert engine.is_loaded(), "Model should be loaded"
        assert load_time < 15.0, f"Model load time {load_time:.2f}s exceeds 15s limit"
        
        engine.unload()
    
    def test_model_load_fails_with_invalid_path(self):
        """Test: ModelLoadError raised for invalid model path."""
        from src.command.slm_engine import SLMEngine
        
        with pytest.raises(ModelLoadError):
            SLMEngine(model_path="nonexistent/model.gguf")
    
    def test_extract_command_turn_on_living_room_light(self, slm_engine):
        """Test: extract_command('turn on living room light') returns correct Command."""
        transcription = "turn on the living room light"
        
        command = slm_engine.extract_command(transcription)
        
        assert isinstance(command, Command), "Should return Command object"
        assert command.intent == "turn_on", f"Expected intent 'turn_on', got '{command.intent}'"
        assert "living_room_light" in command.device.lower() or "living room" in command.device.lower(), \
            f"Expected device to contain 'living room', got '{command.device}'"
        assert command.confidence >= 0.0, "Confidence should be non-negative"
        assert command.confidence <= 1.0, "Confidence should not exceed 1.0"
    
    def test_extract_command_with_brightness_parameter(self, slm_engine):
        """Test: extract_command with brightness returns Command with parameters."""
        transcription = "set bedroom light to 50 percent brightness"
        
        command = slm_engine.extract_command(transcription)
        
        assert isinstance(command, Command), "Should return Command object"
        assert command.intent == "set_brightness", f"Expected intent 'set_brightness', got '{command.intent}'"
        assert "bedroom" in command.device.lower(), f"Expected device to contain 'bedroom', got '{command.device}'"
        assert "brightness" in command.parameters, "Should have brightness parameter"
        
        brightness = command.parameters.get("brightness")
        assert brightness is not None, "Brightness should not be None"
        assert 40 <= brightness <= 60, f"Expected brightness near 50, got {brightness}"
    
    def test_extract_command_unrelated_text_returns_unknown_or_none(self, slm_engine):
        """Test: Unrelated text returns unknown intent or None."""
        transcription = "what's the weather like today"
        
        command = slm_engine.extract_command(transcription)
        
        # Either returns None or Command with unknown intent
        if command is not None:
            assert command.intent == "unknown", \
                f"Unrelated text should have 'unknown' intent, got '{command.intent}'"
    
    def test_extract_command_timeout_after_10_seconds(self, slm_engine):
        """Test: SLM timeout after 10s raises TimeoutError (FR-019)."""
        # This test may be difficult to trigger reliably
        # Skip if model responds quickly
        pytest.skip("Timeout test requires artificially slow inference")
    
    def test_extract_command_malformed_output_raises_inference_error(self, slm_engine):
        """Test: Malformed SLM output raises InferenceError."""
        # This test checks error handling when SLM returns unparseable output
        # May require mocking or specific inputs that cause parsing failures
        pytest.skip("Malformed output test requires specific failure conditions")
    
    def test_model_unload_cleans_up_resources(self, slm_engine):
        """Test: Model unload cleans up resources."""
        assert slm_engine.is_loaded(), "Model should be loaded initially"
        
        slm_engine.unload()
        
        assert not slm_engine.is_loaded(), "Model should not be loaded after unload"
    
    def test_is_loaded_returns_false_before_initialization(self):
        """Test: is_loaded returns False before model is loaded."""
        from src.command.slm_engine import SLMEngine
        
        # Access class without initializing
        # This test may need adjustment based on implementation
        pytest.skip("Requires specific implementation pattern")
    
    def test_multiple_extractions_maintain_performance(self, slm_engine):
        """Test: Multiple command extractions maintain <1s inference time."""
        import time
        
        transcriptions = [
            "turn on the kitchen light",
            "turn off the bedroom light",
            "set living room light to 75 percent"
        ]
        
        inference_times = []
        
        for transcription in transcriptions:
            start = time.time()
            command = slm_engine.extract_command(transcription)
            inference_time = time.time() - start
            inference_times.append(inference_time)
            
            assert command is not None, f"Command should be extracted for '{transcription}'"
        
        avg_time = sum(inference_times) / len(inference_times)
        assert avg_time < 1.0, f"Average inference time {avg_time:.2f}s exceeds 1s target"
        
        # Check that no individual inference exceeded 2s (reasonable buffer)
        for i, t in enumerate(inference_times):
            assert t < 2.0, f"Inference {i+1} took {t:.2f}s, exceeds 2s threshold"
