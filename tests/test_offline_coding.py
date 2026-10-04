"""
Unit tests for V.O.I.D. 100% Offline Neuro-Symbolic Coding Intelligence.
Tests AST validation, symbol indexing, algorithmic pattern retrieval,
and self-healing code execution.
"""

import unittest
from skills.coding_engine import (
    ASTCodeValidator,
    WorkspaceSymbolIndexer,
    LocalCodePatternLibrary,
    SelfHealingExecutionLoop,
    coding_engine
)
from skills.coding import is_coding_request, handle_coding_query, execute_and_verify_code
from core.agents.coding_agent import CodingAgent
from core.agents.protocol import AgentMessage


class TestASTCodeValidator(unittest.TestCase):
    def setUp(self):
        self.validator = ASTCodeValidator()

    def test_valid_syntax(self):
        code = "def add(a: int, b: int) -> int:\n    return a + b\n"
        is_valid, err, line = self.validator.validate_syntax(code)
        self.assertTrue(is_valid)
        self.assertIsNone(err)

    def test_invalid_syntax_detection(self):
        broken_code = "def broken(a, b\n    return a + b"
        is_valid, err, line = self.validator.validate_syntax(broken_code)
        self.assertFalse(is_valid)
        self.assertIsNotNone(err)

    def test_structure_analysis(self):
        code = (
            "import os\n"
            "from typing import List\n\n"
            "class MathEngine:\n"
            "    \"\"\"Docstring for MathEngine.\"\"\"\n"
            "    def calculate(self, x: int) -> int:\n"
            "        return x * 2\n"
        )
        struct = self.validator.analyze_structure(code)
        self.assertTrue(struct["syntax_valid"])
        self.assertIn("os", struct["imports"])
        self.assertEqual(len(struct["classes"]), 1)
        self.assertEqual(struct["classes"][0]["name"], "MathEngine")
        self.assertTrue(any(f["name"] == "calculate" for f in struct["functions"]))

    def test_auto_repair_syntax_missing_colon(self):
        broken = "def my_func(x)\n    return x * 2"
        repaired = self.validator.auto_repair_syntax(broken, "expected ':'", 1)
        self.assertIn("def my_func(x):", repaired)
        is_valid, _, _ = self.validator.validate_syntax(repaired)
        self.assertTrue(is_valid)


class TestWorkspaceSymbolIndexer(unittest.TestCase):
    def setUp(self):
        self.indexer = WorkspaceSymbolIndexer()

    def test_scan_workspace_finds_symbols(self):
        symbols = self.indexer.scan_workspace()
        self.assertTrue(len(symbols) > 0)

    def test_find_symbol(self):
        matches = self.indexer.find_symbol("CodingAgent")
        self.assertTrue(len(matches) >= 1)
        self.assertEqual(matches[0]["name"], "CodingAgent")
        self.assertEqual(matches[0]["type"], "class")

    def test_get_module_outline(self):
        outline = self.indexer.get_module_outline("skills/coding_engine.py")
        self.assertTrue(outline.get("syntax_valid"))
        self.assertTrue(len(outline.get("classes", [])) >= 3)


class TestLocalCodePatternLibrary(unittest.TestCase):
    def setUp(self):
        self.patterns = LocalCodePatternLibrary()

    def test_find_binary_search_pattern(self):
        pat = self.patterns.find_pattern("write a binary search function")
        self.assertIsNotNone(pat)
        self.assertEqual(pat.get("name"), "binary_search")
        self.assertIn("def binary_search", pat.get("code"))

    def test_find_lru_cache_pattern(self):
        pat = self.patterns.find_pattern("implement an LRU cache data structure")
        self.assertIsNotNone(pat)
        self.assertEqual(pat.get("name"), "lru_cache")

    def test_find_quick_sort_pattern(self):
        pat = self.patterns.find_pattern("quick sort algorithm")
        self.assertIsNotNone(pat)
        self.assertEqual(pat.get("name"), "quick_sort")


class TestSelfHealingExecutionLoop(unittest.TestCase):
    def setUp(self):
        self.healer = SelfHealingExecutionLoop()

    def test_clean_execution(self):
        code = "a = 10\nb = 20\nprint(a + b)"
        res = self.healer.execute_and_heal(code)
        self.assertTrue(res["success"])
        self.assertIn("30", res["output"])

    def test_heal_zero_division_error(self):
        broken_code = "divisor = 0\nresult = 100 / divisor\nprint('Result:', result)"
        res = self.healer.execute_and_heal(broken_code)
        self.assertTrue(res["success"])
        self.assertTrue(len(res["repairs"]) > 0)
        self.assertIn("Result: 0", res["output"])

    def test_heal_syntax_missing_colon(self):
        code = "def double(x)\n    return x * 2\nprint(double(5))"
        res = self.healer.execute_and_heal(code)
        self.assertTrue(res["success"])
        self.assertIn("10", res["output"])


class TestCodingSkillAndAgent(unittest.TestCase):
    def setUp(self):
        self.agent = CodingAgent()

    def test_is_coding_request(self):
        self.assertTrue(is_coding_request("Write a quick sort algorithm"))
        self.assertTrue(is_coding_request("Debug this python function"))
        self.assertTrue(is_coding_request("find function execute_and_verify_code"))

    def test_handle_coding_query_pattern_match(self):
        res = handle_coding_query("binary search algorithm in python")
        self.assertTrue(res.get("handled"))
        self.assertIn("Verified Algorithmic Pattern", res.get("response"))

    def test_handle_coding_query_symbol_search(self):
        res = handle_coding_query("find class CodingAgent")
        self.assertTrue(res.get("handled"))
        self.assertIn("CodingAgent", res.get("response"))

    def test_agent_run_python_self_healing(self):
        msg = AgentMessage(
            sender="test",
            receiver="coding_agent",
            goal="run test code",
            payload={"action": "run_python", "code": "x = [1, 2, 3]\nprint(sum(x))"}
        )
        res_msg = self.agent.process(msg)
        self.assertEqual(res_msg.status, "SUCCESS")
        self.assertIn("6", str(res_msg.result))


if __name__ == "__main__":
    unittest.main()
