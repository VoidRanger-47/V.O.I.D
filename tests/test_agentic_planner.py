import unittest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from skills.agentic import build_agent_plan

class TestAgenticPlanner(unittest.TestCase):
    def test_search_intent_triggers_search_tool(self):
        plan = build_agent_plan("What is the latest news about AI?")
        self.assertTrue(plan["needs_search"])
        self.assertIn("web_search", plan["tool_names"])

    def test_coding_intent_triggers_coding_context(self):
        plan = build_agent_plan("Debug this Python NameError in my function")
        self.assertTrue(plan["needs_coding"])
        self.assertTrue(plan["needs_generation"])

    def test_memory_intent_triggers_memory_retrieval(self):
        plan = build_agent_plan("Use my saved preferences and remember that I like concise answers")
        self.assertTrue(plan["needs_memory"])

if __name__ == "__main__":
    unittest.main()
