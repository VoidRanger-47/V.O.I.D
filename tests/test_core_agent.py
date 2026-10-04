# tests/test_core_agent.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.event_bus import EventBus, SystemEvent
from core.state_manager import StateManager
from core.tool_registry import ToolRegistry
from core.planner import AgentPlanner
from core.agent import VoidAgent

class TestCoreAgent(unittest.TestCase):
    def setUp(self):
        self.event_bus = EventBus()
        self.state_manager = StateManager()
        self.tool_registry = ToolRegistry.get_instance()
        self.planner = AgentPlanner()
        self.agent = VoidAgent.get_instance()

    def test_event_bus_publish_and_subscribe(self):
        received = []
        def handler(event_data):
            received.append(event_data)

        self.event_bus.subscribe(SystemEvent.AGENT_TASK_CREATED, handler)
        self.event_bus.publish(SystemEvent.AGENT_TASK_CREATED, {"task": "Diagnostic run"})

        self.assertEqual(len(received), 1)
        self.assertEqual(received[0]["event"], "AGENT_TASK_CREATED")
        self.assertEqual(received[0]["data"]["task"], "Diagnostic run")

    def test_state_manager_world_state(self):
        state = self.state_manager.get_world_state()
        self.assertIn("current_time", state)
        self.assertIn("cpu_usage_percent", state)
        self.assertIn("ram_percent", state)
        self.assertIn("offline_mode", state)

    def test_tool_registry_execution(self):
        # Math tool execution
        math_res = self.tool_registry.execute_tool("math_solver", "calculate 45 * 2 + 10")
        self.assertIn("100", str(math_res))

        # System info tool execution
        sys_res = self.tool_registry.execute_tool("system_info")
        self.assertIn("202", str(sys_res))  # Year format

    def test_planner_goal_decomposition(self):
        # Math plan
        plan_math = self.planner.create_plan("solve 2x + 5 = 15")
        self.assertEqual(plan_math.steps[0].tool_name, "math_solver")

        # Multi-step plan
        plan_multi = self.planner.create_plan("Why isn't my project starting? Please diagnose it.")
        self.assertTrue(plan_multi.is_multi_step)
        self.assertGreaterEqual(len(plan_multi.steps), 2)

    def test_agent_synchronous_task_execution(self):
        result = self.agent.run_task("solve 15 * 6")
        self.assertEqual(result.status, "SUCCESS")
        self.assertIn("90", result.response)

if __name__ == "__main__":
    unittest.main()
