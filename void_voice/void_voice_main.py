# void_voice_main.py

import time
import json
import os

import numpy as np
import pyaudio
import colorama
from colorama import Fore, Style

from wakeword.detector import WakeWordEngine
from stt.transcriber import Ear
from tts.piper_engine import VoiceEngine
from brain.llm_interface import get_void_response

colorama.init(autoreset=True)

# Load Config
with open("config/config.json", "r") as f:
    CONFIG = json.load(f)

# Audio Constants
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
CHUNK = 1280

def main():
    print(Fore.CYAN + Style.BRIGHT + """
    =========================================
      V.O.I.D. - SYSTEM ONLINE
      Virtual Operator of Information & Development
    =========================================
    """)
    
    # 1. Initialize Modules
    wakeword = WakeWordEngine(CONFIG)
    ear = Ear(CONFIG)
    voice = VoiceEngine(CONFIG)

    # 2. Initialize PyAudio and open mic stream
    audio = pyaudio.PyAudio()
    mic_stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )

    print(Fore.GREEN + "✅ Systems Normal. Listening for Wake Word...")

    try:
        while True:
            # --- PHASE 1: Wake Word Detection ---
            data = mic_stream.read(CHUNK, exception_on_overflow=False)
            if wakeword.detect(data):
                print(Fore.YELLOW + "\n⚡ WAKE WORD DETECTED")
                
                # Pause Stream to release mic for STT
                mic_stream.stop_stream()
                
                # --- PHASE 2: Listen (STT) ---
                try:
                    user_text = ear.listen_and_transcribe()
                    print(Fore.WHITE + f"👤 User: {user_text}")

                    if "VOID STOP" in user_text.upper():
                        print(Fore.RED + "⛔ Sequence Aborted.")
                        voice.speak("Stopping systems.")
                    elif user_text:
                        # --- PHASE 3: Think (LLM) ---
                        print(Fore.BLUE + "🧠 Processing...")
                        start_t = time.time()
                        
                        response = get_void_response(user_text)
                        
                        proc_time = time.time() - start_t
                        print(Fore.CYAN + f"🤖 V.O.I.D. ({proc_time:.2f}s): {response}")

                        # --- PHASE 4: Speak (TTS) ---
                        voice.speak(response)
                    else:
                        print("No speech detected.")

                except Exception as e:
                    print(Fore.RED + f"Error during processing: {e}")

                # Resume Listening
                print(Fore.GREEN + "👂 Returning to Standby...")
                mic_stream.start_stream()

    except KeyboardInterrupt:
        print(Fore.RED + "\n🔴 System Shutdown.")
    finally:
        mic_stream.stop_stream()
        mic_stream.close()
        audio.terminate()

if __name__ == "__main__":
    main()