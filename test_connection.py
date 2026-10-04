#!/usr/bin/env python3
"""
V.O.I.D. — Android Phone ADB Connection & Feature Verification Tool.

Usage:
  # 1. Run full diagnostics & interactive test suite:
  python test_connection.py

  # 2. Test specific phone actions:
  python test_connection.py --action unlock
  python test_connection.py --action launch --app JioCinema
  python test_connection.py --action launch --app YouTube
  python test_connection.py --action launch --app WhatsApp
  python test_connection.py --action call --number "+1234567890"
  python test_connection.py --action screenshot

  # 3. Simulate a spoken voice command:
  python test_connection.py --simulate-voice "unlock my phone"
  python test_connection.py --simulate-voice "open JioCinema"
  python test_connection.py --simulate-voice "call mom"

  # 4. Wireless TCP/IP pairing & setup:
  python test_connection.py --tcpip 5555
  python test_connection.py --connect 192.168.1.100:5555
"""

import argparse
import sys
import os
import json
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from void_phone.adb_bridge import ADBBridge, adb_bridge
from void_phone.phone_controller import PhoneController, phone_controller
from void_phone.intent_parser import IntentParser, IntentType, intent_parser

try:
    import colorama
    from colorama import Fore, Style
    colorama.init(autoreset=True, wrap=True)
except ImportError:
    class Fore:
        CYAN = GREEN = YELLOW = RED = BLUE = MAGENTA = WHITE = RESET = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""
        CYAN = GREEN = YELLOW = RED = BLUE = MAGENTA = WHITE = ""
    class Style:
        BRIGHT = DIM = RESET_ALL = ""


def print_banner():
    print(Fore.CYAN + Style.BRIGHT + """
  ================================================================
    V.O.I.D. — ANDROID PHONE ADB BRIDGE VERIFICATION SUITE
  ================================================================
    """)


def run_diagnostics(bridge: ADBBridge, controller: PhoneController):
    print(Fore.CYAN + "\n[1/4] Checking ADB Environment...")
    print(f"  • ADB Executable Path: {bridge.adb_path}")
    
    code, stdout, stderr = bridge.run_adb_command(["version"])
    if code == 0:
        print(Fore.GREEN + f"  • ADB Daemon: Operational ({stdout.splitlines()[0] if stdout else 'OK'})")
    else:
        print(Fore.RED + f"  • ADB Daemon: Error starting daemon ({stderr or stdout})")

    print(Fore.CYAN + "\n[2/4] Scanning for Connected Android Devices...")
    devices = bridge.list_devices()
    if not devices:
        print(Fore.YELLOW + "  ⚠️ No Android devices detected via USB or TCP/IP.")
        print(Fore.WHITE + "     Troubleshooting:")
        print("     1. Ensure USB Debugging is ENABLED on your Android phone.")
        print("     2. Check the USB cable and connection mode (File Transfer/MTP).")
        print("     3. Look at your phone screen for 'Allow USB Debugging' prompt and tap 'Always allow'.")
        print("     4. For Xiaomi/MIUI/Oppo/Vivo/Realme, enable 'USB Debugging (Security settings)'.")
        print("     5. For wireless: run 'python test_connection.py --connect <phone_ip>:5555'\n")
        return False

    print(Fore.GREEN + f"  • Found {len(devices)} device(s):")
    for i, dev in enumerate(devices, 1):
        state_color = Fore.GREEN if dev.state == "device" else Fore.RED
        print(f"    {i}. Serial: {Fore.WHITE}{dev.serial} | Type: {dev.connection_type.upper()} | State: {state_color}{dev.state}{Fore.RESET} | Model: {dev.model}")

    active_serial = bridge.get_active_device_serial()
    print(Fore.CYAN + f"\n[3/4] Fetching Active Device Telemetry ({active_serial})...")
    info = bridge.get_device_info(active_serial)
    if info:
        print(f"  • Manufacturer & Model : {Fore.WHITE}{info.manufacturer} {info.model}")
        print(f"  • Android Version      : {Fore.WHITE}{info.android_version} ({info.sdk_version})")
        print(f"  • Battery Level        : {Fore.GREEN if (info.battery_level or 0) > 20 else Fore.RED}{info.battery_level}%")
        print(f"  • Screen Resolution    : {Fore.WHITE}{info.screen_resolution[0]}x{info.screen_resolution[1]}" if info.screen_resolution else "  • Screen Resolution: Unknown")
        print(f"  • Screen State         : {Fore.GREEN if info.is_screen_on else Fore.YELLOW}{'AWAKE / ON' if info.is_screen_on else 'ASLEEP / OFF'}")
        if info.ip_address:
            print(f"  • Phone IP (wlan0)     : {Fore.CYAN}{info.ip_address}")

    print(Fore.CYAN + "\n[4/4] Connection Verification Status:")
    if bridge.is_connected(active_serial):
        print(Fore.GREEN + Style.BRIGHT + "  ✅ PC-to-Phone ADB Bridge is FULLY OPERATIONAL!\n")
        return True
    else:
        print(Fore.RED + "  ❌ Device state is unauthorized or offline. Please accept the prompt on your phone screen.\n")
        return False


def run_interactive_menu(bridge: ADBBridge, controller: PhoneController):
    while True:
        print(Fore.CYAN + """
  Interactive Test Menu:
  ---------------------
  1. 🔓 Test Unlock Phone (Wake + Swipe + PIN)
  2. 🔒 Test Lock / Screen Off
  3. 🚀 Test Launch App (e.g. JioCinema, YouTube, WhatsApp)
  4. 📞 Test Phone Call / Dialer
  5. 🔊 Test Volume Up (+2 steps)
  6. 🔉 Test Volume Down (-2 steps)
  7. ⏯️  Test Media Play/Pause
  8. 🏠 Test Navigate Home
  9. 📸 Test Take Screenshot
  10. 🎤 Test Voice Command Simulation
  11. 📶 Setup Wireless ADB (TCP/IP)
  12. 🔄 Refresh Diagnostics
  0. ❌ Exit
        """)
        choice = input(Fore.WHITE + "Select an option [0-12]: ").strip()

        if choice == "0":
            print(Fore.GREEN + "Goodbye!")
            break
        elif choice == "1":
            pin = input("Enter PIN (press Enter for default from config): ").strip() or None
            res = controller.unlock(pin=pin)
            print(Fore.GREEN + f"Result: {res}")
        elif choice == "2":
            res = controller.lock_screen()
            print(Fore.GREEN + f"Result: {res}")
        elif choice == "3":
            app = input("Enter app name (e.g. JioCinema, YouTube, WhatsApp, Camera): ").strip()
            if app:
                res = controller.launch_app(app)
                print(Fore.GREEN + f"Result: {res}")
        elif choice == "4":
            target = input("Enter contact name or phone number: ").strip()
            if target:
                res = controller.call_contact(target, direct_call=True)
                print(Fore.GREEN + f"Result: {res}")
        elif choice == "5":
            res = controller.volume_up(2)
            print(Fore.GREEN + f"Result: {res}")
        elif choice == "6":
            res = controller.volume_down(2)
            print(Fore.GREEN + f"Result: {res}")
        elif choice == "7":
            res = controller.media_play_pause()
            print(Fore.GREEN + f"Result: {res}")
        elif choice == "8":
            res = controller.navigate_home()
            print(Fore.GREEN + f"Result: {res}")
        elif choice == "9":
            success, msg = controller.take_screenshot()
            print(Fore.GREEN if success else Fore.RED + f"Result: {msg}")
        elif choice == "10":
            phrase = input("Enter simulated voice command (e.g. 'Void, open JioCinema'): ").strip()
            if phrase:
                intent = intent_parser.parse(phrase)
                print(Fore.BLUE + f"Parsed Intent: {intent.intent_type.value} | Params: {intent.parameters}")
                res = intent.execute(controller)
                print(Fore.GREEN + f"Execution Result: {res}")
        elif choice == "11":
            port = input("Enter port [5555]: ").strip() or "5555"
            ok, msg = bridge.enable_tcpip_mode(int(port))
            print(Fore.GREEN if ok else Fore.RED + msg)
            if ok:
                info = bridge.get_device_info()
                if info and info.ip_address:
                    print(Fore.CYAN + f"Now disconnect USB and run: python test_connection.py --connect {info.ip_address}:{port}")
        elif choice == "12":
            run_diagnostics(bridge, controller)
        else:
            print(Fore.RED + "Invalid option.")


def main():
    parser = argparse.ArgumentParser(description="V.O.I.D. Android Phone ADB Bridge Test Suite")
    parser.add_argument("--diagnostics", "-d", action="store_true", help="Run connection diagnostics and exit")
    parser.add_argument("--action", "-a", type=str, help="Specific action: unlock, lock, launch, call, volume_up, volume_down, mute, home, back, recents, screenshot, status")
    parser.add_argument("--app", type=str, help="App name or package for --action launch")
    parser.add_argument("--number", type=str, help="Phone number or contact for --action call")
    parser.add_argument("--pin", type=str, help="PIN for --action unlock")
    parser.add_argument("--connect", type=str, help="Connect to wireless ADB (e.g. 192.168.1.100:5555)")
    parser.add_argument("--disconnect", type=str, nargs="?", const="", help="Disconnect from wireless ADB")
    parser.add_argument("--tcpip", type=int, nargs="?", const=5555, help="Enable TCP/IP mode on USB device")
    parser.add_argument("--shell", type=str, help="Execute raw ADB shell command")
    parser.add_argument("--simulate-voice", "-v", type=str, help="Simulate a spoken voice command string")

    args = parser.parse_args()
    print_banner()

    bridge = adb_bridge
    controller = phone_controller

    # Handle Wireless Connect/Disconnect/TCP-IP first
    if args.connect:
        if ":" in args.connect:
            host, port = args.connect.split(":", 1)
            ok, msg = bridge.connect_tcp(host, int(port))
        else:
            ok, msg = bridge.connect_tcp(args.connect, 5555)
        print(Fore.GREEN if ok else Fore.RED + msg)
        return

    if args.disconnect is not None:
        ok, msg = bridge.disconnect_tcp(args.disconnect if args.disconnect else None)
        print(Fore.GREEN if ok else Fore.RED + msg)
        return

    if args.tcpip:
        ok, msg = bridge.enable_tcpip_mode(args.tcpip)
        print(Fore.GREEN if ok else Fore.RED + msg)
        return

    if args.shell:
        code, out, err = bridge.shell(args.shell)
        print(out or err or f"Exit code: {code}")
        return

    if args.simulate_voice:
        print(Fore.YELLOW + f"🎤 Spoken Input: \"{args.simulate_voice}\"")
        intent = intent_parser.parse(args.simulate_voice)
        print(Fore.BLUE + f"🎯 Identified Intent: {intent.intent_type.value} (conf={intent.confidence:.2f}) | Params: {intent.parameters}")
        res = intent.execute(controller)
        print(Fore.GREEN + f"📱 Result: {res}")
        return

    if args.action:
        action = args.action.lower()
        if action == "unlock":
            print(controller.unlock(pin=args.pin))
        elif action == "lock":
            print(controller.lock_screen())
        elif action in ["launch", "open"]:
            if not args.app:
                print(Fore.RED + "Error: --app is required for launch action (e.g. --app JioCinema)")
            else:
                print(controller.launch_app(args.app))
        elif action in ["call", "dial"]:
            if not args.number:
                print(Fore.RED + "Error: --number is required for call action (e.g. --number 1234567890)")
            else:
                print(controller.call_contact(args.number, direct_call=(action == "call")))
        elif action == "volume_up":
            print(controller.volume_up())
        elif action == "volume_down":
            print(controller.volume_down())
        elif action == "mute":
            print(controller.volume_mute())
        elif action == "home":
            print(controller.navigate_home())
        elif action == "back":
            print(controller.navigate_back())
        elif action == "recents":
            print(controller.navigate_recents())
        elif action == "screenshot":
            ok, msg = controller.take_screenshot()
            print(msg)
        elif action == "status":
            info = controller.get_status_summary()
            print(json.dumps(info, indent=2))
        else:
            print(Fore.RED + f"Unknown action '{args.action}'.")
        return

    # Default flow: Run diagnostics and open interactive menu if not flag-only
    is_ok = run_diagnostics(bridge, controller)
    if not args.diagnostics:
        run_interactive_menu(bridge, controller)


if __name__ == "__main__":
    main()
