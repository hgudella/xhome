"""WhisperEngine for speech-to-text transcription using Hugging Face Transformers."""

import numpy as np
import librosa
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
from typing import Optional
from .transcriber import Transcription
from ..utils.exceptions import TranscriptionError
from ..utils.logging import get_logger


logger = get_logger(__name__)


class WhisperEngine:
    """
    Whisper-based speech-to-text transcription engine.
    
    Wraps Hugging Face Transformers Whisper model for audio transcription.
    Handles audio preprocessing, inference, and confidence calculation.
    """
    
    def __init__(
        self,
        model_name: str = "openai/whisper-tiny",
        device: str = "cpu"
    ):
        """
        Initialize WhisperEngine with model loading.
        
        Args:
            model_name: Hugging Face model identifier
            device: Device for inference ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.device = device
        
        logger.info(
            "Loading Whisper model",
            model_name=model_name,
            device=device
        )
        
        try:
            # Load model
            self.model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_name,
                torch_dtype=torch.float16 if device == "cuda" else torch.float32,
                low_cpu_mem_usage=True,
                use_safetensors=True
            )
            self.model.to(device)
            
            # Load processor (tokenizer + feature extractor)
            self.processor = AutoProcessor.from_pretrained(model_name)
            
            logger.info(
                "Whisper model loaded successfully",
                model_name=model_name,
                device=device
            )
            
        except Exception as e:
            logger.error(
                "Failed to load Whisper model",
                model_name=model_name,
                error=str(e)
            )
            raise TranscriptionError(f"Failed to load Whisper model: {e}")
    
    def transcribe(
        self,
        audio_data: np.ndarray,
        sample_rate: int
    ) -> Transcription:
        """
        Transcribe audio to text.
        
        Args:
            audio_data: Audio samples as int16 numpy array
            sample_rate: Sample rate of audio
            
        Returns:
            Transcription object with text and metadata
            
        Raises:
            TranscriptionError: If transcription fails
        """
        # Validate inputs
        if audio_data.size == 0:
            raise TranscriptionError("Cannot transcribe empty audio")
        
        if sample_rate <= 0:
            raise TranscriptionError(f"Invalid sample_rate: {sample_rate}")
        
        logger.info(
            "Starting transcription",
            audio_frames=audio_data.shape[0],
            sample_rate=sample_rate,
            duration_seconds=audio_data.shape[0] / sample_rate
        )
        
        try:
            # Preprocess audio
            audio_float = self._normalize_audio(audio_data)
            
            # Resample to 16kHz if needed (Whisper requirement)
            if sample_rate != 16000:
                audio_float = self._resample_audio(audio_float, sample_rate)
            
            # Resample to 16kHz if needed (Whisper requirement)
            if sample_rate != 16000:
                audio_float = self._resample_audio(audio_float, sample_rate)
            
            # Apply automatic gain control (AGC) to boost quiet audio BEFORE padding
            # This helps with quiet microphones or remote audio compression
            audio_level = np.abs(audio_float).mean()
            if audio_level > 0 and audio_level < 0.05:  # Very quiet audio
                # Amplify to target level of ~0.1
                gain = 0.1 / audio_level
                # Cap gain to prevent distortion
                gain = min(gain, 10.0)
                audio_float = audio_float * gain
                logger.debug(f"Applied AGC: level {audio_level:.4f} -> {np.abs(audio_float).mean():.4f} (gain: {gain:.2f}x)")
            
            # Pad short audio to minimum 1 second for better Whisper performance
            # Whisper performs poorly on very short clips (< 0.5s)
            min_samples = 16000  # 1 second at 16kHz
            if len(audio_float) < min_samples:
                padding = min_samples - len(audio_float)
                audio_float = np.pad(audio_float, (0, padding), mode='constant', constant_values=0)
                logger.debug(f"Padded audio from {len(audio_data)} to {len(audio_float)} samples")
            
            # Extract features
            inputs = self.processor(
                audio_float,
                sampling_rate=16000,
                return_tensors="pt"
            )
            inputs = inputs.to(self.device)
            
            # Generate transcription with scores
            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_features"],
                    max_new_tokens=128,
                    language="en",
                    task="transcribe",
                    return_dict_in_generate=True,
                    output_scores=True
                )
                generated_ids = outputs.sequences
            
            # Decode text
            transcription_text = self.processor.batch_decode(
                generated_ids,
                skip_special_tokens=True
            )[0]
            
            # Calculate confidence from output scores
            # Average the softmax probabilities of the predicted tokens
            print(f"🔍 DEBUG: Has scores attr? {hasattr(outputs, 'scores')}")
            if hasattr(outputs, 'scores'):
                print(f"🔍 DEBUG: Scores length: {len(outputs.scores)}")
            
            if hasattr(outputs, 'scores') and len(outputs.scores) > 0:
                # outputs.scores is a tuple of tensors, one per generated token
                # Each tensor has shape (batch_size, vocab_size)
                token_probs = []
                for score in outputs.scores:
                    # Get softmax probabilities
                    probs = torch.softmax(score, dim=-1)
                    # Get max probability (the selected token's probability)
                    max_prob = probs.max().item()
                    token_probs.append(max_prob)
                
                # Average confidence across all tokens
                confidence = float(np.mean(token_probs)) if token_probs else 0.85
                print(f"🔍 DEBUG: Calculated confidence: {confidence:.4f}")
            else:
                # Fallback if scores not available
                confidence = 0.85
                print(f"🔍 DEBUG: Using fallback confidence: {confidence}")
            
            # Detect language (from model output or default to English)
            language = "en"  # Whisper can detect language, but simplified here
            
            # Calculate audio duration
            audio_duration = audio_data.shape[0] / sample_rate
            
            logger.info(
                "Transcription completed",
                text_length=len(transcription_text),
                confidence=confidence,
                language=language,
                audio_duration_seconds=audio_duration
            )
            
            # Create Transcription object
            transcription = Transcription(
                text=transcription_text,
                confidence=confidence,
                audio_duration_seconds=audio_duration,
                language=language,
                model_name=self.model_name
            )
            
            return transcription
            
        except Exception as e:
            logger.error(
                "Transcription failed",
                error=str(e)
            )
            raise TranscriptionError(f"Transcription failed: {e}")
    
    def _normalize_audio(self, audio_int16: np.ndarray) -> np.ndarray:
        """
        Normalize audio to float32 in range [-1.0, 1.0].
        
        Args:
            audio_int16: Audio samples (int16 or float32)
            
        Returns:
            Normalized audio as float32
        """
        # Check if already float32
        if audio_int16.dtype == np.float32 or audio_int16.dtype == np.float64:
            # Already normalized
            return audio_int16.astype(np.float32)
        
        # Convert int16 to float32
        audio_float = audio_int16.astype(np.float32) / 32768.0
        return audio_float
    
    def _resample_audio(
        self,
        audio: np.ndarray,
        source_sr: int,
        target_sr: int = 16000
    ) -> np.ndarray:
        """
        Resample audio to target sample rate.
        
        Args:
            audio: Audio samples as float32
            source_sr: Source sample rate
            target_sr: Target sample rate (default 16kHz for Whisper)
            
        Returns:
            Resampled audio
        """
        if source_sr == target_sr:
            return audio
        
        logger.debug(
            "Resampling audio",
            source_sr=source_sr,
            target_sr=target_sr
        )
        
        resampled = librosa.resample(
            audio,
            orig_sr=source_sr,
            target_sr=target_sr
        )
        
        return resampled
    
    def _calculate_confidence(self, logits: np.ndarray) -> float:
        """
        Calculate confidence score from model logits.
        
        Args:
            logits: Model output logits
            
        Returns:
            Confidence score in range [0.0, 1.0]
        """
        # Simplified confidence calculation
        # For production, use proper softmax and probability aggregation
        softmax = np.exp(logits) / np.sum(np.exp(logits), axis=-1, keepdims=True)
        max_probs = np.max(softmax, axis=-1)
        confidence = float(np.mean(max_probs))
        
        return np.clip(confidence, 0.0, 1.0)
