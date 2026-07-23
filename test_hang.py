import sys
print("1. Importing torch...", flush=True)
import torch
print("2. Checking CUDA...", flush=True)
print(f"CUDA Available: {torch.cuda.is_available()}", flush=True)
if torch.cuda.is_available():
    print(f"Device Name: {torch.cuda.get_device_name(0)}", flush=True)
print("3. Importing whisper...", flush=True)
import whisper
print("4. Loading model (tiny)...", flush=True)
model = whisper.load_model('tiny')
print("5. Moving tensor to GPU to test...", flush=True)
try:
    x = torch.randn(1, 1).cuda()
    print(f"Tensor moved: {x.device}", flush=True)
except Exception as e:
    print(f"Error moving to GPU: {e}", flush=True)

print("6. Creating dummy audio...", flush=True)
import numpy as np
dummy_audio = np.zeros(16000, dtype=np.float32)

print("7. Transcribing...", flush=True)
result = model.transcribe(dummy_audio)
print("8. Done! Result:", result['text'], flush=True)
