# tests/test_smart_router.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.router import ExecutiveRouter, ExecutionPath, IntentClass, executive_router


class TestSmartRouter(unittest.TestCase):
    def setUp(self):
        self.router = ExecutiveRouter.get_instance()

    def test_fast_path_math_arithmetic(self):
        path, res, intent = self.router.route("What is 25 * 42?")
        self.assertEqual(path, ExecutionPath.FAST_PATH)
        self.assertEqual(intent, IntentClass.MATH)
        self.assertIsNotNone(res)
        self.assertIn("1050", str(res))

    def test_fast_path_system_time(self):
        path, res, intent = self.router.route("what time is it right now?")
        self.assertEqual(path, ExecutionPath.FAST_PATH)
        self.assertEqual(intent, IntentClass.SYSTEM)
        self.assertIsNotNone(res)
        self.assertIn("time", str(res).lower())

    def test_fast_path_system_stats(self):
        path, res, intent = self.router.route("show me system stats and cpu usage")
        self.assertEqual(path, ExecutionPath.FAST_PATH)
        self.assertEqual(intent, IntentClass.SYSTEM)
        self.assertIsNotNone(res)
        self.assertIn("cpu", str(res).lower())

    def test_fast_path_app_launch(self):
        path, res, intent = self.router.route("open notepad")
        self.assertEqual(path, ExecutionPath.FAST_PATH)
        self.assertIsNotNone(res)

    def test_deep_path_multi_domain_diagnosis(self):
        # Complex goal requires Deep Path (Executive + Planner + Parallel DAG)
        path, res, intent = self.router.route("Analyze this project, find bugs, calculate performance bottlenecks, and suggest improvements.")
        self.assertEqual(path, ExecutionPath.DEEP_PATH)
        self.assertEqual(intent, IntentClass.MULTI_AGENT)
        self.assertIsNone(res)  # Deep Path executes via multi-agent DAG, not single fast tool

    def test_deep_path_when_thinking_mode_enabled(self):
        path, res, intent = self.router.route("What is 2 + 2?", thinking_mode=True)
        # Explicit thinking mode forces deep path
        self.assertEqual(path, ExecutionPath.DEEP_PATH)

    def test_deep_path_when_force_search_enabled(self):
        path, res, intent = self.router.route("Who won the game yesterday?", force_search=True)
        self.assertEqual(path, ExecutionPath.DEEP_PATH)


if __name__ == "__main__":
    unittest.main()
