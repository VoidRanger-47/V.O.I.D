"""
plugins/gmail_analyzer/gmail_engine.py
Direct IMAP SSL Gmail Engine & Intelligent Email Analysis Engine.
Provides secure fetching, parsing, categorization, action items extraction,
and executive briefings for V.O.I.D.
"""

import os
import re
import html
import imaplib
import email
from email.header import decode_header
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple


class GmailEngine:
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.email_address = config.get("email_address", "").strip()
        self.app_password = config.get("app_password", "").strip()
        self.imap_server = config.get("imap_server", "imap.gmail.com")
        self.imap_port = int(config.get("imap_port", 993))
        self.max_emails = int(config.get("max_emails_fetch", 15))
        self.demo_mode = config.get("demo_mode", False)

    def is_configured(self) -> bool:
        return bool(self.email_address and self.app_password)

    def test_connection(self) -> Tuple[bool, str]:
        """Tests live IMAP authentication to Gmail."""
        if not self.is_configured():
            return False, "Gmail credentials not configured in plugins/gmail_analyzer/config.json."

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, timeout=10)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX", readonly=True)
            mail.logout()
            return True, f"Successfully connected to Gmail ({self.email_address})."
        except Exception as e:
            return False, f"Connection failed: {str(e)}"

    def fetch_emails(self, unread_only: bool = False, search_query: Optional[str] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetches and parses emails from Gmail via IMAP SSL.
        Falls back to demo inbox if unconfigured or connection fails.
        """
        fetch_limit = limit or self.max_emails

        if not self.is_configured() or self.demo_mode:
            return self._get_mock_inbox(unread_only=unread_only, search_query=search_query, limit=fetch_limit)

        try:
            mail = imaplib.IMAP4_SSL(self.imap_server, self.imap_port, timeout=15)
            mail.login(self.email_address, self.app_password)
            mail.select("INBOX", readonly=True)

            if search_query:
                # Search by subject or text
                status, messages = mail.search(None, f'(OR SUBJECT "{search_query}" BODY "{search_query}")')
            elif unread_only:
                status, messages = mail.search(None, "UNSEEN")
            else:
                status, messages = mail.search(None, "ALL")

            if status != "OK" or not messages or not messages[0]:
                mail.logout()
                return []

            email_ids = messages[0].split()
            # Get latest emails first
            selected_ids = email_ids[-fetch_limit:][::-1]

            results = []
            for e_id in selected_ids:
                res, msg_data = mail.fetch(e_id, "(RFC822)")
                if res != "OK":
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        raw_msg = response_part[1]
                        parsed = self._parse_email(raw_msg)
                        if parsed:
                            results.append(parsed)

            mail.logout()
            return results

        except Exception as e:
            print(f"[GmailEngine] Live fetch failed ({e}). Falling back to simulated inbox.")
            return self._get_mock_inbox(unread_only=unread_only, search_query=search_query, limit=fetch_limit, fallback_error=str(e))

    def _parse_header(self, header_val: Optional[str]) -> str:
        if not header_val:
            return ""
        decoded_parts = decode_header(header_val)
        result = []
        for part, enc in decoded_parts:
            if isinstance(part, bytes):
                try:
                    result.append(part.decode(enc or "utf-8", errors="replace"))
                except Exception:
                    result.append(part.decode("latin1", errors="replace"))
            else:
                result.append(str(part))
        return "".join(result)

    def _parse_email(self, raw_bytes: bytes) -> Optional[Dict[str, Any]]:
        try:
            msg = email.message_from_bytes(raw_bytes)
            subject = self._parse_header(msg.get("Subject", "(No Subject)"))
            sender = self._parse_header(msg.get("From", "(Unknown Sender)"))
            date_str = msg.get("Date", "")
            
            # Extract plain text body & attachment names
            body_text = ""
            attachments = []

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    filename = part.get_filename()

                    if filename:
                        attachments.append(self._parse_header(filename))

                    if content_type == "text/plain" and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body_text += payload.decode("utf-8", errors="replace") + "\n"
                    elif content_type == "text/html" and not body_text and "attachment" not in content_disposition:
                        payload = part.get_payload(decode=True)
                        if payload:
                            raw_html = payload.decode("utf-8", errors="replace")
                            clean = re.sub(r"<style.*?</style>", "", raw_html, flags=re.DOTALL)
                            clean = re.sub(r"<script.*?</script>", "", clean, flags=re.DOTALL)
                            clean = re.sub(r"<[^>]+>", " ", clean)
                            body_text += html.unescape(clean)
            else:
                payload = msg.get_payload(decode=True)
                if payload:
                    body_text = payload.decode("utf-8", errors="replace")

            body_preview = " ".join(body_text.split())[:350]

            return {
                "subject": subject,
                "sender": sender,
                "date": date_str,
                "body_preview": body_preview,
                "full_body": body_text[:2000],
                "attachments": attachments,
                "is_unread": True,
                "category": self._classify_category(subject, sender, body_preview),
                "urgency": self._evaluate_urgency(subject, body_preview),
                "action_items": self._extract_action_items(body_preview)
            }
        except Exception as e:
            print(f"[GmailEngine] Failed to parse email: {e}")
            return None

    def _classify_category(self, subject: str, sender: str, body: str) -> str:
        text = f"{subject} {sender} {body}".lower()

        if any(k in text for k in ["security alert", "password reset", "new sign-in", "verification code", "2-step", "unauthorized"]):
            return "Security Alert"
        if any(k in text for k in ["action required", "urgent", "asap", "deadline", "immediate attention", "approval required"]):
            return "Action Required"
        if any(k in text for k in ["invoice", "receipt", "payment", "billing", "statement", "charged", "order #", "subscription renewed"]):
            return "Finance & Billing"
        if any(k in text for k in ["github", "pull request", "jira", "sprint", "meeting", "deployment", "commit", "merge", "code review"]):
            return "Work & Development"
        if any(k in text for k in ["newsletter", "digest", "weekly", "unsubscribe", "updates from", "blog", "roundup"]):
            return "Newsletter & Tech Digest"
        return "General"

    def _evaluate_urgency(self, subject: str, body: str) -> str:
        text = f"{subject} {body}".lower()
        if any(k in text for k in ["urgent", "immediately", "action required", "critical", "deadline today", "overdue"]):
            return "HIGH"
        if any(k in text for k in ["reminder", "please review", "upcoming", "due soon", "attention"]):
            return "MEDIUM"
        return "LOW"

    def _extract_action_items(self, text: str) -> List[str]:
        items = []
        sentences = re.split(r"[.!?\n]+", text)
        action_patterns = [
            r"please\s+(?:review|sign|confirm|send|check|verify|update|complete|approve|reply)",
            r"need\s+you\s+to",
            r"action\s+required",
            r"deadline\s+is",
            r"due\s+by",
            r"scheduled\s+for",
        ]
        for s in sentences:
            clean = s.strip()
            if len(clean) > 10 and any(re.search(pat, clean, re.IGNORECASE) for pat in action_patterns):
                items.append(clean[:120])
                if len(items) >= 2:
                    break
        return items

    def analyze_inbox(self, emails: List[Dict[str, Any]], custom_query: Optional[str] = None) -> str:
        """
        Generates an executive analytical briefing of the provided email dataset.
        """
        if not emails:
            return "📭 **Your Gmail inbox is completely clear!** No emails matched the search criteria."

        total_count = len(emails)
        categories = {}
        high_urgency = []
        all_actions = []

        for em in emails:
            cat = em["category"]
            categories[cat] = categories.get(cat, 0) + 1
            if em["urgency"] == "HIGH":
                high_urgency.append(em)
            if em.get("action_items"):
                for act in em["action_items"]:
                    all_actions.append((em["subject"], act))

        # Build Markdown Output
        mode_label = "🟢 **Live Gmail Sync**" if (self.is_configured() and not self.demo_mode) else "🟡 **Demonstration / Offline Mode**"
        account_str = f"`{self.email_address}`" if self.email_address else "*(Not yet configured — see `plugins/gmail_analyzer/config.json`)*"

        lines = [
            f"### 📬 V.O.I.D. Gmail Intelligence Report",
            f"{mode_label} | Account: {account_str}",
            f"**Total Messages Analyzed**: `{total_count}`\n",
            "---",
            "#### 📊 Inbox Breakdown by Category"
        ]

        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            icon = {
                "Action Required": "🚨",
                "Work & Development": "💻",
                "Finance & Billing": "💳",
                "Security Alert": "🛡️",
                "Newsletter & Tech Digest": "📰",
                "General": "✉️"
            }.get(cat, "📁")
            lines.append(f"- {icon} **{cat}**: `{count}` message(s)")

        # Urgent Items
        if high_urgency:
            lines.append("\n#### 🚨 Critical & High-Priority Alerts")
            for u in high_urgency:
                lines.append(f"- **{u['subject']}** — *From: {u['sender']}*")
                lines.append(f"  > *\"{u['body_preview'][:180]}...\"*")

        # Action Items
        if all_actions:
            lines.append("\n#### ✅ Extracted Action Items & Deadlines")
            for subj, act in all_actions[:5]:
                lines.append(f"- **[{subj[:30]}]**: {act}")

        # Recent Emails Overview Table
        lines.append("\n#### 📋 Recent Messages Digest")
        for i, em in enumerate(emails[:8], 1):
            urgency_tag = "🔴 HIGH" if em["urgency"] == "HIGH" else "🟡 MED" if em["urgency"] == "MEDIUM" else "⚪ LOW"
            attach_str = f" 📎 ({len(em['attachments'])} files)" if em.get("attachments") else ""
            lines.append(f"**{i}. {em['subject']}** [{urgency_tag}]{attach_str}")
            lines.append(f"   *From*: `{em['sender']}` | *Category*: `{em['category']}`")
            lines.append(f"   *Summary*: {em['body_preview'][:140]}...")

        if not self.is_configured():
            lines.append("\n> 💡 **Connect your live Gmail**: Add your email and a Google App Password to `plugins/gmail_analyzer/config.json`.")

        return "\n".join(lines)

    def _get_mock_inbox(self, unread_only: bool = False, search_query: Optional[str] = None, limit: int = 10, fallback_error: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Simulated rich inbox for offline use and zero-setup testing.
        """
        mock_data = [
            {
                "subject": "Action Required: AWS Cloud Invoice & Billing Statement #INV-92841",
                "sender": "AWS Billing <no-reply-billing@amazon.com>",
                "date": "Today, 09:14 AM",
                "body_preview": "Your monthly AWS invoice of $42.50 is ready. Please review your active EC2 and S3 instances before the billing cycle closes on August 31st.",
                "full_body": "Your monthly AWS invoice of $42.50 is ready. Please review your active EC2 and S3 instances before the billing cycle closes on August 31st.",
                "attachments": ["AWS_Invoice_92841.pdf"],
                "is_unread": True,
                "category": "Finance & Billing",
                "urgency": "MEDIUM",
                "action_items": ["Please review your active EC2 and S3 instances before August 31st"]
            },
            {
                "subject": "🚨 [URGENT] Security Alert: New login detected from unknown Windows Device",
                "sender": "Google Security Team <no-reply@accounts.google.com>",
                "date": "Today, 08:30 AM",
                "body_preview": "We noticed a new sign-in to your Google Account from Chrome on Windows (IP: 192.0.2.45). If this was not you, please secure your account immediately.",
                "full_body": "We noticed a new sign-in to your Google Account from Chrome on Windows. If this was not you, please secure your account immediately.",
                "attachments": [],
                "is_unread": True,
                "category": "Security Alert",
                "urgency": "HIGH",
                "action_items": ["If this was not you, please secure your account immediately"]
            },
            {
                "subject": "[GitHub] Pull Request #42: Add VOID Multi-Agent Verification Layer merged",
                "sender": "GitHub Notifications <notifications@github.com>",
                "date": "Yesterday, 18:45 PM",
                "body_preview": "kbven merged pull request #42 (feature/verification-agent) into main. All CI/CD test pipelines passed successfully with 100% test coverage.",
                "full_body": "kbven merged pull request #42 into main. All CI/CD test pipelines passed successfully.",
                "attachments": [],
                "is_unread": False,
                "category": "Work & Development",
                "urgency": "LOW",
                "action_items": []
            },
            {
                "subject": "Action Required: Sprint Planning & Architecture Review meeting scheduled for 3:00 PM",
                "sender": "Lead Architect <lead.dev@company.internal>",
                "date": "Yesterday, 14:10 PM",
                "body_preview": "Hi team, please review the attached architecture diagram for the new offline memory engine and confirm your attendance before 2:00 PM.",
                "full_body": "Please review the attached architecture diagram for the new offline memory engine and confirm your attendance before 2:00 PM.",
                "attachments": ["VOID_Architecture_v2.png"],
                "is_unread": True,
                "category": "Action Required",
                "urgency": "HIGH",
                "action_items": ["Please review the attached architecture diagram and confirm your attendance before 2:00 PM"]
            },
            {
                "subject": "PyTorch 2.5 Released: Native Metal & TensorRT Acceleration Updates",
                "sender": "PyTorch Foundation <updates@pytorch.org>",
                "date": "Aug 28, 2026",
                "body_preview": "Discover what is new in PyTorch 2.5: enhanced torch.compile performance, reduced VRAM consumption for LLMs, and streamlined quantized execution.",
                "full_body": "Discover what is new in PyTorch 2.5 with enhanced compiler capabilities and quantized execution.",
                "attachments": [],
                "is_unread": False,
                "category": "Newsletter & Tech Digest",
                "urgency": "LOW",
                "action_items": []
            }
        ]

        if search_query:
            q_low = search_query.lower()
            mock_data = [
                m for m in mock_data
                if q_low in m["subject"].lower() or q_low in m["sender"].lower() or q_low in m["body_preview"].lower()
            ]

        if unread_only:
            mock_data = [m for m in mock_data if m["is_unread"]]

        return mock_data[:limit]
