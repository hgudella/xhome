"""
Voice Activity Detection (VAD) using Silero VAD model.

Detects speech vs silence in audio streams for continuous listening mode.
"""

import numpy as np
import torch
import librosa
from typing import Optional

from src.utils.logging import get_logger
from src.utils.exceptions import ValidationError, AudioCaptureError


logger = get_logger(__name__)


class VoiceActivityDetector:
    """
    Voice Activity Detector using Silero VAD model.
    
    Detects presence of speech in audio chunks for continuous listening mode.
    Uses pre-trained Silero VAD model from PyTorch Hub.
    
    Attributes:
        sample_rate: Expected sample rate (16kHz for Silero VAD)
        threshold: Confidence threshold for speech detection (0.0-1.0)
        model: Loaded Silero VAD model
        is_loaded: Whether model loaded successfully
    """
    
    def __init__(self, threshold: float = 0.5):
        """
        Initialize Voice Activity Detector.
        
        Args:
            threshold: Confidence threshold for speech detection (0.0-1.0)
                      Values > threshold are considered speech
                      
        Raises:
            ValidationError: If threshold out of range
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValidationError("threshold must be between 0.0 and 1.0")
        
        self.sample_rate = 16000  # Silero VAD expects 16kHz
        self.threshold = threshold
        self.is_loaded = False
        
        logger.info(
            "Initializing VoiceActivityDetector",
            sample_rate=self.sample_rate,
            threshold=self.threshold
        )
        
        try:
            # Load Silero VAD model from PyTorch Hub
            logger.info("Loading VAD model from torch.hub")
            self.model, _ = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            
            self.model.eval()  # Set to evaluation mode
            self.is_loaded = True
            
            logger.info("VoiceActivityDetector initialized successfully")
            
        except Exception as e:
            logger.error("Failed to load VAD model", error=str(e))
            raise AudioCaptureError(f"Failed to load VAD model: {e}")
    
    def is_speech(self, audio_data: np.ndarray, sample_rate: int = 16000) -> bool:
        """
        Detect if audio contains speech.
        
        Args:
            audio_data: Audio data as numpy array (float32, range [-1, 1])
            sample_rate: Sample rate of audio (will resample if needed)
            
        Returns:
            True if speech detected, False otherwise
            
        Raises:
            ValidationError: If audio_data is empty
        """
        if len(audio_data) == 0:
            raise ValidationError("Audio data cannot be empty")
        
        confidence = self.get_speech_confidence(audio_data, sample_rate)
        return confidence > self.threshold
    
    def get_speech_confidence(
        self,
        audio_data: np.ndarray,
        sample_rate: int = 16000
    ) -> float:
        """
        Get speech confidence score for audio.
        
        Args:
            audio_data: Audio data as numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            Confidence score in range [0.0, 1.0]
            Higher values indicate more likely speech
            
        Raises:
            ValidationError: If audio_data is empty
        """
        if len(audio_data) == 0:
            raise ValidationError("Audio data cannot be empty")
        
        # Normalize audio to float32 [-1, 1]
        audio_normalized = self._normalize_audio(audio_data)
        
        # Resample if needed
        audio_resampled = self._resample_if_needed(audio_normalized, sample_rate)
        
        # Get confidence from model
        confidence = self._call_model(audio_resampled)
        
        return float(confidence)
    
    def reset(self):
        """
        Reset VAD internal state.
        
        Clears any cached state from previous audio chunks.
        Useful when starting a new listening session.
        """
        try:
            if hasattr(self.model, 'reset_states'):
                self.model.reset_states()
            logger.debug("VAD state reset")
        except Exception as e:
            logger.warning("Failed to reset VAD state", error=str(e))
    
    def _normalize_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """
        Normalize audio to float32 in range [-1, 1].
        
        Args:
            audio_data: Audio data (any dtype)
            
        Returns:
            Normalized audio as float32
        """
        if audio_data.dtype == np.int16:
            # Convert int16 to float32 in range [-1, 1]
            return audio_data.astype(np.float32) / 32768.0
        elif audio_data.dtype == np.int32:
            return audio_data.astype(np.float32) / 2147483648.0
        else:
            # Already float, ensure float32
            return audio_data.astype(np.float32)
    
    def _resample_if_needed(
        self,
        audio_data: np.ndarray,
        source_rate: int
    ) -> np.ndarray:
        """
        Resample audio to target sample rate if needed.
        
        Args:
            audio_data: Audio data as float32
            source_rate: Current sample rate
            
        Returns:
            Resampled audio at target sample rate
        """
        if source_rate == self.sample_rate:
            return audio_data
        
        # Resample using librosa
        resampled = librosa.resample(
            audio_data,
            orig_sr=source_rate,
            target_sr=self.sample_rate
        )
        
        return resampled
    
    def _call_model(self, audio_data: np.ndarray) -> float:
        """
        Call Silero VAD model to get speech confidence.
        
        Silero VAD requires specific chunk sizes:
        - 512 samples for 16kHz
        - 256 samples for 8kHz
        
        Args:
            audio_data: Audio data as float32, at target sample rate
            
        Returns:
            Speech confidence in range [0.0, 1.0]
        """
        try:
            # Silero VAD expects 512 samples for 16kHz
            required_samples = 512 if self.sample_rate == 16000 else 256
            
            # Pad or trim to required size
            if len(audio_data) < required_samples:
                # Pad with zeros
                audio_data = np.pad(audio_data, (0, required_samples - len(audio_data)))
            elif len(audio_data) > required_samples:
                # Take first N samples (or could average multiple chunks)
                audio_data = audio_data[:required_samples]
            
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio_data)
            
            # Call model
            with torch.no_grad():
                confidence = self.model(audio_tensor, self.sample_rate)
            
            # Extract scalar value
            if isinstance(confidence, torch.Tensor):
                confidence = confidence.item()
            
            return float(confidence)
            
        except Exception as e:
            logger.warning("VAD model call failed", error=str(e))
            # Return low confidence on error (assume silence)
            return 0.0
