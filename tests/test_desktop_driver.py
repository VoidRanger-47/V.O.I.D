# tests/test_desktop_driver.py
import unittest
from core.desktop.driver import desktop_driver, DesktopDriver, FailsafeTriggeredError
from skills.desktop_control import (
    list_desktop_windows,
    focus_desktop_window,
    execute_desktop_action,
    execute_desktop_macro
)


class TestDesktopDriver(unittest.TestCase):
    def setUp(self):
        self.driver = desktop_driver

    def test_screen_size(self):
        w, h = self.driver.get_screen_size()
        self.assertGreater(w, 0)
        self.assertGreater(h, 0)

    def test_list_windows(self):
        windows = self.driver.list_windows(visible_only=True)
        self.assertIsInstance(windows, list)
        if windows:
            first = windows[0]
            self.assertIn("title", first)
            self.assertIn("hwnd", first)
            self.assertIn("rect", first)
            self.assertIn("process_name", first)

    def test_skills_windows_list(self):
        windows = list_desktop_windows(visible_only=True)
        self.assertIsInstance(windows, list)

    def test_desktop_action_screen_size(self):
        res = execute_desktop_action("screen_size")
        self.assertTrue(res.get("success"))
        self.assertIn("screen", res)
        self.assertGreater(res["screen"]["width"], 0)

    def test_desktop_action_cursor_position(self):
        res = execute_desktop_action("get_cursor")
        self.assertTrue(res.get("success"))
        self.assertIn("cursor", res)
        self.assertIn("x", res["cursor"])
        self.assertIn("y", res["cursor"])

    def test_desktop_macro_dry_run(self):
        macro_steps = [
            {"action": "screen_size"},
            {"action": "get_cursor"}
        ]
        res = execute_desktop_macro(macro_steps)
        self.assertTrue(res.get("success"))
        self.assertEqual(res.get("completed_steps"), 2)


if __name__ == "__main__":
    unittest.main()
