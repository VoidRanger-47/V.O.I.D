"""
skills/phone_control.py
V.O.I.D. Android Phone Control Skill.
Integrates ADB phone automation (unlocking, app launching, calls, media) into the VOID skill layer.
"""

from typing import Any, Dict, Optional
from void_phone.phone_controller import phone_controller
from void_phone.intent_parser import intent_parser


def handle_phone_control(command: str) -> str:
    """
    Execute a natural language phone command via ADB.
    """
    intent = intent_parser.parse(command)
    return intent.execute(phone_controller)


def unlock_phone(pin: Optional[str] = None) -> str:
    """
    Wake screen, swipe up lockscreen, and input PIN to unlock the connected Android device.
    """
    return phone_controller.unlock(pin=pin)


def launch_phone_app(app_name: str) -> str:
    """
    Launch an Android application on the connected phone (e.g., 'JioCinema', 'WhatsApp', 'YouTube').
    """
    return phone_controller.launch_app(app_name)


def call_phone_contact(contact_or_number: str) -> str:
    """
    Place a phone call to a named contact or phone number.
    """
    return phone_controller.call_contact(contact_or_number, direct_call=True)


def get_phone_status() -> Dict[str, Any]:
    """
    Retrieve phone telemetry: connection state, model, battery, screen state, IP.
    """
    return phone_controller.get_status_summary()


def send_phone_notification(title: str, message: str, priority: str = "normal") -> Dict[str, Any]:
    """
    Send a push notification or heads-up alert to the connected Android phone.
    """
    from void_phone.notifications import phone_notifications
    return phone_notifications.send_phone_notification(title, message, priority)


def show_phone_toast(message: str) -> Dict[str, Any]:
    """
    Display a brief toast alert on the connected Android phone display.
    """
    from void_phone.notifications import phone_notifications
    return phone_notifications.show_phone_toast(message)


def get_phone_telemetry() -> Dict[str, Any]:
    """
    Extract comprehensive real-time phone telemetry (battery, display, app, network, storage).
    """
    from void_phone.remote_sensor import phone_sensors
    return phone_sensors.get_telemetry()


def capture_phone_screen(max_dimension: Optional[int] = 1080) -> Dict[str, Any]:
    """
    Capture a screenshot frame of the connected Android smartphone screen.
    Returns base64 encoded PNG data URL.
    """
    from void_phone.remote_sensor import phone_sensors
    return phone_sensors.capture_screen_base64(max_dimension=max_dimension)


def read_phone_sms(limit: int = 5) -> Dict[str, Any]:
    """
    Read recent incoming SMS messages from the phone's inbox.
    """
    from void_phone.notification_reader import phone_reader
    return phone_reader.get_recent_sms(limit=limit)


def read_phone_notifications(limit: int = 10) -> Dict[str, Any]:
    """
    Read active notifications posted in the Android notification tray.
    """
    from void_phone.notification_reader import phone_reader
    return phone_reader.get_active_notifications(limit=limit)


def get_phone_briefing() -> str:
    """
    Generate an executive natural language briefing of unread SMS and active notifications.
    """
    from void_phone.notification_reader import phone_reader
    return phone_reader.get_unread_digest()

