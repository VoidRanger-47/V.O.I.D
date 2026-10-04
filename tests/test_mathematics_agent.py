import unittest
from core.agents.mathematics_agent import MathematicsAgent
from core.agents.protocol import AgentMessage, AgentMessageType


class TestMathematicsAgent(unittest.TestCase):
    def setUp(self):
        self.agent = MathematicsAgent()

    def test_arithmetic_calculation(self):
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="Calculate 25 * 4 + 18 / 2",
            payload={"query": "25 * 4 + 18 / 2"}
        )
        response = self.agent.process(msg)
        self.assertEqual(response.status, "SUCCESS")
        self.assertTrue(response.payload.get("verified"))
        self.assertIn("109", response.result)

    def test_algebraic_solving(self):
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="Solve 2*x + 10 = 20",
            payload={"query": "solve 2*x + 10 = 20"}
        )
        response = self.agent.process(msg)
        self.assertEqual(response.status, "SUCCESS")
        self.assertIn("5", response.result)

    def test_symbolic_derivative(self):
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="Derivative of x**3 + 5*x",
            payload={"query": "derivative of x**3 + 5*x"}
        )
        response = self.agent.process(msg)
        self.assertEqual(response.status, "SUCCESS")
        self.assertTrue("3*x**2 + 5" in response.result or "3*x^2 + 5" in response.result)

    def test_symbolic_integration(self):
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="Integrate 3*x**2",
            payload={"query": "integrate 3*x**2"}
        )
        response = self.agent.process(msg)
        self.assertEqual(response.status, "SUCCESS")
        self.assertIn("x**3", response.result)

    def test_matrix_determinant(self):
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="Determinant of [[1, 2], [3, 4]]",
            payload={"query": "determinant of [[1, 2], [3, 4]]"}
        )
        response = self.agent.process(msg)
        self.assertEqual(response.status, "SUCCESS")
        self.assertIn("-2", response.result)

    def test_vector_dot_product(self):
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="Dot product of [1, 2, 3] and [4, 5, 6]",
            payload={"query": "dot product of [1, 2, 3] and [4, 5, 6]"}
        )
        response = self.agent.process(msg)
        self.assertEqual(response.status, "SUCCESS")
        self.assertIn("32", response.result)

    def test_agent_error_handling(self):
        # Malformed math query that causes parser failure
        msg = AgentMessage(
            sender="executive",
            receiver="math_agent",
            goal="calculate ??? +++ //",
            payload={"query": "??? +++ //"}
        )
        response = self.agent.process(msg)
        # Should gracefully return FAILED status or handle error without crashing
        self.assertIn(response.status, ["FAILED", "SUCCESS"])
        if response.status == "FAILED":
            self.assertFalse(response.payload.get("verified", False))


if __name__ == "__main__":
    unittest.main()
