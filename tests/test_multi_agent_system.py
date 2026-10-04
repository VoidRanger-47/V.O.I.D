# tests/test_multi_agent_system.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agents.coordinator import agent_coordinator
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.agents.base import AgentStatus
import core.agents.network  # Ensures initialization

class TestMultiAgentSystem(unittest.TestCase):
    def setUp(self):
        self.coordinator = agent_coordinator

    def test_all_13_agents_registered(self):
        registered_agents = list(self.coordinator.agents.keys())
        expected_agents = [
            "executive", "perception_agent", "memory_agent", "planning_agent",
            "verification_agent", "coding_agent", "system_agent", "computer_agent",
            "knowledge_agent", "research_agent", "vision_agent", "voice_agent", "automation_agent"
        ]
        for name in expected_agents:
            self.assertIn(name, registered_agents, f"Agent '{name}' was not registered in coordinator.")

    def test_system_agent_zero_llm_execution(self):
        msg = AgentMessage(
            sender="test_suite",
            receiver="system_agent",
            goal="Query hardware status",
            payload={"action": "hardware_summary"}
        )
        res = self.coordinator.route_message(msg)
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("CPU", str(res.result))
        self.assertIn("RAM", str(res.result))

    def test_memory_agent_query_and_store(self):
        # Store
        store_msg = AgentMessage(
            sender="test_suite",
            receiver="memory_agent",
            goal="Store favorite IDE",
            payload={"action": "store", "text": "The user is running V.O.I.D. in Antigravity IDE.", "tier": "semantic"}
        )
        res_store = self.coordinator.route_message(store_msg)
        self.assertEqual(res_store.status, "SUCCESS")

        # Retrieve
        query_msg = AgentMessage(
            sender="test_suite",
            receiver="memory_agent",
            goal="What IDE is the user running?",
            payload={"action": "retrieve", "query": "Antigravity IDE"}
        )
        res_query = self.coordinator.route_message(query_msg)
        self.assertEqual(res_query.status, "SUCCESS")
        self.assertIn("Antigravity", str(res_query.result))

        # Forget
        forget_msg = AgentMessage(
            sender="test_suite",
            receiver="memory_agent",
            goal="Forget IDE memory",
            payload={"action": "forget", "target": "Antigravity IDE"}
        )
        res_forget = self.coordinator.route_message(forget_msg)
        self.assertEqual(res_forget.status, "SUCCESS")
        self.assertGreater(res_forget.payload.get("forgotten_count", 0), 0)

    def test_coding_agent_sandboxed_math(self):
        msg = AgentMessage(
            sender="test_suite",
            receiver="coding_agent",
            goal="Execute sandboxed math",
            payload={"action": "run_python", "code": "import math\nprint(math.factorial(5))"}
        )
        res = self.coordinator.route_message(msg)
        self.assertEqual(res.status, "SUCCESS")
        self.assertIn("120", str(res.result))

    def test_executive_agent_multi_agent_delegation(self):
        msg = AgentMessage(
            sender="test_suite",
            receiver="executive",
            goal="Show system stats"
        )
        res = self.coordinator.route_message(msg)
        self.assertEqual(res.status, "SUCCESS")
        self.assertTrue(len(str(res.result)) > 0)

    def test_coordinator_message_tracing(self):
        traces = self.coordinator.message_trace
        self.assertGreater(len(traces), 0)
        latest = traces[-1]
        self.assertIn("task_id", latest)
        self.assertIn("duration", latest)

if __name__ == "__main__":
    unittest.main()
