import sys, time
sys.path.insert(0, ".")
from void_voice.tts.piper_engine import VoiceEngine

print("=== VoiceEngine() constructor ===")
t0 = time.perf_counter()
engine = VoiceEngine()
print(f"init: {(time.perf_counter()-t0)*1000:.1f} ms")
print(f"in-process PiperVoice loaded: {engine._inprocess_voice is not None}")

print()
print("=== synthesize_to_bytes benchmark ===")
phrase = "Hello, I am VOID, your personal offline assistant."
_ = engine.synthesize_to_bytes(phrase)   # warmup
times = []
for i in range(3):
    t0 = time.perf_counter()
    result = engine.synthesize_to_bytes(phrase)
    elapsed_ms = (time.perf_counter() - t0) * 1000
    times.append(elapsed_ms)
    print(f"  run {i+1}: {elapsed_ms:.1f} ms, bytes={len(result) if result else 0}")
print(f"avg: {sum(times)/len(times):.1f} ms")
backend = "in-process Piper" if engine._inprocess_voice else "subprocess/SAPI/pyttsx3"
print(f"backend: {backend}")
