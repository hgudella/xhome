"""
Unit tests for Voice Activity Detection (VAD) implementation.
"""

import numpy as np
import pytest
from unittest.mock import Mock, patch, MagicMock


class TestVoiceActivityDetector:
    """Unit tests for VoiceActivityDetector."""
    
    def test_initialization_default(self):
        """Initialize VAD with default settings."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        assert vad.sample_rate == 16000
        assert vad.threshold == 0.5
        assert vad.is_loaded is True
    
    def test_initialization_custom_threshold(self):
        """Initialize VAD with custom threshold."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector(threshold=0.7)
        
        assert vad.threshold == 0.7
    
    def test_initialization_invalid_threshold(self):
        """VAD initialization raises error for invalid threshold."""
        from src.audio.vad import VoiceActivityDetector
        from src.utils.exceptions import ValidationError
        
        with pytest.raises(ValidationError, match="threshold must be between 0.0 and 1.0"):
            VoiceActivityDetector(threshold=1.5)
        
        with pytest.raises(ValidationError, match="threshold must be between 0.0 and 1.0"):
            VoiceActivityDetector(threshold=-0.1)
    
    @patch('src.audio.vad.torch.hub.load')
    def test_model_loading(self, mock_hub_load):
        """VAD loads Silero VAD model from torch hub."""
        from src.audio.vad import VoiceActivityDetector
        
        # Mock the model
        mock_model = MagicMock()
        mock_hub_load.return_value = (mock_model, None)
        
        vad = VoiceActivityDetector()
        
        # Should load from torch.hub
        mock_hub_load.assert_called_once_with(
            repo_or_dir='snakers4/silero-vad',
            model='silero_vad',
            force_reload=False,
            onnx=False
        )
    
    def test_audio_normalization(self):
        """VAD normalizes audio to float32 in range [-1, 1]."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Create int16 audio
        audio_int16 = np.array([0, 16384, 32767, -16384, -32768], dtype=np.int16)
        
        normalized = vad._normalize_audio(audio_int16)
        
        assert normalized.dtype == np.float32
        assert np.max(normalized) <= 1.0
        assert np.min(normalized) >= -1.0
        # Check specific values (int16 32767 -> float 1.0)
        assert np.isclose(normalized[2], 1.0, atol=0.01)
    
    def test_audio_resampling(self):
        """VAD resamples audio to target sample rate if needed."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()  # expects 16kHz
        
        # Create 48kHz audio (3x the target rate)
        audio_48k = np.random.randn(48000).astype(np.float32)
        
        resampled = vad._resample_if_needed(audio_48k, source_rate=48000)
        
        # Should be downsampled to ~16000 frames
        assert len(resampled) == 16000
    
    def test_audio_resampling_not_needed(self):
        """VAD skips resampling if already at target rate."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Already 16kHz
        audio_16k = np.random.randn(16000).astype(np.float32)
        
        result = vad._resample_if_needed(audio_16k, source_rate=16000)
        
        # Should return same array (no resampling)
        assert result is audio_16k
    
    @patch('src.audio.vad.VoiceActivityDetector._call_model')
    def test_get_speech_confidence(self, mock_call_model):
        """VAD returns speech confidence from model."""
        from src.audio.vad import VoiceActivityDetector
        
        mock_call_model.return_value = 0.85
        
        vad = VoiceActivityDetector()
        audio = np.random.randn(16000).astype(np.float32)
        
        confidence = vad.get_speech_confidence(audio)
        
        assert confidence == 0.85
        mock_call_model.assert_called_once()
    
    @patch('src.audio.vad.VoiceActivityDetector._call_model')
    def test_is_speech_above_threshold(self, mock_call_model):
        """VAD returns True when confidence above threshold."""
        from src.audio.vad import VoiceActivityDetector
        
        mock_call_model.return_value = 0.75
        
        vad = VoiceActivityDetector(threshold=0.5)
        audio = np.random.randn(16000).astype(np.float32)
        
        result = vad.is_speech(audio)
        
        assert result is True
    
    @patch('src.audio.vad.VoiceActivityDetector._call_model')
    def test_is_speech_below_threshold(self, mock_call_model):
        """VAD returns False when confidence below threshold."""
        from src.audio.vad import VoiceActivityDetector
        
        mock_call_model.return_value = 0.25
        
        vad = VoiceActivityDetector(threshold=0.5)
        audio = np.random.randn(16000).astype(np.float32)
        
        result = vad.is_speech(audio)
        
        assert result is False
    
    def test_reset_clears_state(self):
        """VAD reset clears internal model state."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Process some audio first
        audio = np.random.randn(16000).astype(np.float32)
        vad.is_speech(audio)
        
        # Reset should work without error
        vad.reset()
        
        # Should still work after reset
        result = vad.is_speech(audio)
        assert isinstance(result, (bool, np.bool_))
    
    def test_empty_audio_handling(self):
        """VAD handles empty audio gracefully."""
        from src.audio.vad import VoiceActivityDetector
        from src.utils.exceptions import ValidationError
        
        vad = VoiceActivityDetector()
        empty_audio = np.array([], dtype=np.float32)
        
        with pytest.raises(ValidationError, match="Audio data cannot be empty"):
            vad.is_speech(empty_audio)
    
    def test_logging_on_initialization(self):
        """VAD logs initialization without sensitive data."""
        from src.audio.vad import VoiceActivityDetector
        import logging
        import io
        
        # Capture logs
        log_stream = io.StringIO()
        handler = logging.StreamHandler(log_stream)
        handler.setLevel(logging.INFO)
        logger = logging.getLogger('src.audio.vad')
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        
        vad = VoiceActivityDetector(threshold=0.6)
        
        log_output = log_stream.getvalue()
        
        # Should log initialization
        assert "VoiceActivityDetector initialized" in log_output or "Loading VAD model" in log_output
        
        # Cleanup
        logger.removeHandler(handler)
