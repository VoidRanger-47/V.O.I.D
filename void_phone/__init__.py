"""
V.O.I.D. Android Phone Control Module.
Provides ADB bridge abstraction, device management, intent parsing, and voice-controlled phone automation.
"""

from void_phone.adb_bridge import ADBBridge, adb_bridge
from void_phone.phone_controller import PhoneController, phone_controller
from void_phone.intent_parser import IntentParser, PhoneIntent, IntentType
from void_phone.voice_listener import PhoneVoiceListener
from void_phone.notifications import PhoneNotificationManager, phone_notifications
from void_phone.remote_sensor import PhoneSensorManager, phone_sensors
from void_phone.notification_reader import PhoneNotificationReader, phone_reader

__all__ = [
    "ADBBridge",
    "adb_bridge",
    "PhoneController",
    "phone_controller",
    "IntentParser",
    "PhoneIntent",
    "IntentType",
    "PhoneVoiceListener",
    "PhoneNotificationManager",
    "phone_notifications",
    "PhoneSensorManager",
    "phone_sensors",
    "PhoneNotificationReader",
    "phone_reader",
]

