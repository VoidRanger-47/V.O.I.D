#!/usr/bin/env python3
"""
V.O.I.D. — Voice-Controlled Android Phone Assistant.
Listens for the wake word "Void" (or accepts interactive text input)
and controls your connected Android phone via ADB.

Usage:
  # 1. Run live voice assistant (Mic + Wake word "Void"):
  python run_phone_assistant.py --voice

  # 2. Run interactive text prompt:
  python run_phone_assistant.py --text
"""

import argparse
import sys
import os
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from void_phone.adb_bridge import adb_bridge
from void_phone.phone_controller import phone_controller
from void_phone.intent_parser import intent_parser
from void_phone.voice_listener import phone_voice_listener

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True, wrap=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = RED = BLUE = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def run_text_prompt():
    print(Fore.CYAN + Style.BRIGHT + """
  ================================================================
    V.O.I.D. — ANDROID PHONE TEXT COMMAND INTERFACE
  ================================================================
  Type any natural language command (e.g. 'unlock my phone',
  'open JioCinema', 'call mom', 'volume up', 'status', 'exit').
    """)

    summary = phone_controller.get_status_summary()
    if summary.get("connected"):
        print(Fore.GREEN + f"✅ Connected: {summary.get('model')} ({summary.get('serial')}) | Battery: {summary.get('battery_level')}\n")
    else:
        print(Fore.YELLOW + "⚠️ Note: No phone currently connected. Connect USB or run 'python test_connection.py --connect <ip>:5555'.\n")

    while True:
        try:
            cmd = input(Fore.WHITE + "👤 You: ").strip()
            if not cmd:
                continue
            if cmd.lower() in ["exit", "quit", "q", "bye"]:
                print(Fore.GREEN + "Goodbye!")
                break

            phone_voice_listener.process_command_text(cmd)
            print()
        except KeyboardInterrupt:
            print(Fore.RED + "\nSession closed.")
            break


def main():
    parser = argparse.ArgumentParser(description="V.O.I.D. Android Phone Voice Assistant")
    parser.add_argument("--voice", "-v", action="store_true", help="Launch live microphone continuous voice loop")
    parser.add_argument("--text", "-t", action="store_true", help="Launch interactive text command interface")

    args = parser.parse_args()

    # Default to voice mode if specified, otherwise text mode if no mic or default
    if args.voice:
        phone_voice_listener.run_continuous_loop()
    elif args.text:
        run_text_prompt()
    else:
        # If neither flag passed, default to voice if microphone available, else text prompt
        print(Fore.CYAN + "Choose mode:")
        print("  1. 🎤 Voice Mode (Microphone + Wake Word 'Void')")
        print("  2. ⌨️  Text Mode (Interactive Command Prompt)")
        choice = input("Select [1/2] (default: 1): ").strip()
        if choice == "2":
            run_text_prompt()
        else:
            phone_voice_listener.run_continuous_loop()


if __name__ == "__main__":
    main()
