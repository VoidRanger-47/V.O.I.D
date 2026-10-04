# void_voice/tts/piper_engine.py
"""
Local Text-to-Speech engine for V.O.I.D.
Provides in-memory WAV synthesis for Web streaming and in-process playback.
Runs 100% offline.

Synthesis backend priority:
  1. PiperVoice in-process API    ← eliminates ~300-600 ms subprocess spawn overhead
  2. Piper via subprocess          ← legacy fallback if ONNX model not found
  3. Windows SAPI (Native, fast, offline)
  4. pyttsx3

Key improvement over previous implementation:
  - `PiperVoice.synthesize_wav()` is called directly in-process using the
    piper-tts Python package (wraps the C++ ONNX runtime internally).
  - Eliminates: subprocess.run(sys.executable, "-m", "piper", ...) startup cost.
  - Eliminates: temp WAV file write + file read round-trip.
  - In-process synthesis writes directly to io.BytesIO in ~10-40 ms for short phrases.
"""

import io
import os
import re
import sys
import wave
import tempfile
import subprocess
import threading
from pathlib import Path
from typing import Optional

# ── Piper in-process backend ───────────────────────────────────────────────────
try:
    from piper import PiperVoice
    _PIPER_PACKAGE_AVAILABLE = True
except ImportError:
    _PIPER_PACKAGE_AVAILABLE = False

# ── Voice model cache (singleton per model path, thread-safe) ──────────────────
_voice_cache: dict[str, "PiperVoice"] = {}
_voice_cache_lock = threading.Lock()


def _load_piper_voice(model_path: str) -> Optional["PiperVoice"]:
    """Load and cache a PiperVoice by ONNX model path. Thread-safe singleton."""
    with _voice_cache_lock:
        if model_path in _voice_cache:
            return _voice_cache[model_path]
        try:
            voice = PiperVoice.load(model_path, use_cuda=False)
            _voice_cache[model_path] = voice
            print(f"[TTS] PiperVoice loaded in-process: {Path(model_path).name}")
            return voice
        except Exception as e:
            print(f"[TTS] PiperVoice load failed for {model_path}: {e}")
            return None


class VoiceEngine:
    """
    Local Text-to-Speech engine supporting in-process Piper, subprocess Piper,
    Windows SAPI, and pyttsx3. Runs 100% offline.
    """

    def __init__(self, config=None):
        self.config      = config or {}
        self.voice       = self.config.get("voice_model_path") or self.config.get("voice", "en_US-amy-medium")
        self.output_file = "void_output.wav"
        self.tts_enabled = self.config.get("tts_enabled", True)
        self.is_speaking = False

        # Eagerly resolve and cache the voice model if an ONNX path is available
        self._inprocess_voice: Optional["PiperVoice"] = None
        if _PIPER_PACKAGE_AVAILABLE:
            onnx_path = self._resolve_onnx_path(self.voice)
            if onnx_path:
                self._inprocess_voice = _load_piper_voice(onnx_path)

    # ── Text cleaning ──────────────────────────────────────────────────────────

    def clean_text_for_speech(self, text: str) -> str:
        """Strip reasoning accordions, code blocks, URLs, and markdown tokens before speech."""
        if not text:
            return ""
        # Remove <thinking>...</thinking> tags and contents
        cleaned = re.sub(r'<thinking>[\s\S]*?</thinking>', '', text, flags=re.IGNORECASE)
        # Remove code blocks ```...```
        cleaned = re.sub(r'```[\s\S]*?```', ' Code block omitted. ', cleaned)
        # Remove inline code `...`
        cleaned = re.sub(r'`[^`]+`', ' ', cleaned)
        # Remove markdown links [text](url) -> text
        cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
        # Remove markdown headers #, bold/italic *, _, ~, etc.
        cleaned = re.sub(r'[*#_~`\[\]()<>]', ' ', cleaned)
        # Remove excessive whitespace
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        return cleaned

    # ── Public synthesis API ───────────────────────────────────────────────────

    def synthesize_to_bytes(self, text: str) -> Optional[bytes]:
        """Synthesize text to WAV audio bytes using the best available backend."""
        clean_text = self.clean_text_for_speech(text)
        if not clean_text:
            return None

        # 1. In-process PiperVoice (preferred — no subprocess overhead)
        if self._inprocess_voice is not None:
            result = self._synthesize_inprocess(clean_text)
            if result:
                return result

        # 2. Subprocess Piper (fallback if model not cached but ONNX exists on disk)
        piper_bytes = self._synthesize_piper_subprocess(clean_text)
        if piper_bytes:
            return piper_bytes

        # 3. Windows SAPI (Native, fast, offline)
        if os.name == "nt":
            sapi_bytes = self._synthesize_sapi(clean_text)
            if sapi_bytes:
                return sapi_bytes

        # 4. pyttsx3
        pyttsx3_bytes = self._synthesize_pyttsx3(clean_text)
        if pyttsx3_bytes:
            return pyttsx3_bytes

        return None

    def synthesize_to_file(self, text: str, output_path: str) -> bool:
        """Synthesize text and write directly to an audio file."""
        audio_data = self.synthesize_to_bytes(text)
        if audio_data:
            try:
                with open(output_path, "wb") as f:
                    f.write(audio_data)
                return True
            except Exception as e:
                print(f"[TTS Error writing file]: {e}")
        return False

    def stop_speaking(self):
        """Barge-in support: immediately stop any ongoing TTS audio playback."""
        try:
            if os.name == "nt":
                import winsound
                winsound.PlaySound(None, winsound.SND_PURGE)
            self.is_speaking = False
        except Exception:
            pass

    def speak(self, text: str, blocking: bool = False):
        """Convert text to speech locally and play it in-process."""
        if not self.tts_enabled:
            print(f"[V.O.I.D.]: {text}")
            return

        audio_bytes = self.synthesize_to_bytes(text)
        if audio_bytes:
            try:
                with open(self.output_file, "wb") as f:
                    f.write(audio_bytes)
                self._play_audio(self.output_file, blocking=blocking)
            except Exception as e:
                print(f"[TTS Playback Error]: {e}")
        else:
            print(f"[V.O.I.D. (Text)]: {text}")

    # ── Private: in-process Piper ──────────────────────────────────────────────

    def _resolve_onnx_path(self, voice_name: str) -> Optional[str]:
        """
        Resolve a voice name or path string to an absolute ONNX model path.
        Returns None if no ONNX file can be located.
        """
        voice_path = Path(voice_name)
        if voice_path.is_file() and voice_path.suffix == ".onnx":
            return str(voice_path)

        candidates = [
            Path("void_voice/tts/voice_models") / f"{voice_name}.onnx",
            Path("void_voice/voices")            / f"{voice_name}.onnx",
            Path("void_voice/tts/voice_models") / voice_name,
            Path("void_voice/voices")            / voice_name,
        ]
        for c in candidates:
            if c.is_file():
                return str(c)
        return None

    def _synthesize_inprocess(self, text: str) -> Optional[bytes]:
        """
        Call PiperVoice.synthesize_wav() directly in-process.

        Writes PCM audio directly into an io.BytesIO via a wave.Wave_write
        wrapper — no temp files, no subprocess spawn.

        Timing: ~10–50 ms for short phrases on CPU (ONNX Runtime).
        """
        try:
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wav_out:
                self._inprocess_voice.synthesize_wav(text, wav_out)
            buf.seek(0)
            result = buf.read()
            return result if result else None
        except Exception as e:
            print(f"[TTS] In-process Piper synthesis error: {e}")
            return None

    # ── Private: subprocess Piper fallback ────────────────────────────────────

    def _synthesize_piper_subprocess(self, text: str) -> Optional[bytes]:
        """
        Legacy subprocess Piper path.
        Used only when an ONNX model is not found for in-process synthesis.
        """
        onnx_path = self._resolve_onnx_path(self.voice)
        if not onnx_path:
            return None

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            temp_wav = tf.name
        try:
            cmd    = [sys.executable, "-m", "piper", "--model", onnx_path, "--output_file", temp_wav]
            result = subprocess.run(cmd, input=text.encode("utf-8"), capture_output=True, timeout=10)
            if result.returncode == 0 and os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                with open(temp_wav, "rb") as f:
                    return f.read()
        except Exception:
            pass
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
        return None

    # ── Private: SAPI fallback ─────────────────────────────────────────────────

    def _synthesize_sapi(self, text: str) -> Optional[bytes]:
        """Synthesize audio using Windows SAPI."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            temp_wav = tf.name
        try:
            import win32com.client as wincl
            speaker = wincl.Dispatch("SAPI.SpVoice")
            stream  = wincl.Dispatch("SAPI.SpFileStream")
            stream.Open(temp_wav, 3, False)   # 3 = SSFMCreateForWrite
            speaker.AudioOutputStream = stream
            speaker.Speak(text)
            stream.Close()
            if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                with open(temp_wav, "rb") as f:
                    return f.read()
        except Exception as e:
            print(f"[SAPI TTS Error]: {e}")
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
        return None

    # ── Private: pyttsx3 fallback ──────────────────────────────────────────────

    def _synthesize_pyttsx3(self, text: str) -> Optional[bytes]:
        """Synthesize audio using pyttsx3."""
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tf:
            temp_wav = tf.name
        try:
            import pyttsx3
            engine = pyttsx3.init()
            engine.save_to_file(text, temp_wav)
            engine.runAndWait()
            if os.path.exists(temp_wav) and os.path.getsize(temp_wav) > 0:
                with open(temp_wav, "rb") as f:
                    return f.read()
        except Exception as e:
            print(f"[pyttsx3 TTS Error]: {e}")
        finally:
            if os.path.exists(temp_wav):
                try:
                    os.remove(temp_wav)
                except Exception:
                    pass
        return None

    # ── Private: audio playback ────────────────────────────────────────────────

    def _play_audio(self, filepath: str, blocking: bool = False):
        """Play audio file in-process without launching GUI media player applications."""
        try:
            if os.name == "nt":   # Windows
                import winsound
                flags = winsound.SND_FILENAME
                if not blocking:
                    flags |= winsound.SND_ASYNC
                self.is_speaking = True
                winsound.PlaySound(filepath, flags)
            else:                 # Linux/Mac
                subprocess.run(
                    ["ffplay", "-nodisp", "-autoexit", filepath],
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL
                )
        except Exception as e:
            print(f"Could not play in-process audio: {e}")