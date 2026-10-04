# tests/test_gmail_analyzer.py
import unittest
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from plugins.gmail_analyzer.gmail_engine import GmailEngine
from plugins.gmail_analyzer.plugin import GmailAnalyzerPlugin
from core.plugin_manager import PluginMetadata


class TestGmailAnalyzer(unittest.TestCase):
    def setUp(self):
        self.config = {
            "email_address": "",
            "app_password": "",
            "imap_server": "imap.gmail.com",
            "imap_port": 993,
            "max_emails_fetch": 10,
            "demo_mode": True
        }
        self.engine = GmailEngine(self.config)
        self.metadata = PluginMetadata(
            id="gmail_analyzer",
            name="Gmail Analyzer",
            version="1.0.0",
            description="Unit test"
        )
        self.plugin = GmailAnalyzerPlugin(self.metadata, os.path.dirname(__file__))
        self.plugin.initialize({})

    def test_mock_inbox_fetch(self):
        emails = self.engine.fetch_emails(limit=5)
        self.assertEqual(len(emails), 5)
        first = emails[0]
        self.assertIn("subject", first)
        self.assertIn("sender", first)
        self.assertIn("category", first)
        self.assertIn("urgency", first)

    def test_unread_filter(self):
        unread_emails = self.engine.fetch_emails(unread_only=True)
        self.assertTrue(all(e["is_unread"] for e in unread_emails))

    def test_search_filter(self):
        results = self.engine.fetch_emails(search_query="Invoice")
        self.assertTrue(len(results) > 0)
        self.assertTrue(any("invoice" in e["subject"].lower() for e in results))

    def test_inbox_analysis_report(self):
        emails = self.engine.fetch_emails(limit=5)
        report = self.engine.analyze_inbox(emails)
        self.assertIn("V.O.I.D. Gmail Intelligence Report", report)
        self.assertIn("Inbox Breakdown by Category", report)
        self.assertIn("Total Messages Analyzed", report)

    def test_categorization(self):
        self.assertEqual(self.engine._classify_category("New sign-in from Chrome", "Google", "Alert"), "Security Alert")
        self.assertEqual(self.engine._classify_category("Your Monthly Invoice #123", "AWS", "Billing"), "Finance & Billing")
        self.assertEqual(self.engine._classify_category("[PR] Merge main", "GitHub", "Commit review"), "Work & Development")

    def test_action_item_extraction(self):
        body = "Hi team. Please review the attached document and confirm your attendance by Friday."
        actions = self.engine._extract_action_items(body)
        self.assertTrue(len(actions) > 0)
        self.assertTrue(any("please review" in a.lower() for a in actions))

    def test_plugin_handles_queries(self):
        # 1. General analysis
        res, tag = self.plugin.handle("analyze my emails")
        self.assertEqual(tag, "gmail_analyzer")
        self.assertIn("Gmail Intelligence Report", res)

        # 2. Unread query
        res, tag = self.plugin.handle("check my unread emails")
        self.assertEqual(tag, "gmail_unread")

        # 3. Search query
        res, tag = self.plugin.handle("search emails for AWS")
        self.assertEqual(tag, "gmail_search")
        self.assertIn("AWS", res)

        # 4. Status query
        res, tag = self.plugin.handle("gmail status")
        self.assertEqual(tag, "gmail_status")
        self.assertIn("Gmail Connection Status", res)

    def test_tool_registration(self):
        tools = self.plugin.get_tools()
        self.assertEqual(len(tools), 3)
        tool_names = [t.name for t in tools]
        self.assertIn("gmail_analyzer", tool_names)
        self.assertIn("gmail_unread_check", tool_names)
        self.assertIn("gmail_search", tool_names)


if __name__ == "__main__":
    unittest.main()
