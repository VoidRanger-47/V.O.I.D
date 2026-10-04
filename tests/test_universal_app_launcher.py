# tests/test_universal_app_launcher.py
import unittest
import sys
import os
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skills.computer_control import (
    app_registry,
    extract_device_and_app,
    is_app_launch_request,
    launch_application_on_host,
    launch_application
)
from void_phone.phone_controller import phone_controller
from chat import route_query
from app import app


class TestUniversalAppLauncher(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_app_registry_deep_scan(self):
        apps = app_registry.scan_installed_apps()
        self.assertIsInstance(apps, dict)
        self.assertGreater(len(apps), 50, f"Expected at least 50 apps, got {len(apps)}")
        # Check canonical catalog entries exist
        self.assertIn("instagram", apps)
        self.assertIn("telegram", apps)
        self.assertIn("whatsapp", apps)
        self.assertIn("calculator", apps)
        self.assertIn("spotify", apps)

    def test_extract_device_and_app(self):
        cases = [
            ("open insta on phone", ("phone", "insta")),
            ("launch telegram on pc", ("pc", "telegram")),
            ("open spotify everywhere", ("all", "spotify")),
            ("open spotify on all devices", ("all", "spotify")),
            ("open calculator", ("default", "calculator")),
            ("can you please start vscode on laptop", ("pc", "vscode")),
            ("hey void open whatsapp on my mobile", ("phone", "whatsapp")),
        ]
        for query, expected in cases:
            dev, target = extract_device_and_app(query)
            self.assertEqual(dev, expected[0], f"Failed device for {query}: got {dev}")
            self.assertEqual(target, expected[1], f"Failed target for {query}: got {target}")

    def test_is_app_launch_request(self):
        self.assertTrue(is_app_launch_request("open insta"))
        self.assertTrue(is_app_launch_request("launch telegram"))
        self.assertTrue(is_app_launch_request("start calculator"))
        self.assertTrue(is_app_launch_request("open vs code on pc"))
        self.assertTrue(is_app_launch_request("open whatsapp on phone"))
        self.assertFalse(is_app_launch_request("what is the weather today?"))
        self.assertFalse(is_app_launch_request("why is the sky blue?"))

    def test_resolve_social_and_small_apps(self):
        # Instagram
        res_insta = app_registry.resolve("insta")
        self.assertIsNotNone(res_insta)
        disp, target, mode, web = res_insta
        self.assertEqual(disp, "Instagram")

        # Telegram
        res_tg = app_registry.resolve("tg")
        self.assertIsNotNone(res_tg)
        disp, target, mode, web = res_tg
        self.assertEqual(disp, "Telegram")

        # WhatsApp
        res_wa = app_registry.resolve("whatsapp")
        self.assertIsNotNone(res_wa)
        disp, target, mode, web = res_wa
        self.assertEqual(disp, "WhatsApp")

        # Calculator
        res_calc = app_registry.resolve("calc")
        self.assertIsNotNone(res_calc)
        disp, target, mode, web = res_calc
        self.assertEqual(disp, "Calculator")

    def test_phone_package_resolution(self):
        pkg_insta = phone_controller.resolve_app_package("insta")
        self.assertEqual(pkg_insta, "com.instagram.android")

        pkg_tg = phone_controller.resolve_app_package("telegram")
        self.assertEqual(pkg_tg, "org.telegram.messenger")

        pkg_wa = phone_controller.resolve_app_package("whatsapp")
        self.assertEqual(pkg_wa, "com.whatsapp")

        pkg_yt = phone_controller.resolve_app_package("youtube")
        self.assertEqual(pkg_yt, "com.google.android.youtube")

    def test_chat_route_query_app_launch(self):
        # Open Insta
        resp, skill = route_query("open insta")
        self.assertEqual(skill, "computer_control")
        self.assertTrue("Instagram" in resp or "insta" in resp.lower())

        # Open Telegram
        resp, skill = route_query("launch telegram")
        self.assertEqual(skill, "computer_control")
        self.assertTrue("Telegram" in resp or "telegram" in resp.lower())

        # Open Calculator
        resp, skill = route_query("open calculator")
        self.assertEqual(skill, "computer_control")
        self.assertTrue("Calculator" in resp or "calc" in resp.lower())

    def test_api_apps_endpoint(self):
        response = self.client.get("/api/apps")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertGreater(data["host_apps_count"], 50)
        self.assertIn("host_apps", data)


if __name__ == "__main__":
    unittest.main()
