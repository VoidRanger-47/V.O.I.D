"""
plugins/gmail_analyzer/plugin.py
Main Gmail Analyzer Plugin Entrypoint for V.O.I.D.
Inherits from PluginBase and registers with ToolRegistry.
"""

import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple

from core.plugin_manager import PluginBase, PluginMetadata
from plugins.gmail_analyzer.gmail_engine import GmailEngine

logger = logging.getLogger("VOID.GmailPlugin")


class GmailAnalyzerPlugin(PluginBase):
    """
    V.O.I.D. Gmail Intelligence & Inbox Analysis Plugin.
    """
    def __init__(self, metadata: PluginMetadata, plugin_dir: str):
        super().__init__(metadata, plugin_dir)
        self.engine: Optional[GmailEngine] = None

    def initialize(self, context: Dict[str, Any]) -> bool:
        self.engine = GmailEngine(self.config)
        logger.info(f"[GmailPlugin] Initialized. Configured: {self.engine.is_configured()} (Demo Mode: {self.engine.demo_mode})")
        return True

    def can_handle(self, query: str) -> bool:
        if not query:
            return False
        low = query.lower().strip()

        # Direct triggers
        email_keywords = [
            "gmail", "my email", "my emails", "check email", "check emails",
            "inbox", "unread email", "unread emails", "analyze my email",
            "analyze my gmail", "summarize my email", "search email",
            "search emails", "email summary", "mail status", "any urgent email"
        ]
        
        # Avoid false positives for general coding or web searches like "how to send email in python"
        coding_contexts = ["write python", "code to send", "def send_email", "how to send", "script to send", "library for email"]
        if any(c in low for c in coding_contexts):
            return False

        return any(k in low for k in email_keywords)

    def handle(self, query: str, **kwargs) -> Tuple[Optional[str], str]:
        if not self.engine:
            self.engine = GmailEngine(self.config)

        low = query.lower().strip()

        # 1. Connection / Status check
        if any(k in low for k in ["gmail status", "email status", "test gmail", "test email connection"]):
            ok, msg = self.engine.test_connection()
            status_tag = "✅ ONLINE" if ok else "⚠️ UNCONFIGURED / OFFLINE"
            res = (
                f"### 📧 V.O.I.D. Gmail Connection Status\n"
                f"- **Status**: {status_tag}\n"
                f"- **Configured Address**: `{self.engine.email_address or 'None'}`\n"
                f"- **IMAP Server**: `{self.engine.imap_server}:{self.engine.imap_port}`\n"
                f"- **Detail**: {msg}\n\n"
                f"> 💡 *To update credentials, edit `plugins/gmail_analyzer/config.json`.*"
            )
            return res, "gmail_status"

        # 2. Search query (e.g. "search email for invoice", "search emails from amazon")
        search_match = re.search(r"search\s+(?:my\s+)?emails?\s+(?:for|about|with|from)\s+([\"']?)(.+?)\1$", query, re.IGNORECASE)
        if search_match:
            search_term = search_match.group(2).strip()
            emails = self.engine.fetch_emails(search_query=search_term, limit=10)
            return self.engine.analyze_inbox(emails, custom_query=search_term), "gmail_search"

        # 3. Unread query (e.g. "check unread emails", "any unread mail", "read unread emails")
        if any(k in low for k in ["unread", "new email", "new emails", "latest unread"]):
            emails = self.engine.fetch_emails(unread_only=True, limit=10)
            return self.engine.analyze_inbox(emails), "gmail_unread"

        # 4. Urgent / Action items query (e.g. "any urgent emails", "action items in my mail")
        if any(k in low for k in ["urgent", "action item", "priority", "critical"]):
            emails = self.engine.fetch_emails(limit=15)
            urgent_emails = [e for e in emails if e["urgency"] in ["HIGH", "MEDIUM"]]
            if urgent_emails:
                return self.engine.analyze_inbox(urgent_emails), "gmail_urgent"
            return "✅ **No urgent or high-priority emails detected in your inbox.**", "gmail_urgent"

        # 5. General inbox analysis (e.g. "analyze my gmail", "summarize my emails", "check my inbox")
        emails = self.engine.fetch_emails(limit=15)
        return self.engine.analyze_inbox(emails), "gmail_analyzer"

    def get_tools(self) -> List[Any]:
        """
        Exposes Gmail tools to V.O.I.D.'s ToolRegistry.
        """
        from core.security import PermissionLevel
        from core.tool_registry import Tool

        return [
            Tool(
                name="gmail_analyzer",
                description="Analyze and generate executive briefing of Gmail inbox, categorize messages, and extract action items",
                permission_level=PermissionLevel.LEVEL_6_NETWORK,
                risk_level="LOW",
                execute_func=lambda query="": self.handle(query or "analyze my gmail")[0]
            ),
            Tool(
                name="gmail_unread_check",
                description="Fetch and summarize all unread emails currently in Gmail inbox",
                permission_level=PermissionLevel.LEVEL_6_NETWORK,
                risk_level="LOW",
                execute_func=lambda query="": self.handle("check unread emails")[0]
            ),
            Tool(
                name="gmail_search",
                description="Search Gmail inbox by keywords, senders, or subject terms",
                permission_level=PermissionLevel.LEVEL_6_NETWORK,
                risk_level="LOW",
                execute_func=lambda term: self.handle(f"search emails for {term}")[0]
            )
        ]

    def get_status(self) -> Dict[str, Any]:
        base_status = super().get_status()
        base_status.update({
            "configured": bool(self.engine and self.engine.is_configured()),
            "email": self.engine.email_address if self.engine else "",
            "demo_mode": self.engine.demo_mode if self.engine else False,
        })
        return base_status
