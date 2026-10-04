"""
scripts/benchmark_voice.py
Measures wall-clock latency of both STT and TTS paths.
Run BEFORE and AFTER the C++ migration changes to get concrete numbers.

Usage:
    python scripts/benchmark_voice.py --tts-only
    python scripts/benchmark_voice.py --stt-only
    python scripts/benchmark_voice.py         # both
"""

import sys
import time
import io
import wave
import argparse
import numpy as np

def benchmark_tts():
    """Measure time from synthesize_to_bytes() call to first byte of audio."""
    print("\n[BENCHMARK] TTS — piper_engine.VoiceEngine.synthesize_to_bytes()")
    print("=" * 60)

    from void_voice.tts.piper_engine import VoiceEngine
    engine = VoiceEngine(config={"tts_enabled": False})

    phrases = [
        "Hello, I am V.O.I.D., your personal offline assistant.",
        "The current system time is twelve thirty PM.",
        "I have found three relevant memory entries matching your query.",
    ]

    for phrase in phrases:
        # Warmup run (model load)
        _ = engine.synthesize_to_bytes(phrase)

        # Timed run
        N = 3
        times = []
        for _ in range(N):
            t0 = time.perf_counter()
            result = engine.synthesize_to_bytes(phrase)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            times.append(elapsed_ms)
            status = "OK" if result else "FAIL"

        avg = sum(times) / len(times)
        print(f"  [{status}] avg={avg:.1f} ms  min={min(times):.1f} ms  | \"{phrase[:45]}...\"")

    print()


def benchmark_stt_import():
    """Measure the cold import + model load time (Whisper init)."""
    print("\n[BENCHMARK] STT — Ear() constructor (Whisper model load)")
    print("=" * 60)

    t0 = time.perf_counter()
    from void_voice.stt.transcriber import Ear
    elapsed_import = (time.perf_counter() - t0) * 1000
    print(f"  Import time: {elapsed_import:.1f} ms")

    config = {"use_gpu": True, "whisper_model": "small.en"}
    t1 = time.perf_counter()
    ear = Ear(config)
    elapsed_init = (time.perf_counter() - t1) * 1000
    print(f"  Ear() init (model load): {elapsed_init:.1f} ms")
    print(f"  Audio backend: {'sounddevice (WASAPI)' if ear._use_sounddevice else 'SpeechRecognition (PyAudio)'}")
    print(f"  Whisper device: {ear.device}, compute: {ear.compute_type}")
    print()

    return ear


def benchmark_tts_import():
    """Measure TTS cold import time."""
    print("\n[BENCHMARK] TTS — VoiceEngine() constructor")
    print("=" * 60)
    t0 = time.perf_counter()
    from void_voice.tts.piper_engine import VoiceEngine
    elapsed_import = (time.perf_counter() - t0) * 1000
    print(f"  Import time: {elapsed_import:.1f} ms")

    t1 = time.perf_counter()
    engine = VoiceEngine()
    elapsed_init = (time.perf_counter() - t1) * 1000
    print(f"  VoiceEngine() init: {elapsed_init:.1f} ms")

    has_inproc = engine._inprocess_voice is not None
    print(f"  In-process PiperVoice loaded: {has_inproc}")
    print()

    return engine


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V.O.I.D. voice pipeline latency benchmark")
    parser.add_argument("--tts-only", action="store_true")
    parser.add_argument("--stt-only", action="store_true")
    args = parser.parse_args()

    run_tts = not args.stt_only
    run_stt = not args.tts_only

    print("V.O.I.D. Voice Pipeline Latency Benchmark")
    print(f"Python {sys.version}")
    print()

    if run_stt:
        benchmark_stt_import()

    if run_tts:
        benchmark_tts_import()
        benchmark_tts()
