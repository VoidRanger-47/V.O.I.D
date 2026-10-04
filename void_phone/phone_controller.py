"""
Phone Controller for V.O.I.D.
Provides high-level automation methods to control an Android smartphone via ADB:
unlocking, app launching (JioCinema, WhatsApp, YouTube, etc.), phone calling,
volume/media controls, navigation, and device telemetry.
"""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from void_phone.adb_bridge import ADBBridge, adb_bridge


class PhoneController:
    """
    High-level Android phone automation controller.
    """
    _instance: Optional[PhoneController] = None

    def __init__(self, bridge: Optional[ADBBridge] = None, config_path: Optional[str] = None):
        self.bridge = bridge or adb_bridge
        self.config_path = config_path or os.path.join(os.path.dirname(__file__), "phone_config.json")
        self.config = self._load_config()

    @classmethod
    def get_instance(cls, bridge: Optional[ADBBridge] = None) -> PhoneController:
        if cls._instance is None:
            cls._instance = PhoneController(bridge)
        return cls._instance

    def _load_config(self) -> Dict[str, Any]:
        """Load phone settings, package mappings, and contacts."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"[PhoneController] Config load error: {e}")
        return {
            "unlock": {"default_pin": "1234", "swipe_start_y_percent": 0.85, "swipe_end_y_percent": 0.20, "swipe_duration_ms": 300},
            "apps": {},
            "contacts": {}
        }

    def reload_config(self):
        """Reload configuration from disk."""
        self.config = self._load_config()

    # -------------------------------------------------------------------------
    # Screen & Unlock Automation
    # -------------------------------------------------------------------------

    def is_screen_on(self, serial: Optional[str] = None) -> bool:
        """Check if the phone screen is currently awake."""
        _, out, _ = self.bridge.shell("dumpsys display | grep mHoldingDisplaySuspendBlocker", serial=serial)
        if "true" in out.lower():
            return True
        _, out2, _ = self.bridge.shell("dumpsys power | grep 'Display Power: state='", serial=serial)
        return "ON" in out2.upper()

    def wake_screen(self, serial: Optional[str] = None) -> bool:
        """Turn on the screen if it is asleep."""
        if not self.is_screen_on(serial=serial):
            # KEYCODE_WAKEUP = 224, fallback to KEYCODE_POWER = 26
            self.bridge.shell("input keyevent 224", serial=serial)
            time.sleep(0.3)
            if not self.is_screen_on(serial=serial):
                self.bridge.shell("input keyevent 26", serial=serial)
            time.sleep(0.3)
            return True
        return False

    def lock_screen(self, serial: Optional[str] = None) -> str:
        """Turn off the screen / lock the device."""
        if self.is_screen_on(serial=serial):
            self.bridge.shell("input keyevent 26", serial=serial)  # KEYCODE_POWER
            return "🔒 Phone screen turned off."
        return "Phone screen is already off."

    def swipe_up(self, serial: Optional[str] = None) -> None:
        """Perform a bottom-to-top swipe gesture on the lockscreen to display the PIN pad."""
        width, height = self.bridge.get_display_size(serial=serial)
        cfg_unlock = self.config.get("unlock", {})
        start_pct = cfg_unlock.get("swipe_start_y_percent", 0.85)
        end_pct = cfg_unlock.get("swipe_end_y_percent", 0.20)
        duration_ms = cfg_unlock.get("swipe_duration_ms", 300)

        x = width // 2
        y1 = int(height * start_pct)
        y2 = int(height * end_pct)

        self.bridge.shell(f"input swipe {x} {y1} {x} {y2} {duration_ms}", serial=serial)

    def input_pin(self, pin: str, serial: Optional[str] = None) -> None:
        """Input numeric PIN and submit with Enter."""
        clean_pin = re.sub(r"[^\d]", "", str(pin))
        if clean_pin:
            self.bridge.shell(f"input text {clean_pin}", serial=serial)
            time.sleep(0.2)
            self.bridge.shell("input keyevent 66", serial=serial)  # KEYCODE_ENTER

    def unlock(self, pin: Optional[str] = None, serial: Optional[str] = None) -> str:
        """
        Wakes the phone, swipes up the lockscreen, and enters the PIN.
        """
        if not self.bridge.is_connected(serial=serial):
            return "❌ Cannot unlock: No Android phone connected."

        # 1. Wake screen
        woke = self.wake_screen(serial=serial)
        time.sleep(0.4)

        # 2. Swipe up to reveal PIN input
        self.swipe_up(serial=serial)
        time.sleep(0.4)

        # 3. Enter PIN
        pin_to_use = pin or self.config.get("unlock", {}).get("default_pin", "1234")
        if pin_to_use:
            self.input_pin(pin_to_use, serial=serial)
            return f"🔓 Phone unlocked using PIN."
        return "📱 Screen awakened and swiped up."

    # -------------------------------------------------------------------------
    # Application Launching
    # -------------------------------------------------------------------------

    def get_live_device_packages(self, serial: Optional[str] = None) -> List[str]:
        """
        Fetch all installed package IDs on the connected Android device.
        """
        if not self.bridge.is_connected(serial=serial):
            return []
        packages = []
        try:
            code, out, _ = self.bridge.shell("pm list packages", serial=serial)
            if code == 0 and out:
                for line in out.splitlines():
                    clean_line = line.strip()
                    if clean_line.startswith("package:"):
                        pkg = clean_line.replace("package:", "").strip()
                        if pkg:
                            packages.append(pkg)
        except Exception:
            pass
        return packages

    def resolve_app_package(self, app_name: str, serial: Optional[str] = None) -> Optional[str]:
        """
        Resolve a friendly app name (e.g. 'Instagram', 'Telegram', 'JioCinema', 'WhatsApp') to its Android package ID.
        """
        clean_name = app_name.strip().lower()
        clean_name = re.sub(r'^(?:open|launch|start|run)\s+', '', clean_name).strip()
        apps_map = self.config.get("apps", {})

        # 1. Exact match in config dictionary
        if clean_name in apps_map:
            return apps_map[clean_name]

        # 2. Match without spaces or punctuation
        condensed = re.sub(r"[\s\-_]+", "", clean_name)
        for name, pkg in apps_map.items():
            if re.sub(r"[\s\-_]+", "", name) == condensed:
                return pkg

        # 3. If input is already in package notation (e.g. com.example.app)
        if "." in clean_name and len(clean_name.split(".")) >= 2:
            return clean_name

        # 4. Search installed packages on the live device via Python
        live_pkgs = self.get_live_device_packages(serial=serial)
        if live_pkgs:
            # 4a. Check if condensed name matches package ending or segment
            for pkg in live_pkgs:
                pkg_lower = pkg.lower()
                segments = pkg_lower.split(".")
                if condensed in segments or any(condensed == seg for seg in segments):
                    return pkg

            # 4b. Substring in package
            for pkg in live_pkgs:
                if condensed in pkg.lower():
                    return pkg

        return None

    def launch_app(self, app_name: str, serial: Optional[str] = None) -> str:
        """
        Launch an Android application by friendly name or package name.
        Uses monkey launcher to start the default launcher activity reliably.
        """
        if not self.bridge.is_connected(serial=serial):
            return "❌ Cannot launch app: No Android phone connected."

        # Ensure screen is unlocked/awake
        self.wake_screen(serial=serial)

        pkg = self.resolve_app_package(app_name, serial=serial)
        if not pkg:
            return f"❌ Could not find package for '{app_name}'. Please verify the app name or add it to phone_config.json."

        # Launch app via monkey (starts default category.LAUNCHER activity)
        code, stdout, stderr = self.bridge.shell(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1", serial=serial)
        if "Events injected: 1" in stdout or code == 0:
            return f"🚀 Launched {app_name} (`{pkg}`) on your phone."

        # Fallback to am start
        code2, stdout2, stderr2 = self.bridge.shell(f"am start -a android.intent.action.MAIN -c android.intent.category.LAUNCHER {pkg}", serial=serial)
        if code2 == 0 and "Error" not in (stdout2 + stderr2):
            return f"🚀 Launched {app_name} (`{pkg}`) on your phone."

        return f"⚠️ Attempted to launch {app_name} ({pkg}), but received: {stdout or stderr or stdout2 or stderr2}"

    def force_stop_app(self, app_name: str, serial: Optional[str] = None) -> str:
        """Force stop a running application."""
        pkg = self.resolve_app_package(app_name, serial=serial)
        if not pkg:
            return f"❌ Unknown app '{app_name}'"

        self.bridge.shell(f"am force-stop {pkg}", serial=serial)
        return f"🛑 Closed {app_name} ({pkg})."

    # -------------------------------------------------------------------------
    # Calling & Messaging
    # -------------------------------------------------------------------------

    def resolve_contact_number(self, target: str) -> Tuple[Optional[str], str]:
        """
        Resolve a name or phone number string to a normalized phone number.
        Returns (phone_number, contact_display_name).
        """
        clean_target = target.strip().lower()
        contacts = self.config.get("contacts", {})

        # 1. Direct contact lookup
        if clean_target in contacts:
            return contacts[clean_target], target.capitalize()

        # 2. Fuzzy contact lookup
        for name, num in contacts.items():
            if name in clean_target or clean_target in name:
                return num, name.capitalize()

        # 3. Check if target is a phone number
        digits_only = re.sub(r"[^\d+]", "", target)
        if len(digits_only) >= 3:
            return digits_only, target

        return None, target

    def call_contact(self, contact_or_number: str, direct_call: bool = True, serial: Optional[str] = None) -> str:
        """
        Initiate a phone call to a contact name or phone number.
        If direct_call is True, calls immediately via ACTION_CALL; otherwise opens dialer via ACTION_DIAL.
        """
        if not self.bridge.is_connected(serial=serial):
            return "❌ Cannot place call: No Android phone connected."

        self.wake_screen(serial=serial)

        phone_num, display_name = self.resolve_contact_number(contact_or_number)
        if not phone_num:
            return f"❌ Could not resolve contact or phone number for '{contact_or_number}'."

        action = "android.intent.action.CALL" if direct_call else "android.intent.action.DIAL"
        code, stdout, stderr = self.bridge.shell(f"am start -a {action} -d tel:{phone_num}", serial=serial)

        if code == 0 and "Error" not in (stdout + stderr):
            verb = "Calling" if direct_call else "Opened dialer for"
            return f"📞 {verb} {display_name} ({phone_num})..."

        # If ACTION_CALL fails (e.g. missing CALL_PHONE permission for ADB), fallback to ACTION_DIAL
        if direct_call:
            code2, stdout2, stderr2 = self.bridge.shell(f"am start -a android.intent.action.DIAL -d tel:{phone_num}", serial=serial)
            if code2 == 0:
                return f"📞 Dialing {display_name} ({phone_num}) on your phone screen."

        return f"⚠️ Call attempt failed: {stdout or stderr}"

    def send_sms(self, contact_or_number: str, message: str, serial: Optional[str] = None) -> str:
        """Open SMS app with recipient and message pre-filled."""
        if not self.bridge.is_connected(serial=serial):
            return "❌ Cannot send message: No Android phone connected."

        self.wake_screen(serial=serial)
        phone_num, display_name = self.resolve_contact_number(contact_or_number)
        if not phone_num:
            return f"❌ Unknown contact '{contact_or_number}'."

        escaped_msg = message.replace('"', '\\"')
        self.bridge.shell(f'am start -a android.intent.action.SENDTO -d sms:{phone_num} --es sms_body "{escaped_msg}"', serial=serial)
        return f"💬 Drafted SMS to {display_name} ({phone_num}): '{message}'"

    # -------------------------------------------------------------------------
    # Hardware & Media Controls
    # -------------------------------------------------------------------------

    def volume_up(self, steps: int = 1, serial: Optional[str] = None) -> str:
        """Increase phone media/ring volume."""
        for _ in range(max(1, min(steps, 10))):
            self.bridge.shell("input keyevent 24", serial=serial)  # KEYCODE_VOLUME_UP
        return f"🔊 Volume increased by {steps} step(s)."

    def volume_down(self, steps: int = 1, serial: Optional[str] = None) -> str:
        """Decrease phone media/ring volume."""
        for _ in range(max(1, min(steps, 10))):
            self.bridge.shell("input keyevent 25", serial=serial)  # KEYCODE_VOLUME_DOWN
        return f"🔉 Volume decreased by {steps} step(s)."

    def volume_mute(self, serial: Optional[str] = None) -> str:
        """Mute / unmute phone volume."""
        self.bridge.shell("input keyevent 164", serial=serial)  # KEYCODE_VOLUME_MUTE
        return "🔇 Volume muted / toggled."

    def media_play_pause(self, serial: Optional[str] = None) -> str:
        """Toggle media play / pause on the phone."""
        self.bridge.shell("input keyevent 85", serial=serial)  # KEYCODE_MEDIA_PLAY_PAUSE
        return "⏯️ Media play/pause toggled."

    def media_next(self, serial: Optional[str] = None) -> str:
        """Skip to the next media track."""
        self.bridge.shell("input keyevent 87", serial=serial)  # KEYCODE_MEDIA_NEXT
        return "⏭️ Skipped to next track."

    def media_previous(self, serial: Optional[str] = None) -> str:
        """Return to previous media track."""
        self.bridge.shell("input keyevent 88", serial=serial)  # KEYCODE_MEDIA_PREVIOUS
        return "⏮️ Returned to previous track."

    # -------------------------------------------------------------------------
    # Navigation & UI Controls
    # -------------------------------------------------------------------------

    def navigate_home(self, serial: Optional[str] = None) -> str:
        """Press the Home button."""
        self.bridge.shell("input keyevent 3", serial=serial)  # KEYCODE_HOME
        return "🏠 Returned to Home screen."

    def navigate_back(self, serial: Optional[str] = None) -> str:
        """Press the Back button."""
        self.bridge.shell("input keyevent 4", serial=serial)  # KEYCODE_BACK
        return "◀️ Pressed Back."

    def navigate_recents(self, serial: Optional[str] = None) -> str:
        """Open Recent Apps overview."""
        self.bridge.shell("input keyevent 187", serial=serial)  # KEYCODE_APP_SWITCH
        return "📱 Opened Recent Apps."

    def open_notifications(self, serial: Optional[str] = None) -> str:
        """Pull down the notification shade."""
        self.bridge.shell("cmd statusbar expand-notifications", serial=serial)
        return "🔔 Opened notification panel."

    def take_screenshot(self, local_dest: Optional[str] = None, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Capture phone screen and pull to local destination."""
        remote_path = "/sdcard/void_screenshot.png"
        self.bridge.shell(f"screencap -p {remote_path}", serial=serial)

        if not local_dest:
            local_dest = os.path.join(os.path.dirname(os.path.dirname(__file__)), "void_screenshot.png")

        code, stdout, stderr = self.bridge.run_adb_command(["pull", remote_path, local_dest])
        if code == 0 and os.path.exists(local_dest):
            self.bridge.shell(f"rm {remote_path}", serial=serial)
            return True, f"📸 Screenshot saved to {local_dest}"
        return False, f"❌ Screenshot capture failed: {stdout or stderr}"

    def get_status_summary(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """Return a structured dictionary of phone status and hardware metrics."""
        info = self.bridge.get_device_info(serial=serial)
        if not info:
            return {
                "connected": False,
                "status": "No Android device connected via ADB."
            }

        return {
            "connected": info.state == "device",
            "serial": info.serial,
            "state": info.state,
            "connection_type": info.connection_type,
            "model": info.model,
            "manufacturer": info.manufacturer,
            "android_version": info.android_version,
            "sdk_version": info.sdk_version,
            "battery_level": f"{info.battery_level}%" if info.battery_level is not None else "Unknown",
            "screen_on": info.is_screen_on,
            "resolution": f"{info.screen_resolution[0]}x{info.screen_resolution[1]}" if info.screen_resolution else "Unknown",
            "ip_address": info.ip_address or "Unknown"
        }


# Global singleton instance
phone_controller = PhoneController.get_instance()
