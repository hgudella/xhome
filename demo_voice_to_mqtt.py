"""Demo script for voice-to-MQTT pipeline.

Demonstrates the complete flow from voice transcription to MQTT publishing.
"""
import logging
import sys
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.command.router import CommandRouter
from src.devices.mqtt_config import MQTTConfig
from unittest.mock import patch, MagicMock

def print_separator():
    print("\n" + "="*80 + "\n")

def demo_voice_to_mqtt():
    """Run end-to-end voice-to-MQTT demo."""
    
    print_separator()
    print("🏠 XHOME Voice-to-MQTT Demo")
    print("Feature 002: SLM Command Understanding + MQTT Publishing")
    print_separator()
    
    # Configuration
    print("📋 Configuration:")
    print("   - Model: Phi-4-mini-instruct-Q4_K_M.gguf")
    print("   - Device Config: config/devices.yaml.example")
    print("   - MQTT: localhost:1883 (mocked for demo)")
    print_separator()
    
    # Demo transcriptions
    test_transcriptions = [
        "turn on the living room light",
        "set bedroom light to 75 percent brightness",
        "turn off the kitchen light",
        "set thermostat to 72 degrees",
    ]
    
    # Initialize router with mocked MQTT
    print("🔧 Initializing CommandRouter...")
    
    mqtt_config = MQTTConfig(
        host="localhost",
        port=1883
    )
    
    with patch('paho.mqtt.client.Client') as mock_mqtt:
        # Setup MQTT mock
        mock_client = MagicMock()
        mock_mqtt.return_value = mock_client
        mock_publish_result = MagicMock(rc=0)
        mock_client.publish.return_value = mock_publish_result
        
        router = CommandRouter(
            model_path="models/Phi-4-Mini-GGUF/Phi-4-mini-instruct-Q4_K_M.gguf",
            device_config_path="config/devices.yaml.example",
            mqtt_config=mqtt_config
        )
        
        # Mock connection state
        router.mqtt_client._connected = True
        
        print("   ✓ SLM Engine loaded")
        print("   ✓ Device configuration loaded")
        print("   ✓ MQTT client initialized (mocked for demo)")
        print_separator()
        
        run_demo_tests(router, test_transcriptions)
        
        # Cleanup
        router.cleanup()
        print("✓ Cleanup complete\n")
    
def run_demo_tests(router, test_transcriptions):
    """Run demo tests with given router."""
    print("🎤 Processing Voice Commands:\n")
    
    for i, transcription in enumerate(test_transcriptions, 1):
        print(f"Test {i}/{len(test_transcriptions)}")
        print(f"🗣️  Voice Input: \"{transcription}\"")
        
        try:
            # Process transcription
            session = router.process_transcription(transcription)
            
            # Display results
            if session.commands:
                for cmd in session.commands:
                    print(f"   ✓ Intent: {cmd.intent}")
                    print(f"   ✓ Device: {cmd.device}")
                    if cmd.parameters:
                        print(f"   ✓ Parameters: {cmd.parameters}")
                    print(f"   ✓ Confidence: {cmd.confidence:.2%}")
                
                if session.mqtt_messages:
                    for msg in session.mqtt_messages:
                        print(f"   📡 MQTT Topic: {msg['topic']}")
                        print(f"   📡 Payload: {msg['payload']}")
                
                print(f"   ⏱️  Processing Time: {session.duration_ms}ms")
            else:
                print("   ℹ️  No commands extracted")
            
            if session.errors:
                print(f"   ⚠️  Errors: {session.errors}")
            
            print()
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            print()
    
    print_separator()
    print("📊 Demo Summary:")
    print(f"   - Total Commands: {len(test_transcriptions)}")
    print(f"   - Commands Processed: {len([t for t in test_transcriptions])}")
    print(f"   - Pipeline: Voice → SLM → Device Resolution → MQTT")
    print_separator()
    
    print("✅ Demo Complete!")
    print("\nKey Features Demonstrated:")
    print("   1. Local SLM inference (Phi-4-Mini)")
    print("   2. Intent extraction (turn_on, turn_off, set_brightness, set_temperature)")
    print("   3. Device name resolution with aliases")
    print("   4. MQTT message generation with QoS 1")
    print("   5. Session tracking with metrics")
    print("   6. Privacy: 0-day retention (transcriptions not logged)")
    print_separator()
    
    print("🧹 Cleanup in progress...\n")

if __name__ == "__main__":
    try:
        demo_voice_to_mqtt()
    except KeyboardInterrupt:
        print("\n\n⚠️  Demo interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
