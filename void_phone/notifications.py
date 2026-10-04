# void_phone/notifications.py
"""
V.O.I.D. Mobile Remote Notification & Alert Engine.
Pushes real-time alerts, mission completion statuses, and toasts to connected Android devices
over USB or Wireless TCP/IP ADB.
"""

import logging
import shlex
from typing import Dict, Any, Optional
from void_phone.adb_bridge import ADBBridge
from core.event_bus import event_bus, SystemEvent

logger = logging.getLogger("VOID.PhoneNotifications")


class PhoneNotificationManager:
    """
    Manages push alerts, heads-up notifications, and toasts sent to the smartphone.
    """
    _instance: Optional['PhoneNotificationManager'] = None

    def __init__(self):
        self.bridge = ADBBridge.get_instance()
        self.auto_mission_alerts = True
        self._subscribe_events()

    @classmethod
    def get_instance(cls) -> 'PhoneNotificationManager':
        if cls._instance is None:
            cls._instance = PhoneNotificationManager()
        return cls._instance

    def _subscribe_events(self):
        """Subscribes to system events to relay mission/task milestones automatically."""
        try:
            event_bus.subscribe(SystemEvent.AGENT_TASK_FINISHED, self._on_agent_task_finished)
        except Exception as e:
            logger.debug(f"Event bus subscription notice: {e}")

    def _on_agent_task_finished(self, data: Dict[str, Any]):
        """Relays critical agent task completions if auto alerts are enabled."""
        if not self.auto_mission_alerts:
            return
        task_id = data.get("task_id", "")
        status = data.get("status", "SUCCESS")
        if status in ["SUCCESS", "COMPLETED", "FAILED"]:
            # Check if there is an active device
            code, out, _ = self.bridge.run_adb_command(["devices"])
            devices = [line for line in out.splitlines()[1:] if "\tdevice" in line]
            if devices:
                self.send_phone_notification(
                    title=f"V.O.I.D. Task {status}",
                    message=f"Task '{task_id[:16]}' completed with status: {status}."
                )

    def is_device_connected(self) -> bool:
        """Checks whether at least one Android device is connected and authorized."""
        code, out, _ = self.bridge.run_adb_command(["devices"])
        lines = out.splitlines()[1:]
        return any("\tdevice" in line for line in lines)

    def send_phone_notification(self, title: str, message: str, priority: str = "normal") -> Dict[str, Any]:
        """
        Pushes a heads-up notification to the Android device.
        Uses Android's 'cmd notification post' on modern Android, or Termux API broadcast fallback.
        """
        if not self.is_device_connected():
            return {
                "success": False,
                "error": "No Android device connected over ADB. Please connect via USB or Wi-Fi (adb connect <ip>:5555)."
            }

        clean_title = title.replace('"', '\\"').replace("'", "")
        clean_msg = message.replace('"', '\\"').replace("'", "")
        tag = "void_mission_alert"

        # 1. Primary Method: Android 11+ 'cmd notification post'
        # Syntax: cmd notification post [-S <style>] [-t <title>] <tag> <text>
        cmd1 = ["shell", "cmd", "notification", "post", "-S", "bigtext", "-t", clean_title, tag, clean_msg]
        code, out, err = self.bridge.run_adb_command(cmd1)
        if code == 0 and "error" not in out.lower() and "error" not in err.lower():
            logger.info(f"Notification pushed via cmd notification: {title}")
            return {"success": True, "method": "cmd_notification", "title": title, "message": message}

        # 2. Secondary Method: Termux:API broadcast
        termux_cmd = [
            "shell",
            f"termux-notification -t {shlex.quote(title)} -c {shlex.quote(message)} --vibrate 400"
        ]
        code, out, err = self.bridge.run_adb_command(termux_cmd)
        if code == 0 and "not found" not in err.lower():
            logger.info(f"Notification pushed via Termux API: {title}")
            return {"success": True, "method": "termux_api", "title": title, "message": message}

        # 3. Tertiary Method: Android Intent broadcast
        intent_cmd = [
            "shell", "am", "broadcast",
            "-a", "android.intent.action.VIEW",
            "--es", "title", clean_title,
            "--es", "message", clean_msg
        ]
        code, out, err = self.bridge.run_adb_command(intent_cmd)
        return {
            "success": code == 0,
            "method": "intent_broadcast",
            "title": title,
            "message": message,
            "output": out.strip()
        }

    def show_phone_toast(self, message: str) -> Dict[str, Any]:
        """Displays an instant toast message on the smartphone display."""
        if not self.is_device_connected():
            return {"success": False, "error": "No Android device connected."}

        clean_msg = message.replace('"', '\\"')
        # Try termux-toast
        cmd = ["shell", f"termux-toast {shlex.quote(message)} 2>/dev/null || true"]
        code, out, err = self.bridge.run_adb_command(cmd)

        # Trigger a short vibration to signal the user
        vibe_cmd = ["shell", "cmd", "vibrator", "vibrate", "150"]
        self.bridge.run_adb_command(vibe_cmd)

        return {"success": True, "toast": message}

    def send_mission_alert(
        self,
        mission_id: int,
        title: str,
        status: str,
        progress: int = 0,
        objective: str = ""
    ) -> Dict[str, Any]:
        """Pushes a structured mission milestone notification to the phone."""
        icon = "✅" if status == "COMPLETED" else "🚀" if status == "IN_PROGRESS" else "⚠️"
        alert_title = f"{icon} V.O.I.D. Mission #{mission_id}: {status}"
        alert_msg = f"{title} ({progress}%)\nObjective: {objective or 'Ongoing'}"
        return self.send_phone_notification(title=alert_title, message=alert_msg)


# Global Singleton Manager
phone_notifications = PhoneNotificationManager.get_instance()
