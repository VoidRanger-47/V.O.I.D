# tests/test_verification_agent.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agents.coordinator import agent_coordinator
from core.agents.protocol import AgentMessage

class TestVerificationAgent(unittest.TestCase):
    def setUp(self):
        self.coordinator = agent_coordinator

    def test_verification_pass_on_valid_output(self):
        msg = AgentMessage(
            sender="test_suite",
            receiver="verification_agent",
            goal="Verify greeting output",
            payload={"output": "Hello, I am V.O.I.D., your offline AI operating layer.", "expected_type": "general"}
        )
        res = self.coordinator.route_message(msg)
        self.assertEqual(res.status, "SUCCESS")
        self.assertEqual(res.payload.get("verdict"), "PASS")

    def test_verification_fail_on_empty_output(self):
        msg = AgentMessage(
            sender="test_suite",
            receiver="verification_agent",
            goal="Verify empty output",
            payload={"output": "   ", "expected_type": "general"}
        )
        res = self.coordinator.route_message(msg)
        self.assertEqual(res.status, "FAILED")
        self.assertEqual(res.payload.get("verdict"), "FAIL")
        self.assertEqual(res.payload.get("reason"), "empty_output")

    def test_verification_fail_on_error_output(self):
        msg = AgentMessage(
            sender="test_suite",
            receiver="verification_agent",
            goal="Verify error output",
            payload={"output": "❌ Syntax Error: unexpected EOF while parsing", "expected_type": "general"}
        )
        res = self.coordinator.route_message(msg)
        self.assertEqual(res.status, "FAILED")
        self.assertEqual(res.payload.get("verdict"), "FAIL")

    def test_verification_math_output(self):
        msg_pass = AgentMessage(
            sender="test_suite",
            receiver="verification_agent",
            goal="Verify math calculation",
            payload={"output": "x**3/3 + C", "expected_type": "math"}
        )
        res_pass = self.coordinator.route_message(msg_pass)
        self.assertEqual(res_pass.status, "SUCCESS")
        self.assertEqual(res_pass.payload.get("verdict"), "PASS")

if __name__ == "__main__":
    unittest.main()
