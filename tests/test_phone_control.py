"""
Unit tests for V.O.I.D. Android Phone Control Module.
Tests ADBBridge, PhoneController, IntentParser, and VOID agent integration.
"""

import os
import unittest
from unittest.mock import MagicMock, patch

from void_phone.adb_bridge import ADBBridge, DeviceInfo
from void_phone.phone_controller import PhoneController
from void_phone.intent_parser import IntentParser, IntentType, PhoneIntent
from skills.phone_control import handle_phone_control, unlock_phone, launch_phone_app, call_phone_contact
from core.tool_registry import tool_registry
from core.agents.coordinator import agent_coordinator
from core.agents.phone_agent import PhoneAgent
from core.agents.protocol import AgentMessage
import core.agents.network


class TestADBBridge(unittest.TestCase):
    def setUp(self):
        self.bridge = ADBBridge()

    def test_adb_path_resolved(self):
        self.assertIsNotNone(self.bridge.adb_path)
        self.assertTrue(len(self.bridge.adb_path) > 0)

    @patch.object(ADBBridge, "run_adb_command")
    def test_list_devices_parsing(self, mock_run):
        mock_stdout = (
            "List of devices attached\n"
            "emulator-5554          device product:sdk_gphone64_arm64 model:sdk_gphone64_arm64 device:emulator_arm64\n"
            "192.168.1.50:5555      device product:redmi model:Redmi_Note_12 device:sunstone\n"
            "unauth_serial          unauthorized\n"
        )
        mock_run.return_value = (0, mock_stdout, "")

        devices = self.bridge.list_devices()
        self.assertEqual(len(devices), 3)

        self.assertEqual(devices[0].serial, "emulator-5554")
        self.assertEqual(devices[0].state, "device")
        self.assertEqual(devices[0].connection_type, "usb")

        self.assertEqual(devices[1].serial, "192.168.1.50:5555")
        self.assertEqual(devices[1].state, "device")
        self.assertEqual(devices[1].connection_type, "tcpip")
        self.assertEqual(devices[1].model, "Redmi Note 12")

        self.assertEqual(devices[2].serial, "unauth_serial")
        self.assertEqual(devices[2].state, "unauthorized")

    @patch.object(ADBBridge, "list_devices")
    def test_is_connected(self, mock_list):
        mock_list.return_value = [
            DeviceInfo(serial="dev123", state="device", connection_type="usb")
        ]
        self.assertTrue(self.bridge.is_connected("dev123"))

        mock_list.return_value = [
            DeviceInfo(serial="dev123", state="unauthorized", connection_type="usb")
        ]
        self.assertFalse(self.bridge.is_connected("dev123"))


class TestPhoneController(unittest.TestCase):
    def setUp(self):
        self.mock_bridge = MagicMock(spec=ADBBridge)
        self.mock_bridge.is_connected.return_value = True
        self.mock_bridge.get_display_size.return_value = (1080, 2400)
        self.controller = PhoneController(bridge=self.mock_bridge)

    def test_app_package_resolution(self):
        self.assertEqual(self.controller.resolve_app_package("JioCinema"), "com.jio.media.ondemand")
        self.assertEqual(self.controller.resolve_app_package("jio cinema"), "com.jio.media.ondemand")
        self.assertEqual(self.controller.resolve_app_package("WhatsApp"), "com.whatsapp")
        self.assertEqual(self.controller.resolve_app_package("YouTube"), "com.google.android.youtube")
        self.assertEqual(self.controller.resolve_app_package("yt"), "com.google.android.youtube")
        self.assertEqual(self.controller.resolve_app_package("Instagram"), "com.instagram.android")
        self.assertEqual(self.controller.resolve_app_package("Spotify"), "com.spotify.music")
        self.assertEqual(self.controller.resolve_app_package("Netflix"), "com.netflix.mediaclient")

    def test_contact_number_resolution(self):
        num, name = self.controller.resolve_contact_number("Mom")
        self.assertEqual(num, "+1234567890")
        self.assertEqual(name, "Mom")

        num_direct, _ = self.controller.resolve_contact_number("+919876543210")
        self.assertEqual(num_direct, "+919876543210")

    def test_unlock_sequence(self):
        self.mock_bridge.shell.return_value = (0, "Events injected: 1", "")
        res = self.controller.unlock(pin="4321")
        self.assertIn("Phone unlocked", res)
        # Verify wakeup and input calls were made
        calls = [c[0][0] for c in self.mock_bridge.shell.call_args_list]
        self.assertTrue(any("input text 4321" in c for c in calls))
        self.assertTrue(any("input swipe" in c for c in calls))

    def test_launch_app(self):
        self.mock_bridge.shell.return_value = (0, "Events injected: 1", "")
        res = self.controller.launch_app("JioCinema")
        self.assertIn("Launched JioCinema", res)
        self.assertIn("com.jio.media.ondemand", res)

    def test_call_contact(self):
        self.mock_bridge.shell.return_value = (0, "Starting: Intent { act=android.intent.action.CALL ... }", "")
        res = self.controller.call_contact("Mom", direct_call=True)
        self.assertIn("Calling Mom", res)
        self.assertIn("+1234567890", res)


class TestIntentParser(unittest.TestCase):
    def setUp(self):
        self.parser = IntentParser()

    def test_unlock_intents(self):
        intent = self.parser.parse("Void, unlock my phone")
        self.assertEqual(intent.intent_type, IntentType.UNLOCK)

        intent2 = self.parser.parse("unlock phone with pin 9999")
        self.assertEqual(intent2.intent_type, IntentType.UNLOCK)
        self.assertEqual(intent2.parameters.get("pin"), "9999")

    def test_lock_intents(self):
        intent = self.parser.parse("Void, lock my phone")
        self.assertEqual(intent.intent_type, IntentType.LOCK)

        intent2 = self.parser.parse("turn off screen")
        self.assertEqual(intent2.intent_type, IntentType.LOCK)

    def test_launch_app_intents(self):
        intent1 = self.parser.parse("Void, open JioCinema")
        self.assertEqual(intent1.intent_type, IntentType.LAUNCH_APP)
        self.assertEqual(intent1.parameters.get("app_name"), "jiocinema")

        intent2 = self.parser.parse("launch WhatsApp please")
        self.assertEqual(intent2.intent_type, IntentType.LAUNCH_APP)
        self.assertEqual(intent2.parameters.get("app_name"), "whatsapp")

        intent3 = self.parser.parse("start YouTube app")
        self.assertEqual(intent3.intent_type, IntentType.LAUNCH_APP)
        self.assertEqual(intent3.parameters.get("app_name"), "youtube")

    def test_call_intents(self):
        intent1 = self.parser.parse("Void, call Mom")
        self.assertEqual(intent1.intent_type, IntentType.CALL)
        self.assertEqual(intent1.parameters.get("target"), "mom")

        intent2 = self.parser.parse("dial 9876543210")
        self.assertEqual(intent2.intent_type, IntentType.DIAL)
        self.assertEqual(intent2.parameters.get("target"), "9876543210")

    def test_volume_and_media_intents(self):
        intent_vol = self.parser.parse("increase volume 3 steps")
        self.assertEqual(intent_vol.intent_type, IntentType.VOLUME_UP)
        self.assertEqual(intent_vol.parameters.get("steps"), 3)

        intent_play = self.parser.parse("pause music")
        self.assertEqual(intent_play.intent_type, IntentType.MEDIA_PLAY_PAUSE)

        intent_next = self.parser.parse("skip song")
        self.assertEqual(intent_next.intent_type, IntentType.MEDIA_NEXT)

    def test_nav_and_screenshot_intents(self):
        intent_home = self.parser.parse("go home")
        self.assertEqual(intent_home.intent_type, IntentType.NAV_HOME)

        intent_shot = self.parser.parse("take screenshot")
        self.assertEqual(intent_shot.intent_type, IntentType.TAKE_SCREENSHOT)


class TestVOIDIntegration(unittest.TestCase):
    def test_tool_registry_has_phone_control(self):
        tool = tool_registry.get_tool("phone_control")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "phone_control")

    def test_agent_coordinator_has_phone_agent(self):
        agent = agent_coordinator.get_agent("phone_agent")
        self.assertIsNotNone(agent)
        self.assertIsInstance(agent, PhoneAgent)


if __name__ == "__main__":
    unittest.main()
