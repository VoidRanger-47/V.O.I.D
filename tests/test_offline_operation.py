# tests/test_offline_operation.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.offline_manager import offline_mgr
from core.tool_registry import ToolRegistry
from void_memory.memory import VoidMemory

class TestOfflineOperation(unittest.TestCase):
    def setUp(self):
        self.offline_mgr = offline_mgr
        self.tools = ToolRegistry.get_instance()
        self.memory = VoidMemory.get_instance()

    def test_offline_manager_status(self):
        status = self.offline_mgr.get_status()
        self.assertIn("offline_mode", status)
        self.assertIn("local_components", status)
        self.assertGreater(len(status["local_components"]), 4)

    def test_web_search_fails_gracefully_offline(self):
        from skills.web_search import perform_search
        # Force offline simulation on singleton
        self.offline_mgr.cached_online_state = False
        self.offline_mgr.last_check_time = 9999999999.0  # Keep cache fixed

        result = perform_search("What is the temperature today?")
        self.assertIn("Offline Mode", result)
        self.assertIn("No Internet Access", result)

    def test_local_math_works_offline(self):
        res = self.tools.execute_tool("math_solver", "integrate x^2 dx")
        self.assertIn("x", str(res))

    def test_local_system_stats_work_offline(self):
        stats = self.tools.execute_tool("system_monitor")
        self.assertIn("CPU", stats)
        self.assertIn("RAM", stats)

if __name__ == "__main__":
    unittest.main()

