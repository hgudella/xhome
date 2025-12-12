"""Quick test to verify Whisper score output"""
import torch
from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
import numpy as np

# Load model
model_name = "openai/whisper-base"
device = "cuda:0" if torch.cuda.is_available() else "cpu"
torch_dtype = torch.float16 if torch.cuda.is_available() else torch.float32

print(f"Loading {model_name} on {device}...")
model = AutoModelForSpeechSeq2Seq.from_pretrained(
    model_name,
    torch_dtype=torch_dtype,
    low_cpu_mem_usage=True,
    use_safetensors=True,
)
model.to(device)
processor = AutoProcessor.from_pretrained(model_name)

# Generate some dummy audio (1 second of silence)
audio = np.zeros(16000, dtype=np.float32)

# Process audio
inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
inputs = inputs.to(device)

# Generate with scores
with torch.no_grad():
    outputs = model.generate(
        inputs["input_features"],
        max_new_tokens=128,
        language="en",
        task="transcribe",
        return_dict_in_generate=True,
        output_scores=True
    )

print(f"\nOutputs type: {type(outputs)}")
print(f"Outputs attributes: {dir(outputs)}")
print(f"Has 'scores': {hasattr(outputs, 'scores')}")

if hasattr(outputs, 'scores'):
    print(f"Scores type: {type(outputs.scores)}")
    print(f"Number of score tensors: {len(outputs.scores)}")
    if len(outputs.scores) > 0:
        print(f"First score shape: {outputs.scores[0].shape}")
        
        # Calculate confidence
        token_probs = []
        for score in outputs.scores:
            probs = torch.softmax(score, dim=-1)
            max_prob = probs.max().item()
            token_probs.append(max_prob)
            print(f"Token prob: {max_prob:.4f}")
        
        confidence = np.mean(token_probs) if token_probs else 0.85
        print(f"\nFinal confidence: {confidence:.4f}")
else:
    print("NO SCORES ATTRIBUTE!")

# Decode text
text = processor.batch_decode(outputs.sequences, skip_special_tokens=True)[0]
print(f"\nTranscribed text: '{text}'")
