"""
Contract tests for Voice Activity Detection (VAD) interface.

These tests define the expected interface and behavior of the VAD detector.
"""

import numpy as np
import pytest


class TestVADContract:
    """Contract tests for VAD detector interface."""
    
    def test_vad_initialization(self):
        """VAD detector can be initialized with default settings."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        assert vad is not None
        assert hasattr(vad, 'sample_rate')
        assert vad.sample_rate > 0
        assert hasattr(vad, 'is_loaded')
        assert vad.is_loaded is True
    
    def test_vad_detect_speech_interface(self):
        """VAD detector provides is_speech() method returning boolean."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Create dummy audio (1 second at 16kHz)
        audio = np.random.randn(16000).astype(np.float32)
        
        # Should return boolean
        result = vad.is_speech(audio)
        assert isinstance(result, (bool, np.bool_))
    
    def test_vad_detect_speech_confidence(self):
        """VAD detector provides get_speech_confidence() returning float 0-1."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Create dummy audio
        audio = np.random.randn(16000).astype(np.float32)
        
        # Should return confidence in range [0, 1]
        confidence = vad.get_speech_confidence(audio)
        assert isinstance(confidence, (float, np.floating))
        assert 0.0 <= confidence <= 1.0
    
    def test_vad_reset_state(self):
        """VAD detector provides reset() method to clear internal state."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Process some audio
        audio = np.random.randn(16000).astype(np.float32)
        vad.is_speech(audio)
        
        # Should have reset method
        vad.reset()
        
        # Should still work after reset
        result = vad.is_speech(audio)
        assert isinstance(result, (bool, np.bool_))
    
    def test_vad_handles_different_audio_lengths(self):
        """VAD detector handles audio chunks of varying lengths."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Test different lengths
        for duration_seconds in [0.5, 1.0, 2.0, 3.0]:
            frames = int(vad.sample_rate * duration_seconds)
            audio = np.random.randn(frames).astype(np.float32)
            
            result = vad.is_speech(audio)
            assert isinstance(result, (bool, np.bool_))
    
    def test_vad_silence_detection(self):
        """VAD detector correctly identifies silence (all zeros)."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Create silence (all zeros)
        silence = np.zeros(16000, dtype=np.float32)
        
        # Silence should not be detected as speech
        result = vad.is_speech(silence)
        confidence = vad.get_speech_confidence(silence)
        
        # Either result is False or confidence is very low
        assert result is False or confidence < 0.3
