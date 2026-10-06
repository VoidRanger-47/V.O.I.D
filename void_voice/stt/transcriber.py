# void_voice/stt/transcriber.py
"""
Offline Speech-to-Text for V.O.I.D.
Audio capture: sounddevice (PortAudio/WASAPI on Windows) — replaces PyAudio + SpeechRecognition.
Transcription: faster-whisper (CTranslate2 C++ core) — unchanged.

Key improvements over the previous sr.Recognizer implementation:
  - Eliminates 600ms adjust_for_ambient_noise() blocking call.
  - Direct float32 PCM ring buffer: no Python buffer copy chain.
  - Non-blocking capture with energy-based Voice Activity Detection (VAD).
  - Graceful fallback to legacy sr.Recognizer if sounddevice is unavailable.
"""

import io
import os
import time
import threading
from collections import deque
import numpy as np
import torch

# ── Audio backend selection ────────────────────────────────────────────────────
try:
    import sounddevice as sd
    _SD_AVAILABLE = True
except ImportError:
    _SD_AVAILABLE = False

try:
    import speech_recognition as sr
    _SR_AVAILABLE = True
except ImportError:
    _SR_AVAILABLE = False

from faster_whisper import WhisperModel


# ── Constants ──────────────────────────────────────────────────────────────────
_SAMPLE_RATE    = 16_000      # Whisper requires 16 kHz mono
_CHANNELS       = 1
_DTYPE          = "float32"
_FRAME_DURATION = 0.030       # 30 ms frames for VAD
_FRAME_SAMPLES  = int(_SAMPLE_RATE * _FRAME_DURATION)

# Energy-based VAD thresholds
_SILENCE_ENERGY  = 0.005      # frames below this are silence (calibrated for laptop mics)
_SPEECH_ENERGY   = 0.010      # frames above this are speech (calibrated for natural speech)
_SILENCE_FRAMES  = 25         # consecutive silence frames before ending capture (~750 ms)
_MAX_RECORD_SEC  = 15         # hard cap


class _WASAPICapture:
    """
    Low-latency audio capture using sounddevice (PortAudio → WASAPI on Windows).

    Records in 30 ms increments into a float32 numpy array. Uses simple
    energy-based Voice Activity Detection (VAD) to:
      1. Wait for speech onset without blocking the thread for a fixed period.
      2. Stop automatically when the user pauses for ~750 ms.

    This replaces the previous flow:
        sr.Recognizer.adjust_for_ambient_noise()  ← 600 ms block removed
        sr.Recognizer.listen()
        audio.get_wav_data()                      ← full PCM copy removed
    """

    def __init__(self, device: int = None, timeout: float = 8.0):
        self._device       = device          # None = system default
        self._timeout      = timeout
        self._frames: list = []
        self._preroll_buf  = deque(maxlen=8) # Keep ~240ms pre-speech audio
        self._lock         = threading.Lock()
        self._speech_started = False
        self._silence_count  = 0
        self._done           = threading.Event()
        self._overflow       = False
        self._error: str     = ""

    def _callback(self, indata: np.ndarray, frames: int, time_info, status):
        """sounddevice stream callback — runs on the PortAudio thread (no GIL)."""
        if status.input_overflow:
            self._overflow = True
        energy = float(np.sqrt(np.mean(indata ** 2)))

        with self._lock:
            if not self._speech_started:
                self._preroll_buf.append(indata.copy())
                if energy >= _SPEECH_ENERGY:
                    self._speech_started = True
                    # Prepend pre-roll buffer so the leading consonant/syllable (e.g. "V-") is not clipped
                    self._frames.extend(list(self._preroll_buf))
            else:
                self._frames.append(indata.copy())
                if energy < _SILENCE_ENERGY:
                    self._silence_count += 1
                    if self._silence_count >= _SILENCE_FRAMES:
                        self._done.set()
                else:
                    self._silence_count = 0

                # Hard cap
                total_samples = len(self._frames) * _FRAME_SAMPLES
                if total_samples / _SAMPLE_RATE >= _MAX_RECORD_SEC:
                    self._done.set()

    def record(self) -> np.ndarray:
        """
        Opens the WASAPI stream, waits for speech onset, records until silence,
        and returns a float32 mono PCM array at 16 kHz.
        Returns an empty array on timeout or error.
        """
        try:
            with sd.InputStream(
                samplerate=_SAMPLE_RATE,
                channels=_CHANNELS,
                dtype=_DTYPE,
                blocksize=_FRAME_SAMPLES,
                device=self._device,
                callback=self._callback,
                latency="low",              # Request low-latency WASAPI mode
            ):
                # Wait up to timeout for the VAD to signal completion
                self._done.wait(timeout=self._timeout)

            with self._lock:
                frames = list(self._frames)

            if not frames:
                return np.array([], dtype=np.float32)

            return np.concatenate(frames, axis=0).flatten()

        except Exception as e:
            self._error = str(e)
            return np.array([], dtype=np.float32)


def _pcm_to_wav_bytes(pcm: np.ndarray, sample_rate: int = _SAMPLE_RATE) -> bytes:
    """Pack float32 PCM array into a minimal in-memory WAV byte string."""
    import struct, wave
    pcm_int16 = (np.clip(pcm, -1.0, 1.0) * 32767).astype(np.int16)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)          # int16 = 2 bytes
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_int16.tobytes())
    buf.seek(0)
    return buf


# ── Public Ear class ───────────────────────────────────────────────────────────

class Ear:
    """
    100% Offline Speech-to-Text module for V.O.I.D.

    Audio backend priority:
        1. sounddevice (PortAudio / WASAPI on Windows)  ← preferred
        2. speech_recognition + PyAudio                 ← legacy fallback

    Transcription: faster-whisper (CTranslate2, runs on CUDA or CPU).
    Zero external cloud calls or network dependencies.
    """

    def __init__(self, config: dict):
        self.config   = config
        self.language = config.get("language", "en-US")

        # ── Whisper model ──────────────────────────────────────────────────────
        use_gpu          = config.get("use_gpu", True) and torch.cuda.is_available()
        self.device      = "cuda" if use_gpu else "cpu"
        self.compute_type = "float16" if self.device == "cuda" else "int8"
        model_size       = config.get("whisper_model", "small.en")

        print(f"[VOICE] Loading Faster-Whisper ({model_size}) on {self.device} ({self.compute_type})...")
        try:
            self.model    = WhisperModel(model_size, device=self.device, compute_type=self.compute_type)
            self.is_ready = True
        except Exception as e:
            print(f"[WARN] Faster-Whisper GPU load failed ({e}), falling back to CPU int8...")
            try:
                self.device        = "cpu"
                self.compute_type  = "int8"
                self.model         = WhisperModel(model_size, device="cpu", compute_type="int8")
                self.is_ready      = True
            except Exception as e2:
                print(f"[ERROR] Faster-Whisper CPU load failed: {e2}")
                self.model    = None
                self.is_ready = False

        # ── Audio backend ──────────────────────────────────────────────────────
        if _SD_AVAILABLE:
            print("[VOICE] Audio backend: sounddevice (PortAudio/WASAPI) — low-latency mode active.")
            self._use_sounddevice = True
        elif _SR_AVAILABLE:
            print("[VOICE] Audio backend: SpeechRecognition (PyAudio) — legacy fallback mode.")
            self._use_sounddevice = False
            self._recognizer      = sr.Recognizer()
        else:
            print("[ERROR] No audio capture backend available (sounddevice and speech_recognition both missing).")
            self._use_sounddevice = False
            self.is_ready         = False

    # ── Public API ─────────────────────────────────────────────────────────────

    def transcribe_file(self, file_path: str) -> str:
        """
        Transcribe audio from a local file path using local faster-whisper.
        API is unchanged from the previous implementation.
        """
        if not self.is_ready or not self.model:
            return "[Error: Local Whisper engine not available]"
        try:
            if not os.path.exists(file_path):
                return "[Error: Audio file not found]"
            segments, _ = self.model.transcribe(
                file_path,
                beam_size=3,
                initial_prompt="Hey VOID, VOID, phone assistant, unlock phone, open app."
            )
            text = "".join(seg.text for seg in segments).strip()
            return text if text else "[inaudible]"
        except Exception as e:
            return f"[Transcription Error: {str(e)}]"

    def listen_and_transcribe(self, timeout: int = 8, phrase_time_limit: int = 15) -> str:
        """
        Listen to microphone and transcribe speech 100% locally via Faster-Whisper.
        No internet or Google Cloud APIs required.

        When sounddevice is available:
          - Opens WASAPI stream directly (low latency, no 600 ms calibration).
          - Returns immediately on timeout if no speech detected.

        Falls back to the legacy sr.Recognizer + PyAudio path if sounddevice
        is unavailable.
        """
        if not self.is_ready or not self.model:
            return "[Error: Local Whisper engine not available]"

        if self._use_sounddevice:
            return self._transcribe_via_sounddevice(timeout=float(timeout))
        else:
            return self._transcribe_via_sr(timeout=timeout, phrase_time_limit=phrase_time_limit)

    # ── Private: sounddevice path ──────────────────────────────────────────────

    def _transcribe_via_sounddevice(self, timeout: float) -> str:
        """
        WASAPI capture path.

        Flow:
          1. Open a low-latency WASAPI input stream (no blocking calibration).
          2. Collect float32 PCM frames in a ring buffer via the PortAudio callback.
          3. Energy-based VAD: record from speech onset until ~750 ms of silence.
          4. Pack PCM into an in-memory WAV BytesIO and transcribe with Whisper.
        """
        try:
            capture = _WASAPICapture(device=None, timeout=timeout)
            pcm     = capture.record()

            if capture._error:
                print(f"[VOICE] sounddevice capture error: {capture._error}")
                return "[Error: Audio capture failed]"

            if pcm is None or len(pcm) < _SAMPLE_RATE * 0.2:
                # Less than 200 ms of audio means timeout with no speech
                return ""

            wav_buf = _pcm_to_wav_bytes(pcm, _SAMPLE_RATE)
            segments, _ = self.model.transcribe(
                wav_buf,
                beam_size=3,
                initial_prompt="Hey VOID, VOID, phone assistant, unlock phone, open app."
            )
            text = "".join(seg.text for seg in segments).strip()
            return text if text else "[inaudible]"

        except Exception as e:
            return f"[Offline STT Error: {e}]"

    # ── Private: legacy sr.Recognizer fallback ─────────────────────────────────

    def _transcribe_via_sr(self, timeout: int, phrase_time_limit: int) -> str:
        """
        Legacy SpeechRecognition + PyAudio path.
        Kept for environments where sounddevice is not available.
        Behaviour is identical to the original implementation.
        """
        try:
            with sr.Microphone() as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.6)
                audio = self._recognizer.listen(
                    source, timeout=timeout, phrase_time_limit=phrase_time_limit
                )
            wav_data   = audio.get_wav_data()
            wav_stream = io.BytesIO(wav_data)
            segments, _ = self.model.transcribe(wav_stream, beam_size=3)
            text = "".join(seg.text for seg in segments).strip()
            return text if text else "[inaudible]"
        except sr.WaitTimeoutError:
            return ""
        except Exception as e:
            return f"[Offline STT Error: {e}]"