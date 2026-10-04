"""
tests/test_phone_features.py
Comprehensive unit test suite for V.O.I.D. Mobile Remote Perception, Notifications,
Sensor Engine, and Phone Agent integrations.
"""

import io
import json
import unittest
from unittest.mock import MagicMock, patch
from PIL import Image

from void_phone.notifications import PhoneNotificationManager
from void_phone.remote_sensor import PhoneSensorManager
from void_phone.notification_reader import PhoneNotificationReader
from core.agents.phone_agent import PhoneAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.tool_registry import tool_registry
from core.mcp.server import MCPServer


class TestPhoneFeatures(unittest.TestCase):

    def setUp(self):
        # Sample 1x1 valid PNG bytes for image mock tests
        buf = io.BytesIO()
        img = Image.new("RGB", (100, 200), color="blue")
        img.save(buf, format="PNG")
        self.sample_png_bytes = buf.getvalue()

    def test_phone_tools_registered(self):
        """Verify all phone perception & alert tools are registered in tool_registry."""
        tools = tool_registry.list_tools()
        names = [t["name"] if isinstance(t, dict) else t.name for t in tools]
        expected_tools = [
            "phone_notify",
            "phone_toast",
            "phone_telemetry",
            "phone_screenshot",
            "phone_read_sms",
            "phone_notifications",
            "phone_briefing"
        ]
        for exp in expected_tools:
            self.assertIn(exp, names, f"Tool '{exp}' missing from ToolRegistry")

    def test_mcp_phone_tools_registered(self):
        """Verify phone tools are exposed through MCP server."""
        server = MCPServer()
        tools = server._tools
        self.assertIn("void_phone_notify", tools)
        self.assertIn("void_phone_telemetry", tools)

    def test_notification_manager_offline(self):
        """Verify PhoneNotificationManager fails gracefully when no device is connected."""
        mgr = PhoneNotificationManager()
        with patch.object(mgr.bridge, "run_adb_command", return_value=(0, "List of devices attached\n\n", "")):
            res = mgr.send_phone_notification("Test Title", "Test Message")
            self.assertFalse(res.get("success"))
            self.assertIn("No Android device connected", res.get("error", ""))

            toast_res = mgr.show_phone_toast("Test Toast")
            self.assertFalse(toast_res.get("success"))

    def test_notification_manager_online_cmd_post(self):
        """Verify successful notification dispatch via Android 11+ cmd notification."""
        mgr = PhoneNotificationManager()
        with patch.object(mgr.bridge, "run_adb_command") as mock_adb:
            # First call for devices check, second for cmd notification post
            mock_adb.side_effect = [
                (0, "List of devices attached\nemulator-5554\tdevice\n", ""),
                (0, "", "")  # cmd notification post returns 0
            ]
            res = mgr.send_phone_notification("Mission 47", "Model compiled successfully")
            self.assertTrue(res.get("success"))
            self.assertEqual(res.get("method"), "cmd_notification")
            self.assertEqual(res.get("title"), "Mission 47")

    def test_telemetry_parsers(self):
        """Verify sensor telemetry parsing for battery, display, app, and network."""
        sensor = PhoneSensorManager()

        # 1. Battery parsing
        battery_dumpsys = """
Current Battery Service state:
  AC powered: false
  USB powered: true
  Wireless powered: false
  Max charging current: 500000
  Max charging voltage: 5000000
  Charge counter: 2800000
  status: 2
  health: 2
  present: true
  level: 84
  scale: 100
  voltage: 4120
  temperature: 315
  technology: Li-ion
"""
        with patch.object(sensor.bridge, "shell", return_value=(0, battery_dumpsys, "")):
            batt = sensor._parse_battery("test_device")
            self.assertEqual(batt["level"], 84)
            self.assertEqual(batt["status"], "Charging")
            self.assertEqual(batt["plugged"], "USB Port")
            self.assertEqual(batt["temperature_c"], 31.5)
            self.assertEqual(batt["voltage_mv"], 4120)

        # 2. Display parsing
        with patch.object(sensor.bridge, "get_display_size", return_value=(1080, 2400)), \
             patch.object(sensor.bridge, "shell", return_value=(0, "mHoldingDisplaySuspendBlocker=true", "")):
            disp = sensor._parse_display("test_device")
            self.assertEqual(disp["width"], 1080)
            self.assertEqual(disp["height"], 2400)
            self.assertTrue(disp["is_screen_on"])
            self.assertEqual(disp["orientation"], "portrait")

        # 3. Foreground app parsing
        window_out = "  mCurrentFocus=Window{8bc9c89 u0 com.whatsapp/com.whatsapp.HomeActivity}"
        with patch.object(sensor.bridge, "shell", return_value=(0, window_out, "")):
            app = sensor._parse_foreground_app("test_device")
            self.assertEqual(app["package"], "com.whatsapp")
            self.assertEqual(app["activity"], "com.whatsapp.HomeActivity")
            self.assertFalse(app["is_home"])

    def test_screen_capture(self):
        """Verify binary screen capture and base64 encoding."""
        sensor = PhoneSensorManager()
        with patch.object(sensor.bridge, "get_active_device_serial", return_value="device_001"), \
             patch.object(sensor.bridge, "is_connected", return_value=True), \
             patch.object(sensor.bridge, "run_adb_command_raw", return_value=(0, self.sample_png_bytes, b"")):

            res = sensor.capture_screen_base64()
            self.assertTrue(res.get("success"))
            self.assertIn("data:image/png;base64,", res.get("data_url", ""))
            self.assertEqual(res.get("width"), 100)
            self.assertEqual(res.get("height"), 200)

    def test_notification_reader_sms_parsing(self):
        """Verify SMS row parsing from ADB content query."""
        reader = PhoneNotificationReader()
        sample_rows = (
            "Row: 0 address=+14155552671, date=1700000000000, read=1, body=Your verification code is 492011\n"
            "Row: 1 address=Amazon, date=1699990000000, read=0, body=Your package has arrived at front door\n"
        )
        parsed = reader._parse_sms_content_rows(sample_rows, limit=5)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["sender"], "+14155552671")
        self.assertIn("492011", parsed[0]["body"])
        self.assertTrue(parsed[0]["read"])
        self.assertEqual(parsed[1]["sender"], "Amazon")
        self.assertFalse(parsed[1]["read"])

    def test_dumpsys_notification_parsing(self):
        """Verify active notification parsing from dumpsys text."""
        reader = PhoneNotificationReader()
        dumpsys_sample = """
Current Notification List:
  NotificationRecord(0x7ff0123 pkg=com.whatsapp id=101 tag=null: Notification(channel=chat pri=1 tickerText=null contentIntent=PendingIntent))
    android.title=String (Alex)
    android.text=String (Hey, did you finish the V.O.I.D. integration?)
  NotificationRecord(0x7ff0456 pkg=com.google.android.gm id=202 tag=null: Notification(channel=mail pri=0))
    android.title=String (GitHub)
    android.text=String (New pull request opened)
"""
        parsed = reader._parse_dumpsys_notifications(dumpsys_sample, limit=5)
        self.assertEqual(len(parsed), 2)
        self.assertEqual(parsed[0]["package"], "com.whatsapp")
        self.assertEqual(parsed[0]["title"], "Alex")
        self.assertEqual(parsed[0]["text"], "Hey, did you finish the V.O.I.D. integration?")
        self.assertEqual(parsed[1]["package"], "com.google.android.gm")

    def test_phone_agent_actions(self):
        """Verify PhoneAgent dispatches notify, toast, telemetry, screen, and briefing actions."""
        agent = PhoneAgent()

        # 1. Action: notify
        with patch("core.agents.phone_agent.send_phone_notification", return_value={"success": True, "title": "T", "message": "M"}):
            msg = AgentMessage(
                sender="user",
                receiver="phone_agent",
                goal="Notify phone",
                payload={"action": "notify", "title": "Mission Alert", "message": "Done!"}
            )
            resp = agent.process(msg)
            self.assertEqual(resp.status, "SUCCESS")
            self.assertIn("Notification pushed", resp.result)

        # 2. Action: telemetry
        sample_tel = {
            "success": True,
            "battery": {"level": 90, "status": "Full"},
            "foreground_app": {"package": "com.android.launcher"}
        }
        with patch("core.agents.phone_agent.get_phone_telemetry", return_value=sample_tel):
            msg2 = AgentMessage(
                sender="user",
                receiver="phone_agent",
                goal="Check telemetry",
                payload={"action": "telemetry"}
            )
            resp2 = agent.process(msg2)
            self.assertEqual(resp2.status, "SUCCESS")
            self.assertIn("Battery 90%", resp2.result)

        # 3. Action: briefing
        with patch("core.agents.phone_agent.get_phone_briefing", return_value="📱 Mobile Status Briefing: Everything clear."):
            msg3 = AgentMessage(
                sender="user",
                receiver="phone_agent",
                goal="Phone briefing",
                payload={"action": "briefing"}
            )
            resp3 = agent.process(msg3)
            self.assertEqual(resp3.status, "SUCCESS")
            self.assertIn("Everything clear", resp3.result)


if __name__ == "__main__":
    unittest.main()
