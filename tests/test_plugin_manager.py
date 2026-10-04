# tests/test_plugin_manager.py
import unittest
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.plugin_manager import PluginManager, PluginBase, PluginMetadata


class TestPluginManager(unittest.TestCase):
    def setUp(self):
        self.pm = PluginManager.get_instance()
        self.pm.discover_and_load_plugins()

    def test_plugin_discovery(self):
        plugins = self.pm.list_plugins()
        self.assertIsInstance(plugins, list)
        # Verify gmail_analyzer is loaded
        plugin_ids = [p["id"] for p in plugins]
        self.assertIn("gmail_analyzer", plugin_ids)

    def test_get_plugin(self):
        gmail_plugin = self.pm.get_plugin("gmail_analyzer")
        self.assertIsNotNone(gmail_plugin)
        self.assertEqual(gmail_plugin.metadata.id, "gmail_analyzer")
        self.assertTrue(gmail_plugin.is_initialized)

    def test_can_handle_matching(self):
        plugin = self.pm.can_handle("analyze my gmail")
        self.assertIsNotNone(plugin)
        self.assertEqual(plugin.metadata.id, "gmail_analyzer")

        plugin2 = self.pm.can_handle("check my unread emails")
        self.assertIsNotNone(plugin2)
        self.assertEqual(plugin2.metadata.id, "gmail_analyzer")

        # Non-matching query
        plugin_none = self.pm.can_handle("solve 2x + 5 = 10")
        self.assertIsNone(plugin_none)

    def test_dispatch(self):
        res = self.pm.dispatch("analyze my gmail")
        self.assertIsNotNone(res)
        text, skill_tag = res
        self.assertIn("V.O.I.D. Gmail Intelligence Report", text)
        self.assertEqual(skill_tag, "gmail_analyzer")


if __name__ == "__main__":
    unittest.main()
