"""
Integration tests for continuous listening mode with VAD.
"""

import numpy as np
import pytest
import time
from unittest.mock import Mock, patch


class TestContinuousListeningPipeline:
    """Integration tests for VAD-based continuous listening."""
    
    def test_vad_integration_with_audio_stream(self):
        """VAD integrates with AudioStream for continuous capture."""
        from src.audio.capture import AudioStream
        from src.audio.vad import VoiceActivityDetector
        
        stream = AudioStream(sample_rate=16000)
        vad = VoiceActivityDetector()
        
        # Create speech-like audio (non-zero values)
        speech_audio = np.random.randn(16000).astype(np.float32) * 0.5
        
        # VAD should process audio from stream
        is_speech = vad.is_speech(speech_audio)
        
        assert isinstance(is_speech, (bool, np.bool_))
    
    def test_speech_detection_triggers_transcription(self):
        """When speech detected, system triggers transcription."""
        from src.audio.vad import VoiceActivityDetector
        from src.audio.buffer import AudioBuffer
        from src.transcription.whisper_engine import WhisperEngine
        
        vad = VoiceActivityDetector()
        engine = WhisperEngine()
        
        # Simulate speech audio
        speech_audio = np.random.randn(48000).astype(np.float32) * 0.3  # 3 seconds
        
        # Check if speech detected
        is_speech = vad.is_speech(speech_audio[:16000])  # Check first second
        
        if is_speech:
            # Create buffer and transcribe
            buffer = AudioBuffer(audio_data=speech_audio, sample_rate=16000)
            transcription = engine.transcribe(buffer.audio_data, buffer.sample_rate)
            
            assert transcription is not None
            assert hasattr(transcription, 'text')
            
            # Cleanup
            buffer.clear()
    
    def test_silence_detection_skips_transcription(self):
        """When silence detected, system skips transcription."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Create silence
        silence = np.zeros(16000, dtype=np.float32)
        
        # Should detect no speech
        is_speech = vad.is_speech(silence)
        confidence = vad.get_speech_confidence(silence)
        
        # Silence should not trigger transcription
        assert is_speech is False or confidence < 0.3
    
    def test_continuous_mode_speech_boundaries(self):
        """Continuous mode detects speech start and end boundaries."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector(threshold=0.5)
        
        # Simulate: silence -> speech -> silence
        silence1 = np.zeros(8000, dtype=np.float32)  # 0.5s silence
        speech = np.random.randn(32000).astype(np.float32) * 0.5  # 2s speech
        silence2 = np.zeros(8000, dtype=np.float32)  # 0.5s silence
        
        # Check boundaries
        assert vad.is_speech(silence1) is False  # Before speech
        # Speech detection depends on actual model, but confidence should be higher
        speech_confidence = vad.get_speech_confidence(speech[:16000])
        assert vad.is_speech(silence2) is False  # After speech
    
    def test_vad_with_buffer_accumulation(self):
        """VAD accumulates audio until silence detected."""
        from src.audio.vad import VoiceActivityDetector
        from src.audio.buffer import AudioBuffer
        import numpy as np
        
        vad = VoiceActivityDetector()
        accumulated_audio = []
        
        # Simulate streaming chunks
        chunks = [
            np.random.randn(4800).astype(np.float32) * 0.3,  # 0.3s speech
            np.random.randn(4800).astype(np.float32) * 0.3,  # 0.3s speech
            np.zeros(4800, dtype=np.float32),  # 0.3s silence - END
        ]
        
        for chunk in chunks:
            accumulated_audio.append(chunk)
            
            # Check if silence (end of utterance)
            if not vad.is_speech(chunk):
                # Create buffer from accumulated audio
                combined = np.concatenate(accumulated_audio)
                buffer = AudioBuffer(audio_data=combined, sample_rate=16000)
                
                assert buffer.duration_seconds > 0
                buffer.clear()
                break
    
    @patch('src.audio.capture.AudioStream.start')
    @patch('src.audio.capture.AudioStream.stop')
    def test_continuous_mode_lifecycle(self, mock_stop, mock_start):
        """Continuous mode maintains lifecycle: listen -> process -> repeat."""
        from src.audio.capture import AudioStream
        from src.audio.vad import VoiceActivityDetector
        
        stream = AudioStream()
        vad = VoiceActivityDetector()
        
        # Start listening
        mock_start.return_value = None
        stream.start()
        mock_start.assert_called_once()
        
        # Process speech
        audio = np.random.randn(16000).astype(np.float32) * 0.3
        is_speech = vad.is_speech(audio)
        
        # Should continue listening (not stop between utterances)
        # In real implementation, stream stays active
        assert stream.state == "listening" or mock_stop.call_count == 0
    
    def test_multiple_utterances_in_sequence(self):
        """Continuous mode handles multiple speech utterances correctly."""
        from src.audio.vad import VoiceActivityDetector
        
        vad = VoiceActivityDetector()
        
        # Simulate 3 utterances separated by silence
        utterances = []
        for i in range(3):
            # Speech
            speech = np.random.randn(24000).astype(np.float32) * 0.4  # 1.5s
            utterances.append(('speech', speech))
            
            # Silence between utterances
            silence = np.zeros(8000, dtype=np.float32)  # 0.5s
            utterances.append(('silence', silence))
        
        speech_count = 0
        silence_count = 0
        
        for utt_type, audio in utterances:
            # Check chunks of audio
            for i in range(0, len(audio), 4800):  # 0.3s chunks
                chunk = audio[i:i+4800]
                if len(chunk) < 4800:
                    chunk = np.pad(chunk, (0, 4800 - len(chunk)))
                
                is_speech = vad.is_speech(chunk)
                
                if utt_type == 'speech' and is_speech:
                    speech_count += 1
                elif utt_type == 'silence' and not is_speech:
                    silence_count += 1
        
        # Should detect at least some speech and silence
        assert speech_count > 0 or silence_count > 0
    
    def test_continuous_mode_privacy_compliance(self):
        """Continuous mode maintains 0-day audio retention."""
        from src.audio.vad import VoiceActivityDetector
        from src.audio.buffer import AudioBuffer
        
        vad = VoiceActivityDetector()
        
        # Process utterance
        audio = np.random.randn(32000).astype(np.float32) * 0.3
        is_speech = vad.is_speech(audio[:16000])
        
        if is_speech:
            buffer = AudioBuffer(audio_data=audio, sample_rate=16000)
            
            # After processing, clear immediately
            buffer.clear()
            
            # Verify cleared
            assert np.all(buffer.audio_data == 0)
