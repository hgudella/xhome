"""Command parser for integrating SLM with device configuration.

This module provides a high-level interface that combines the SLM engine
with device configuration for complete command parsing and validation.
"""
import logging
from pathlib import Path
from typing import List, Optional

from src.command.slm_engine import SLMEngine
from src.command.models import Command
from src.command.session import CommandSession
from src.devices.config import DeviceConfig
from src.utils.exceptions import DeviceNotFoundError, CommandParsingError

logger = logging.getLogger(__name__)


class CommandParser:
    """High-level command parser integrating SLM and device config.
    
    Orchestrates the flow from transcription to validated Command objects.
    Handles device name resolution, alias matching, and session tracking.
    """
    
    def __init__(
        self,
        model_path: str,
        device_config_path: str,
        context_length: int = 2048,
        n_gpu_layers: int = 0,
        timeout: int = 30
    ):
        """Initialize command parser.
        
        Args:
            model_path: Path to GGUF model file
            device_config_path: Path to devices.yaml configuration
            context_length: SLM context window size (default: 2048)
            n_gpu_layers: GPU layers for acceleration (default: 0)
            timeout: Maximum inference time in seconds (default: 30)
        """
        self.slm_engine = SLMEngine(
            model_path=model_path,
            context_length=context_length,
            n_gpu_layers=n_gpu_layers,
            timeout=timeout
        )
        
        self.device_config = DeviceConfig(device_config_path)
        
        logger.info(
            f"CommandParser initialized with {len(self.device_config.devices)} devices"
        )
    
    def parse(
        self,
        transcription: str,
        validate_devices: bool = True,
        session: Optional[CommandSession] = None
    ) -> List[Command]:
        """Parse transcription into validated Command objects.
        
        Args:
            transcription: Natural language transcription from voice input
            validate_devices: Whether to validate device names against config (default: True)
            session: Optional CommandSession for tracking (default: None)
            
        Returns:
            List of Command objects (may be empty for unrelated text)
            
        Raises:
            DeviceNotFoundError: If validate_devices=True and device not found
            CommandParsingError: If SLM returns unparseable output
        """
        try:
            # Extract command using SLM
            command = self.slm_engine.extract_command(transcription)
            
            # If no command extracted (unrelated text), return empty list
            if command is None:
                logger.info(f"No command extracted from: {transcription[:50]}")
                return []
            
            # Validate and resolve device names
            if validate_devices and command.device:
                command = self._resolve_device_name(command)
            
            # Add to session if provided
            if session:
                session.commands.append(command)
            
            logger.info(
                f"Parsed command: intent={command.intent}, "
                f"device={command.device}, confidence={command.confidence:.2f}"
            )
            
            return [command]
            
        except Exception as e:
            logger.error(f"Failed to parse transcription: {e}")
            
            # Add error to session if provided
            if session:
                session.errors.append(str(e))
            
            raise
    
    def _resolve_device_name(self, command: Command) -> Command:
        """Resolve device name using aliases and validate against config.
        
        Args:
            command: Command object with potentially ambiguous device name
            
        Returns:
            Command object with canonical device name
            
        Raises:
            DeviceNotFoundError: If device not found in configuration
        """
        device_mapping = self.device_config.find_device(command.device)
        
        if device_mapping is None:
            logger.warning(f"Device not found: {command.device}")
            raise DeviceNotFoundError(
                f"Device '{command.device}' not found in configuration"
            )
        
        # Update command with canonical device name if different
        if command.device != device_mapping.name:
            logger.debug(
                f"Resolved device '{command.device}' to '{device_mapping.name}'"
            )
            # Create new Command with canonical name
            command = Command(
                intent=command.intent,
                device=device_mapping.name,
                parameters=command.parameters,
                confidence=command.confidence,
                raw_transcription=command.raw_transcription
            )
        
        return command
    
    def cleanup(self) -> None:
        """Clean up resources (unload model)."""
        logger.info("Cleaning up CommandParser")
        self.slm_engine.unload()
