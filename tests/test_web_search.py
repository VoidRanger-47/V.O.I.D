# tests/test_web_search.py
import unittest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from lib.offline_manager import offline_mgr
from skills.web_search import (
    perform_search,
    is_search_request,
    is_explicit_search,
    extract_search_query,
    NO_INTERNET_STATEMENT
)
from core.agents.research_agent import ResearchAgent
from core.agents.protocol import AgentMessage
from core.tool_registry import ToolRegistry
from chat import route_query


class TestWebSearch(unittest.TestCase):
    def setUp(self):
        self.offline_mgr = offline_mgr
        self.research_agent = ResearchAgent()
        self.tools = ToolRegistry.get_instance()

    def test_search_intent_detection(self):
        # Explicit search commands
        self.assertTrue(is_explicit_search("search for quantum computing"))
        self.assertTrue(is_explicit_search("search web for latest news"))
        self.assertTrue(is_explicit_search("search online for weather"))
        self.assertTrue(is_explicit_search("look up population of Tokyo"))
        self.assertTrue(is_explicit_search("google python tutorials"))
        self.assertTrue(is_explicit_search("search: NVIDIA stock price"))

        # General search requests
        self.assertTrue(is_search_request("what is the latest news today?"))
        self.assertTrue(is_search_request("visit https://python.org for details"))
        self.assertTrue(is_search_request("check www.wikipedia.org"))

        # Non-search requests
        self.assertFalse(is_explicit_search("calculate 2 + 2"))
        self.assertFalse(is_search_request("hi"))

    def test_extract_search_query(self):
        self.assertEqual(extract_search_query("search web for Python 3.12 features"), "Python 3.12 features")
        self.assertEqual(extract_search_query("search for quantum computing"), "quantum computing")
        self.assertEqual(extract_search_query("please search online for weather in London"), "weather in London")
        self.assertEqual(extract_search_query("look up machine learning algorithms"), "machine learning algorithms")
        self.assertEqual(extract_search_query("search: artificial intelligence"), "artificial intelligence")

    def test_search_offline_statement(self):
        # Force offline state
        self.offline_mgr.cached_online_state = False
        self.offline_mgr.last_check_time = 9999999999.0

        result = perform_search("latest technology news")
        self.assertIn("No Internet Access", result)
        self.assertIn("[Offline Mode]", result)
        self.assertIn("Live web search is unavailable", result)

    def test_search_online_mocked(self):
        # Simulate online state
        self.offline_mgr.cached_online_state = True
        self.offline_mgr.last_check_time = 9999999999.0

        mock_results = [
            {"title": "Python Website", "body": "Official site of Python programming.", "href": "https://www.python.org"}
        ]

        with patch("skills.web_search.DDGS") as MockDDGS:
            instance = MagicMock()
            instance.__enter__.return_value.text.return_value = mock_results
            MockDDGS.return_value = instance

            result = perform_search("python website")
            self.assertIn("Python Website", result)
            self.assertIn("Official site of Python programming.", result)
            self.assertIn("https://www.python.org", result)

    def test_search_network_exception_fallback(self):
        # Simulate online check passing but DDGS throwing connection error
        self.offline_mgr.cached_online_state = True
        self.offline_mgr.last_check_time = 9999999999.0

        with patch("skills.web_search.DDGS") as MockDDGS:
            instance = MagicMock()
            instance.__enter__.return_value.text.side_effect = ConnectionError("Connection timed out (no internet)")
            MockDDGS.return_value = instance

            result = perform_search("test query")
            self.assertIn("No Internet Access", result)
            self.assertIn("[Offline Mode]", result)

    def test_research_agent_offline(self):
        self.offline_mgr.cached_online_state = False
        self.offline_mgr.last_check_time = 9999999999.0

        msg = AgentMessage(
            sender="test_suite",
            receiver="research_agent",
            goal="search web for AI trends",
            payload={"query": "AI trends"}
        )
        res = self.research_agent.process(msg)
        self.assertEqual(res.status, "OFFLINE")
        self.assertTrue(res.payload.get("offline"))
        self.assertIn("No Internet Access", str(res.result))

    def test_tool_registry_web_search_offline(self):
        self.offline_mgr.cached_online_state = False
        self.offline_mgr.last_check_time = 9999999999.0

        res = self.tools.execute_tool("web_search", "search web for space exploration")
        self.assertIn("No Internet Access", str(res))

    def test_route_query_explicit_search(self):
        """
        Explicit search queries must NOT return raw results directly.
        route_query() should return (None, 'web_search') to signal the LLM
        synthesis path — web results are injected as context for the model
        to analyse and compose a coherent answer from.
        """
        self.offline_mgr.cached_online_state = False
        self.offline_mgr.last_check_time = 9999999999.0

        resp, skill = route_query("search web for latest stocks")
        self.assertEqual(skill, "web_search")
        # resp must be None — the caller (app.py) handles LLM synthesis
        self.assertIsNone(resp, "Explicit search must enter the LLM synthesis path (resp=None)")


if __name__ == "__main__":
    unittest.main()
