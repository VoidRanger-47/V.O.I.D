"""
Intent Parser for V.O.I.D. Phone Control.
Parses natural language / transcribed voice commands into structured phone automation intents.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Optional

from void_phone.phone_controller import PhoneController, phone_controller


class IntentType(str, Enum):
    UNLOCK = "UNLOCK"
    LOCK = "LOCK"
    LAUNCH_APP = "LAUNCH_APP"
    CLOSE_APP = "CLOSE_APP"
    CALL = "CALL"
    DIAL = "DIAL"
    SEND_SMS = "SEND_SMS"
    VOLUME_UP = "VOLUME_UP"
    VOLUME_DOWN = "VOLUME_DOWN"
    VOLUME_MUTE = "VOLUME_MUTE"
    MEDIA_PLAY_PAUSE = "MEDIA_PLAY_PAUSE"
    MEDIA_NEXT = "MEDIA_NEXT"
    MEDIA_PREV = "MEDIA_PREV"
    NAV_HOME = "NAV_HOME"
    NAV_BACK = "NAV_BACK"
    NAV_RECENTS = "NAV_RECENTS"
    NOTIFICATIONS = "NOTIFICATIONS"
    TAKE_SCREENSHOT = "TAKE_SCREENSHOT"
    STATUS = "STATUS"
    CUSTOM_SHELL = "CUSTOM_SHELL"
    UNKNOWN = "UNKNOWN"


@dataclass
class PhoneIntent:
    intent_type: IntentType
    confidence: float
    raw_text: str
    parameters: Dict[str, Any] = field(default_factory=dict)

    def execute(self, controller: Optional[PhoneController] = None) -> str:
        """Execute this intent on the provided or default PhoneController."""
        ctrl = controller or phone_controller

        if self.intent_type == IntentType.UNLOCK:
            pin = self.parameters.get("pin")
            return ctrl.unlock(pin=pin)

        elif self.intent_type == IntentType.LOCK:
            return ctrl.lock_screen()

        elif self.intent_type == IntentType.LAUNCH_APP:
            app = self.parameters.get("app_name", "")
            return ctrl.launch_app(app)

        elif self.intent_type == IntentType.CLOSE_APP:
            app = self.parameters.get("app_name", "")
            return ctrl.force_stop_app(app)

        elif self.intent_type == IntentType.CALL:
            target = self.parameters.get("target", "")
            return ctrl.call_contact(target, direct_call=True)

        elif self.intent_type == IntentType.DIAL:
            target = self.parameters.get("target", "")
            return ctrl.call_contact(target, direct_call=False)

        elif self.intent_type == IntentType.SEND_SMS:
            target = self.parameters.get("target", "")
            message = self.parameters.get("message", "")
            return ctrl.send_sms(target, message)

        elif self.intent_type == IntentType.VOLUME_UP:
            steps = self.parameters.get("steps", 1)
            return ctrl.volume_up(steps=steps)

        elif self.intent_type == IntentType.VOLUME_DOWN:
            steps = self.parameters.get("steps", 1)
            return ctrl.volume_down(steps=steps)

        elif self.intent_type == IntentType.VOLUME_MUTE:
            return ctrl.volume_mute()

        elif self.intent_type == IntentType.MEDIA_PLAY_PAUSE:
            return ctrl.media_play_pause()

        elif self.intent_type == IntentType.MEDIA_NEXT:
            return ctrl.media_next()

        elif self.intent_type == IntentType.MEDIA_PREV:
            return ctrl.media_previous()

        elif self.intent_type == IntentType.NAV_HOME:
            return ctrl.navigate_home()

        elif self.intent_type == IntentType.NAV_BACK:
            return ctrl.navigate_back()

        elif self.intent_type == IntentType.NAV_RECENTS:
            return ctrl.navigate_recents()

        elif self.intent_type == IntentType.NOTIFICATIONS:
            return ctrl.open_notifications()

        elif self.intent_type == IntentType.TAKE_SCREENSHOT:
            success, msg = ctrl.take_screenshot()
            return msg

        elif self.intent_type == IntentType.STATUS:
            summary = ctrl.get_status_summary()
            if not summary.get("connected"):
                return "📱 No Android phone connected via ADB."
            return (
                f"📱 Phone Status: {summary.get('model')} ({summary.get('manufacturer')})\n"
                f"🔋 Battery: {summary.get('battery_level')} | Screen: {'ON' if summary.get('screen_on') else 'OFF'}\n"
                f"📶 Connection: {summary.get('connection_type').upper()} ({summary.get('serial')})\n"
                f"🤖 OS: {summary.get('android_version')} ({summary.get('sdk_version')})"
            )

        elif self.intent_type == IntentType.CUSTOM_SHELL:
            cmd = self.parameters.get("command", "")
            code, out, err = ctrl.bridge.shell(cmd)
            return out or err or f"Exit code {code}"

        return f"❓ Could not map command '{self.raw_text}' to a phone action."


class IntentParser:
    """
    Parses speech transcripts or text into structured PhoneIntent objects.
    """
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path

    def parse(self, text: str) -> PhoneIntent:
        """
        Extract intent and parameters from natural language command.
        """
        raw = text.strip()
        cleaned = re.sub(r"^(void|hey void|ok void|hello void)[,\s]*", "", raw, flags=re.IGNORECASE).strip()
        lower = cleaned.lower()

        if not lower:
            return PhoneIntent(IntentType.UNKNOWN, 0.0, raw)

        # 1. UNLOCK PHONE
        # e.g., "unlock my phone", "unlock phone with pin 1234", "wake up and unlock"
        if re.search(r"\b(unlock|open lock|unlock my phone|unlock device)\b", lower):
            pin_match = re.search(r"(?:pin|code|password)\s+(?:is\s+)?(\d+)", lower)
            pin = pin_match.group(1) if pin_match else None
            return PhoneIntent(IntentType.UNLOCK, 0.95, raw, {"pin": pin})

        # 2. LOCK PHONE
        # e.g., "lock my phone", "turn off screen", "lock phone", "sleep phone"
        if re.search(r"\b(lock|turn off screen|screen off|sleep phone|lock my phone)\b", lower):
            return PhoneIntent(IntentType.LOCK, 0.95, raw)

        # 3. CALL CONTACT / NUMBER
        # e.g., "call mom", "call 1234567890", "make a call to dad", "dial john"
        call_match = re.search(r"\b(?:call|phone|dial|make a call to)\s+([\w\s+]+)", lower)
        if call_match:
            target = call_match.group(1).strip()
            # Filter out non-target trailing phrases
            target = re.sub(r"\b(on my phone|please|now)\b", "", target).strip()
            is_dial = "dial" in lower and "call" not in lower
            intent_type = IntentType.DIAL if is_dial else IntentType.CALL
            return PhoneIntent(intent_type, 0.95, raw, {"target": target})

        # 4. LAUNCH APP
        # e.g., "open JioCinema", "launch WhatsApp", "start YouTube", "open camera", "open insta on phone"
        app_match = re.search(r"\b(?:open|launch|start|run|switch to)\s+([a-zA-Z0-9\s._]+)", lower)
        if app_match:
            app_name = app_match.group(1).strip()
            # Clean trailing words
            app_name = re.sub(r"\b(app|application|on my phone|please|on phone|in phone|on mobile|on android)\b", "", app_name).strip()
            if app_name and app_name not in ["the phone", "phone screen", "system"]:
                return PhoneIntent(IntentType.LAUNCH_APP, 0.95, raw, {"app_name": app_name})

        # 5. CLOSE APP
        # e.g., "close WhatsApp", "stop JioCinema", "quit YouTube"
        close_match = re.search(r"\b(?:close|stop|quit|force stop|kill)\s+([a-zA-Z0-9\s._]+)", lower)
        if close_match:
            app_name = close_match.group(1).strip()
            app_name = re.sub(r"\b(app|application|on my phone|please)\b", "", app_name).strip()
            if app_name and app_name not in ["phone", "screen", "system"]:
                return PhoneIntent(IntentType.CLOSE_APP, 0.90, raw, {"app_name": app_name})

        # 6. SEND SMS
        # e.g., "send message to mom I will be late", "text John hello there"
        sms_match = re.search(r"\b(?:text|message|send sms to|send message to)\s+([\w]+)\s+(?:saying\s+)?(.+)", lower)
        if sms_match:
            target = sms_match.group(1).strip()
            msg = sms_match.group(2).strip()
            return PhoneIntent(IntentType.SEND_SMS, 0.90, raw, {"target": target, "message": msg})

        # 7. VOLUME CONTROLS
        if re.search(r"\b(volume up|increase volume|louder|turn up the volume|raise volume)\b", lower):
            steps_match = re.search(r"(\d+)\s*(?:steps|times|points)", lower)
            steps = int(steps_match.group(1)) if steps_match else 2
            return PhoneIntent(IntentType.VOLUME_UP, 0.95, raw, {"steps": steps})

        if re.search(r"\b(volume down|decrease volume|lower volume|turn down the volume|quieter)\b", lower):
            steps_match = re.search(r"(\d+)\s*(?:steps|times|points)", lower)
            steps = int(steps_match.group(1)) if steps_match else 2
            return PhoneIntent(IntentType.VOLUME_DOWN, 0.95, raw, {"steps": steps})

        if re.search(r"\b(mute|unmute|silence phone|toggle mute)\b", lower):
            return PhoneIntent(IntentType.VOLUME_MUTE, 0.90, raw)

        # 8. MEDIA CONTROLS
        if re.search(r"\b(play|pause|resume|toggle media|play music|pause music|stop music)\b", lower):
            return PhoneIntent(IntentType.MEDIA_PLAY_PAUSE, 0.90, raw)

        if re.search(r"\b(next song|next track|skip song|next track please|skip)\b", lower):
            return PhoneIntent(IntentType.MEDIA_NEXT, 0.90, raw)

        if re.search(r"\b(previous song|previous track|last song|play previous)\b", lower):
            return PhoneIntent(IntentType.MEDIA_PREV, 0.90, raw)

        # 9. NAVIGATION
        if re.search(r"\b(go home|home screen|home button|go to home)\b", lower):
            return PhoneIntent(IntentType.NAV_HOME, 0.95, raw)

        if re.search(r"\b(go back|back button|back)\b", lower):
            return PhoneIntent(IntentType.NAV_BACK, 0.90, raw)

        if re.search(r"\b(recent apps|open recents|task manager|recent tasks)\b", lower):
            return PhoneIntent(IntentType.NAV_RECENTS, 0.90, raw)

        if re.search(r"\b(notifications|show notifications|open notifications|notification panel)\b", lower):
            return PhoneIntent(IntentType.NOTIFICATIONS, 0.90, raw)

        # 10. SCREENSHOT
        if re.search(r"\b(take screenshot|screenshot|capture screen|screen capture)\b", lower):
            return PhoneIntent(IntentType.TAKE_SCREENSHOT, 0.95, raw)

        # 11. PHONE STATUS & BATTERY
        if re.search(r"\b(phone status|battery|battery level|phone battery|device info)\b", lower):
            return PhoneIntent(IntentType.STATUS, 0.90, raw)

        # 12. CUSTOM SHELL
        if lower.startswith("adb shell ") or lower.startswith("shell "):
            cmd = re.sub(r"^(adb )?shell\s+", "", cleaned).strip()
            return PhoneIntent(IntentType.CUSTOM_SHELL, 0.99, raw, {"command": cmd})

        return PhoneIntent(IntentType.UNKNOWN, 0.2, raw)


# Global singleton instance
intent_parser = IntentParser()
