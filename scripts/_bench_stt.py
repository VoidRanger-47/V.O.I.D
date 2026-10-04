import sys, time
sys.path.insert(0, ".")
from void_voice.stt.transcriber import Ear, _SD_AVAILABLE, _SR_AVAILABLE

print("=== Audio backend detection ===")
print(f"sounddevice available: {_SD_AVAILABLE}")
print(f"speech_recognition available: {_SR_AVAILABLE}")
print()

print("=== Ear() constructor (Whisper model load) ===")
config = {"use_gpu": True, "whisper_model": "small.en"}
t0 = time.perf_counter()
ear = Ear(config)
elapsed_ms = (time.perf_counter() - t0) * 1000
print(f"Ear() init: {elapsed_ms:.0f} ms")
print(f"Backend: {'sounddevice (WASAPI)' if ear._use_sounddevice else 'SpeechRecognition+PyAudio'}")
print(f"Whisper: device={ear.device}, compute={ear.compute_type}, ready={ear.is_ready}")
