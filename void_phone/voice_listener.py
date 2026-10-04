"""
Voice Listener for V.O.I.D. Phone Control.
Listens continuously for the wake word "Void", transcribes spoken phone commands,
and triggers intent-based ADB execution.
"""

from __future__ import annotations

import json
import os
import sys
import threading
import time
from typing import Callable, Optional

import colorama
from colorama import Fore, Style

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

colorama.init(autoreset=True)

from void_phone.intent_parser import IntentParser, IntentType, PhoneIntent, intent_parser
from void_phone.phone_controller import PhoneController, phone_controller


class PhoneVoiceListener:
    """
    Continuous voice recognition loop for phone automation.
    """
    def __init__(
        self,
        controller: Optional[PhoneController] = None,
        parser: Optional[IntentParser] = None,
        config_path: Optional[str] = None
    ):
        self.controller = controller or phone_controller
        self.parser = parser or intent_parser
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "phone_config.json")
        self.config = self._load_config()
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Voice components (lazy-loaded on demand)
        self._stt_initialized = False
        self.sr_recognizer = None
        self.ear = None
        self.tts = None

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _ensure_voice_components(self):
        """Lazily initialize speech recognition and TTS engines when needed."""
        if self._stt_initialized:
            return

        self._stt_initialized = True

        # Try Faster-Whisper from void_voice
        try:
            from void_voice.stt.transcriber import Ear
            voice_cfg_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "void_voice", "config", "config.json")
            v_cfg = {}
            if os.path.exists(voice_cfg_path):
                with open(voice_cfg_path, "r") as vf:
                    v_cfg = json.load(vf)
            self.ear = Ear(v_cfg)
        except Exception as e:
            print(f"[VoiceListener] Faster-Whisper fallback to SpeechRecognition: {e}")

        # SpeechRecognition fallback
        try:
            import speech_recognition as sr
            self.sr_recognizer = sr.Recognizer()
            self.sr_recognizer.energy_threshold = 300
            self.sr_recognizer.dynamic_energy_threshold = True
        except Exception as e:
            print(f"[VoiceListener] SpeechRecognition init: {e}")

        # Piper / local TTS
        try:
            from void_voice.tts.piper_engine import VoiceEngine
            if 'v_cfg' in locals() and v_cfg:
                self.tts = VoiceEngine(v_cfg)
        except Exception:
            pass

    def speak_feedback(self, text: str):
        """Provide voice feedback if TTS is enabled, otherwise log to console."""
        clean_text = text.replace("🚀", "").replace("📱", "").replace("📞", "").replace("🔓", "").replace("🔒", "").strip()
        print(Fore.CYAN + f"🤖 V.O.I.D.: {text}")
        if self.config.get("voice", {}).get("speak_feedback", True):
            self._ensure_voice_components()
            if self.tts:
                try:
                    self.tts.speak(clean_text)
                except Exception:
                    pass

    def process_command_text(self, command_text: str) -> str:
        """Parse spoken or typed text, execute intent, and return response."""
        print(Fore.YELLOW + f"👤 Transcribed: \"{command_text}\"")

        intent: PhoneIntent = self.parser.parse(command_text)
        print(Fore.BLUE + f"🎯 Identified Intent: {intent.intent_type.value} (conf={intent.confidence:.2f}) {intent.parameters}")

        if intent.intent_type == IntentType.UNKNOWN:
            res = f"I didn't recognize a specific phone action in '{command_text}'. Try 'open JioCinema', 'unlock my phone', or 'call [contact]'."
        else:
            res = intent.execute(self.controller)

        print(Fore.GREEN + f"📱 Execution Result: {res}")
        self.speak_feedback(res)
        return res

    def listen_and_transcribe_once(self) -> Optional[str]:
        """Capture one speech utterance from the microphone."""
        self._ensure_voice_components()
        if self.ear and self.ear.is_ready:
            try:
                text = self.ear.listen_and_transcribe(timeout=6, phrase_time_limit=8)
                return text.strip() if text else None
            except Exception as e:
                print(f"[VoiceListener] Ear error: {e}")

        if self.sr_recognizer:
            import speech_recognition as sr
            try:
                with sr.Microphone() as source:
                    print(Fore.WHITE + Style.DIM + "🎤 Listening...")
                    audio = self.sr_recognizer.listen(source, timeout=5, phrase_time_limit=8)
                try:
                    text = self.sr_recognizer.recognize_google(audio)
                    return text.strip()
                except sr.UnknownValueError:
                    return None
                except Exception as e:
                    print(f"[VoiceListener] Online STT error: {e}")
            except Exception as e:
                print(f"[VoiceListener] Mic capture error: {e}")

        return None

    def run_continuous_loop(self):
        """
        Main continuous voice loop.
        Listens for wake words like 'Void', captures subsequent phone commands, and executes ADB actions.
        """
        self._running = True
        wake_words = ["void", "hey void", "ok void", "hello void", "hey, void"]

        print(Fore.CYAN + Style.BRIGHT + """
        ====================================================
          V.O.I.D. — ANDROID PHONE VOICE ASSISTANT ONLINE
          Listening for Wake Word: "Void"
        ====================================================
        """)

        # Quick connection diagnostic
        summary = self.controller.get_status_summary()
        if summary.get("connected"):
            print(Fore.GREEN + f"✅ Connected to: {summary.get('model')} ({summary.get('serial')}) | Battery: {summary.get('battery_level')}")
        else:
            print(Fore.YELLOW + "⚠️ No phone currently detected. Connect via USB or WiFi ('adb connect <ip>:5555').")

        print(Fore.GREEN + "👂 Standby... Say 'Void, unlock my phone' or 'Void, open JioCinema'\n")

        while self._running:
            try:
                transcript = self.listen_and_transcribe_once()
                if not transcript:
                    continue

                lower = transcript.lower()

                # Check if wake word is present
                is_wake = any(w in lower for w in wake_words)
                if is_wake:
                    print(Fore.MAGENTA + f"\n⚡ Wake Word Detected: '{transcript}'")
                    # Extract the command portion
                    cmd_part = transcript
                    for w in wake_words:
                        if lower.startswith(w):
                            cmd_part = transcript[len(w):].strip(", ")
                            break

                    if not cmd_part or len(cmd_part) < 3:
                        # Wake word only, prompt user for command
                        print(Fore.CYAN + "🤖 V.O.I.D.: I'm listening. What would you like me to do on your phone?")
                        self.speak_feedback("I am listening.")
                        cmd_part = self.listen_and_transcribe_once()

                    if cmd_part:
                        self.process_command_text(cmd_part)
                else:
                    # If direct command mode or high confidence phone action uttered
                    parsed = self.parser.parse(transcript)
                    if parsed.intent_type != IntentType.UNKNOWN and parsed.confidence >= 0.90:
                        print(Fore.BLUE + f"\nDirect Command Recognized: '{transcript}'")
                        self.process_command_text(transcript)

            except KeyboardInterrupt:
                print(Fore.RED + "\n🛑 Voice Listener stopped by user.")
                break
            except Exception as e:
                print(Fore.RED + f"⚠️ Voice loop error: {e}")
                time.sleep(1.0)

        self._running = False

    def start_background(self):
        """Start the voice listener in a background daemon thread."""
        if not self._running:
            self._thread = threading.Thread(target=self.run_continuous_loop, daemon=True)
            self._thread.start()

    def stop(self):
        """Stop the continuous loop."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)


# Global singleton instance
phone_voice_listener = PhoneVoiceListener()
