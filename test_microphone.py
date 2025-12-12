Open file. Hello. Hello world. Checking. Problem construction. Yep. Hey, Cortana. Once upon a Time in China. Knock. Knock. Hey, Cortana. OK testing 1235. Testing 1235678. Cortana. What? It's not trivia, are you? Oh. Hello. Hello. Hi there. Mike testing 123123. At least I see some transcription right now, but it's not correct. No, you missed entirely. Can you turn on the lights? Go on? Will you please turn on the lights? Can you please turn on the lights? What happened now it's not working. Hello. Hello 123. Testing 123123 Testing 123. Hello. Why the **** are you not working? Friday has. Recent message. Hello. Hi there. How are you? Once upon a time. Once upon a Time in China. Hey, Cortana. Hi there. Hello world. Can you please turn on the lights? Can you please turn off the lights? Wow. It's working really transcription. Oh really? Why did that fix someone saying was? From the. Those should be there after the kids. Hello. Hello, Chiti. Hello, Chitti. Can you turn on the Light City? Can you? Can you turn on the light please? Can you turn on the lights please? Can you turn on the lights please? I said turn off. I said turn down the lights. What is my To Do List today? Do I have a robo in my home? When you make the fix up for me. Hey, Chitti. Will you make a pizza for me? Shiman, can you make it easier for her? However, I still see the debug printing statement in the output. A file must have been udated. Let me check if there is a Python cache issue to reset. Good job. Hey, Kitty. Hey, Chitti. Hey, Chitti. Hey. Hey, Chitty. Yes, Sir. Should I be training you with Indian slang? Isn't it? Can you bring me some water? You know. OK. How does Genzi Tipple talk? Hello world. Hello. Hello. What the **** is happening? What does it mean? No. """Test microphone input levels to diagnose transcription issues."""

import sounddevice as sd
import numpy as np
import time

print("=" * 60)
print("🎤 Microphone Level Test")
print("=" * 60)
print()
print("This will show you the audio levels from your microphone.")
print("SPEAK LOUDLY into your mic to test.")
print("Press Ctrl+C to stop")
print()

sample_rate = 16000
chunk_duration = 0.1  # 100ms chunks
chunk_samples = int(sample_rate * chunk_duration)

def audio_callback(indata, frames, time_info, status):
    """Process audio and show levels."""
    if status:
        print(f"Status: {status}")
    
    # Convert to float32
    audio = indata.flatten().astype(np.float32)
    
    # Normalize if int16
    if indata.dtype == np.int16:
        audio = audio / 32768.0
    
    # Calculate levels
    level = np.abs(audio).mean()
    max_level = np.abs(audio).max()
    rms = np.sqrt(np.mean(audio**2))
    
    # Create visual bar
    bar_length = int(level * 100)
    bar = "█" * bar_length
    
    # Color code by level
    if level < 0.01:
        status_icon = "🔇"  # Too quiet
        status_text = "TOO QUIET - SPEAK LOUDER!"
    elif level < 0.05:
        status_icon = "🔉"  # Quiet
        status_text = "Quiet - speak louder"
    elif level < 0.15:
        status_icon = "🔊"  # Good
        status_text = "Good level ✓"
    else:
        status_icon = "📢"  # Loud
        status_text = "Loud! (good)"
    
    print(f"\r{status_icon} Level: {level:.4f} {bar:40s} {status_text:30s}", end="", flush=True)

try:
    # List available devices
    print("Available audio devices:")
    print(sd.query_devices())
    print()
    
    default_device = sd.query_devices(kind='input')
    print(f"Using default input: {default_device['name']}")
    print()
    
    # Start stream
    with sd.InputStream(
        samplerate=sample_rate,
        channels=1,
        blocksize=chunk_samples,
        callback=audio_callback
    ):
        print("Monitoring... (Ctrl+C to stop)")
        print()
        while True:
            time.sleep(0.1)

except KeyboardInterrupt:
    print("\n\n✅ Test completed!")
    print()
    print("Expected levels for good transcription:")
    print("  - Normal speech: 0.02 - 0.10")
    print("  - Loud speech: 0.10 - 0.30")
    print("  - Too quiet (won't transcribe well): < 0.01")
    print()
    print("If levels were too low, try:")
    print("  1. Speak louder and closer to microphone")
    print("  2. Increase microphone boost in Windows Sound Settings")
    print("  3. Use a better microphone")

except Exception as e:
    print(f"\n❌ Error: {e}")
