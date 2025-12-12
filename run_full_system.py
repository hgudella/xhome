"""Full end-to-end voice-controlled smart home system.

Integrates:
- Feature 001: Voice capture and transcription
- Feature 002: SLM command understanding and MQTT publishing
"""
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.audio.continuous import ContinuousListener
from src.transcription.whisper_engine import WhisperEngine
from src.transcription.transcriber import Transcription
from src.command.router import CommandRouter
from src.devices.mqtt_config import MQTTConfig

def print_separator():
    print("\n" + "="*80 + "\n")

def print_banner():
    print_separator()
    print("🏠 XHOME - Voice-Controlled Smart Home System")
    print("Full End-to-End Pipeline: Voice → Text → Command → MQTT")
    print_separator()

def main():
    """Run the full voice-controlled smart home system."""
    
    print_banner()
    
    # Configuration
    print("📋 Configuration:")
    print("   - Audio: 16kHz, mono, Silero VAD")
    print("   - Transcription: Whisper (base model)")
    print("   - SLM: Phi-4-mini-instruct-Q4_K_M")
    print("   - Devices: config/devices.yaml.example")
    print("   - MQTT: localhost:1883")
    print_separator()
    
    # Initialize components
    print("🔧 Initializing components...")
    
    try:
        # Initialize Whisper engine (Feature 001)
        print("   Loading Whisper model...")
        whisper_engine = WhisperEngine(model_name="openai/whisper-base", device="cpu")
        print("   ✓ Whisper model loaded")
        
        # Initialize command router (Feature 002)
        print("   Loading SLM model...")
        mqtt_config = MQTTConfig(
            host="localhost",
            port=1883
        )
        
        router = CommandRouter(
            model_path="models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf",
            device_config_path="config/devices.yaml.example",
            mqtt_config=mqtt_config
        )
        print("   ✓ SLM model loaded")
        
        # Connect to MQTT broker
        print("   Connecting to MQTT broker...")
        router.connect_mqtt()
        print("   ✓ MQTT broker connected")
        
        print_separator()
        print("✅ System Ready!")
        print("\n🎤 Listening for voice commands...")
        print("   Available devices:")
        for device_name in router.device_config.devices.keys():
            print(f"      - {device_name}")
        print("\n   Example commands:")
        print("      - 'Turn on the living room light'")
        print("      - 'Set bedroom light to 75 percent'")
        print("      - 'Turn off the kitchen light'")
        print("      - 'Set thermostat to 72 degrees'")
        print("\n   Press Ctrl+C to stop")
        print_separator()
        
        # Callback for processing transcriptions
        def on_transcription(transcription: Transcription):
            """Process transcription through command router."""
            text = transcription.text
            print(f"\n🗣️  Heard: \"{text}\"")
            
            try:
                # Process through SLM and publish to MQTT
                session = router.process_transcription(text)
                
                # Display results
                if session.commands:
                    for cmd in session.commands:
                        # Check if command was successfully published
                        if session.mqtt_messages:
                            # Generate friendly confirmation message
                            device_friendly = cmd.device.replace('_', ' ').title()
                            
                            if cmd.intent == "turn_on":
                                print(f"   ✅ {device_friendly} is now turned on!")
                            elif cmd.intent == "turn_off":
                                print(f"   ✅ {device_friendly} is now turned off!")
                            elif cmd.intent == "set_brightness":
                                brightness = cmd.parameters.get('brightness', '?')
                                print(f"   ✅ {device_friendly} brightness set to {brightness}%!")
                            elif cmd.intent == "set_temperature":
                                temp = cmd.parameters.get('temperature', '?')
                                print(f"   ✅ {device_friendly} temperature set to {temp}°!")
                            else:
                                print(f"   ✅ Command executed successfully!")
                            
                            print(f"   📡 Published to: {session.mqtt_messages[0]['topic']}")
                        else:
                            # Command extracted but not published
                            device_friendly = cmd.device.replace('_', ' ').title()
                            print(f"   ❌ Sorry, I couldn't control {device_friendly}")
                            print(f"   ⚠️  There was an issue communicating with the device")
                    
                    print(f"   ⏱️  {session.duration_ms}ms")
                else:
                    # Friendly response for small talk
                    text_lower = text.lower().strip()
                    if any(greeting in text_lower for greeting in ['hello', 'hi', 'hey', 'good morning', 'good evening']):
                        print("   💬 Hello! I'm your smart home assistant. How can I help you today?")
                    elif any(q in text_lower for q in ['how are you', 'whats up', "what's up"]):
                        print("   💬 I'm doing great! Ready to help you control your smart home devices.")
                    elif 'thank' in text_lower:
                        print("   💬 You're welcome! Happy to help.")
                    elif 'bye' in text_lower or 'goodbye' in text_lower:
                        print("   💬 Goodbye! Let me know if you need anything.")
                    else:
                        print("   ℹ️  I didn't recognize that as a smart home command.")
                        print("   💡 Try: 'Turn on the living room light' or 'Set bedroom light to 50 percent'")
                
                if session.errors:
                    print(f"   ⚠️  Errors: {', '.join(session.errors)}")
                    
            except KeyboardInterrupt:
                raise  # Re-raise to stop the system
            except Exception as e:
                error_msg = str(e)
                
                # Friendly error messages with conversational tone
                if "not found" in error_msg.lower() and "device" in error_msg.lower():
                    # Extract device name from error if possible
                    import re
                    match = re.search(r"Device '([^']+)'", error_msg)
                    if match:
                        device_name = match.group(1).replace('_', ' ')
                        print(f"   ❌ Sorry, I couldn't find '{device_name}' in your home.")
                    else:
                        print(f"   ❌ Sorry, I couldn't find that device.")
                    print(f"   💡 Available devices: living room light, bedroom light, kitchen light, ceiling fan")
                elif "timeout" in error_msg.lower():
                    print(f"   ❌ Sorry, that request took too long to process.")
                    print(f"   💡 Try a shorter, clearer command like 'Turn on living room light'")
                elif "mqtt" in error_msg.lower() or "connection" in error_msg.lower():
                    print(f"   ❌ Sorry, I'm having trouble connecting to your smart home.")
                    print(f"   💡 Check if your MQTT broker is running")
                elif "json" in error_msg.lower() or "parse" in error_msg.lower():
                    print(f"   ❌ Sorry, I had trouble understanding that command.")
                    print(f"   💡 Try rephrasing: 'Turn on the bedroom light'")
                else:
                    print(f"   ❌ Sorry, something went wrong: {error_msg}")
                    
                logger.error(f"Command processing error: {e}", exc_info=True)
                # Don't crash - keep listening for next command
        
        # Start continuous listening (Feature 001)
        listener = ContinuousListener(
            model_name="openai/whisper-base",
            device="cpu",
            on_transcription=on_transcription
        )
        
        listener.start()
        
        # Keep running until interrupted
        try:
            while True:
                import time
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Shutting down...")
    except Exception as e:
        print(f"\n\n❌ System error: {e}")
        logger.exception("System error")
    finally:
        # Cleanup
        print("\n🧹 Cleaning up...")
        try:
            listener.stop()
            print("   ✓ Audio listener stopped")
        except:
            pass
        
        try:
            router.cleanup()
            print("   ✓ SLM and MQTT cleaned up")
        except:
            pass
        
        print("\n✅ Shutdown complete")

if __name__ == "__main__":
    main()
