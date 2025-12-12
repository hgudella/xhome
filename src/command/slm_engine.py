"""SLM Engine for command extraction using llama-cpp-python.

This module provides the interface to the Phi-4-mini-instruct model
for extracting structured commands from natural language transcriptions.
"""
import json
import logging
import time
from pathlib import Path
from typing import Optional, Dict, Any
from threading import Thread, Event

from llama_cpp import Llama

from src.command.models import Command
from src.utils.exceptions import (
    ModelLoadError,
    InferenceError,
    TimeoutError as SLMTimeoutError,
    CommandParsingError
)

logger = logging.getLogger(__name__)


class SLMEngine:
    """Small Language Model engine for command extraction.
    
    Uses llama-cpp-python with Phi-4-mini-instruct-GGUF for local inference.
    Handles model loading, prompt engineering, and structured output parsing.
    """
    
    # Few-shot examples for prompt
    FEW_SHOT_EXAMPLES = """
Example 1:
Input: "turn on the living room light"
Output: {"intent": "turn_on", "device": "living_room_light", "confidence": 0.95}

Example 2:
Input: "set bedroom light to 50 percent brightness"
Output: {"intent": "set_brightness", "device": "bedroom_light", "parameters": {"brightness": 50}, "confidence": 0.9}

Example 3:
Input: "turn off the kitchen light"
Output: {"intent": "turn_off", "device": "kitchen_light", "confidence": 0.95}

Example 4:
Input: "set thermostat to 72 degrees"
Output: {"intent": "set_temperature", "device": "thermostat", "parameters": {"temperature": 72}, "confidence": 0.9}

Example 5:
Input: "what's the weather like"
Output: {"intent": "unknown", "device": null, "confidence": 0.1}
"""
    
    def __init__(
        self,
        model_path: str,
        context_length: int = 2048,
        n_gpu_layers: int = 0,
        timeout: int = 10
    ):
        """Initialize SLM engine and load model.
        
        Args:
            model_path: Path to the GGUF model file
            context_length: Context window size (default: 2048)
            n_gpu_layers: Number of layers to offload to GPU (default: 0 for CPU-only)
            timeout: Maximum inference time in seconds (default: 10)
            
        Raises:
            ModelLoadError: If model file not found or fails to load
        """
        self.model_path = Path(model_path)
        self.context_length = context_length
        self.n_gpu_layers = n_gpu_layers
        self.timeout = timeout
        self._model: Optional[Llama] = None
        
        # Validate model exists
        if not self.model_path.exists():
            raise ModelLoadError(
                f"Model file not found: {self.model_path}"
            )
        
        # Load model
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the GGUF model using llama-cpp-python.
        
        Raises:
            ModelLoadError: If model fails to load
        """
        start_time = time.time()
        
        try:
            logger.info(f"Loading model from {self.model_path}")
            
            self._model = Llama(
                model_path=str(self.model_path),
                n_ctx=self.context_length,
                n_gpu_layers=self.n_gpu_layers,
                n_batch=512,  # Batch size for prompt processing
                verbose=False  # Suppress llama.cpp output
            )
            
            load_time = time.time() - start_time
            logger.info(
                f"Model loaded successfully in {load_time:.2f}s "
                f"(context={self.context_length}, gpu_layers={self.n_gpu_layers})"
            )
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise ModelLoadError(f"Model load failed: {e}") from e
    
    def is_loaded(self) -> bool:
        """Check if model is loaded.
        
        Returns:
            True if model is loaded and ready for inference
        """
        return self._model is not None
    
    def unload(self) -> None:
        """Unload model and free resources."""
        if self._model is not None:
            logger.info("Unloading model")
            del self._model
            self._model = None
    
    def extract_command(self, transcription: str) -> Optional[Command]:
        """Extract structured command from transcription.
        
        Uses few-shot prompting to guide the model toward JSON output.
        Enforces timeout per FR-019.
        
        Args:
            transcription: Natural language transcription from voice input
            
        Returns:
            Command object if valid command extracted, None if unrelated text
            
        Raises:
            SLMTimeoutError: If inference exceeds timeout
            InferenceError: If model returns unparseable output
            CommandParsingError: If JSON parsing fails
        """
        if not self.is_loaded():
            raise InferenceError("Model not loaded")
        
        # Build prompt with few-shot examples
        prompt = self._build_prompt(transcription)
        
        # Run inference with timeout
        result_container = {}
        error_container = {}
        timeout_event = Event()
        
        def inference_thread():
            try:
                output = self._run_inference(prompt)
                result_container['output'] = output
            except Exception as e:
                error_container['error'] = e
            finally:
                timeout_event.set()
        
        thread = Thread(target=inference_thread, daemon=True)
        start_time = time.time()
        thread.start()
        
        # Wait for completion or timeout
        if not timeout_event.wait(timeout=self.timeout):
            inference_time = time.time() - start_time
            logger.error(
                f"Inference timeout after {inference_time:.2f}s "
                f"(limit: {self.timeout}s)"
            )
            raise SLMTimeoutError(
                f"Inference exceeded {self.timeout}s timeout"
            )
        
        # Check for errors
        if 'error' in error_container:
            raise InferenceError(
                f"Inference failed: {error_container['error']}"
            ) from error_container['error']
        
        # Parse output
        output = result_container.get('output', '')
        inference_time = time.time() - start_time
        
        try:
            command = self._parse_output(output, transcription)
            
            if command:
                logger.info(
                    f"Command extracted in {inference_time:.2f}s: "
                    f"intent={command.intent}, device={command.device}, "
                    f"confidence={command.confidence:.2f}"
                )
            else:
                logger.info(
                    f"No command extracted (unrelated text) in {inference_time:.2f}s"
                )
            
            return command
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON output: {e}")
            logger.debug(f"Raw output: {output}")
            raise CommandParsingError(
                f"Failed to parse model output as JSON: {e}"
            ) from e
    
    def _build_prompt(self, transcription: str) -> str:
        """Build few-shot prompt for the model.
        
        Args:
            transcription: User's transcription to parse
            
        Returns:
            Complete prompt string
        """
        # Simpler, more direct prompt for Phi-4 with unknown intent handling
        prompt = f"""Parse this smart home command into JSON. Include room name in device. If not a smart home command, return "unknown" intent.

Input: "turn on the living room light"
Output: {{"intent":"turn_on","device":"living_room_light","confidence":0.95}}

Input: "turn on the light in the bedroom"
Output: {{"intent":"turn_on","device":"bedroom_light","confidence":0.90}}

Input: "set bedroom light to 50 percent"  
Output: {{"intent":"set_brightness","device":"bedroom_light","parameters":{{"brightness":50}},"confidence":0.9}}

Input: "turn off the fan"
Output: {{"intent":"turn_off","device":"ceiling_fan","confidence":0.90}}

Input: "turn off kitchen light"
Output: {{"intent":"turn_off","device":"kitchen_light","confidence":0.95}}

Input: "hello"
Output: {{"intent":"unknown","device":null,"confidence":0.1}}

Input: "what's the weather"
Output: {{"intent":"unknown","device":null,"confidence":0.1}}

Input: "{transcription}"
Output:"""
        
        return prompt
    
    def _run_inference(self, prompt: str) -> str:
        """Run model inference.
        
        Args:
            prompt: Complete prompt string
            
        Returns:
            Model output string
            
        Raises:
            InferenceError: If inference fails
        """
        try:
            # Reset context to prevent memory issues
            self._model.reset()
            
            response = self._model(
                prompt,
                max_tokens=128,  # Reduced for faster responses
                temperature=0.1,  # Low temperature for deterministic output
                echo=False,
                stop=["\n", "Input:"]  # Stop at newline or next input
            )
            
            # Extract text from response
            output = response.get('choices', [{}])[0].get('text', '').strip()
            
            # Log if output is empty for debugging
            if not output:
                logger.warning(f"Empty output. Prompt length: {len(prompt)}, Response: {response}")
            
            return output
            
        except Exception as e:
            logger.error(f"Inference failed: {e}")
            raise InferenceError(f"Model inference failed: {e}") from e
    
    def _parse_output(
        self,
        output: str,
        transcription: str
    ) -> Optional[Command]:
        """Parse model output into Command object.
        
        Args:
            output: Raw model output string
            transcription: Original transcription (for privacy tracking)
            
        Returns:
            Command object or None if unknown intent
            
        Raises:
            CommandParsingError: If JSON parsing fails
        """
        # Handle empty output gracefully
        if not output or not output.strip():
            logger.warning("Model returned empty output")
            raise CommandParsingError("Model returned empty output")
        
        # Extract JSON from output (model may include extra text)
        json_start = output.find('{')
        
        if json_start == -1:
            # No JSON found, treat as unparseable
            logger.warning(f"No JSON found in output: {output[:100]}")
            raise CommandParsingError(
                f"No JSON object found in output: {output[:100]}"
            )
        
        # Find the matching closing brace for the first JSON object
        brace_count = 0
        json_end = json_start
        for i in range(json_start, len(output)):
            if output[i] == '{':
                brace_count += 1
            elif output[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    json_end = i + 1
                    break
        
        if brace_count != 0:
            # No matching closing brace found
            logger.warning(f"Unmatched braces in output: {output[:100]}")
            raise CommandParsingError(
                f"Unmatched braces in JSON output"
            )
        
        json_str = output[json_start:json_end]
        
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise CommandParsingError(
                f"Invalid JSON in output: {json_str}"
            ) from e
        
        # Validate required fields
        intent = data.get('intent')
        if not intent:
            raise CommandParsingError("Missing 'intent' field in output")
        
        # If intent is unknown, return None (unrelated text)
        if intent == 'unknown':
            return None
        
        # Extract fields
        device = data.get('device', '')
        parameters = data.get('parameters', {})
        confidence = data.get('confidence', 0.5)
        
        # Create Command object
        command = Command(
            intent=intent,
            device=device,
            parameters=parameters,
            confidence=confidence,
            raw_transcription=transcription
        )
        
        return command
