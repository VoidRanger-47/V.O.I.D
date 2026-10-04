# void_phone/notification_reader.py
"""
V.O.I.D. Mobile Inbound Notification & SMS Reader.
Extracts active notifications and incoming SMS messages from the phone via ADB
content providers and dumpsys, providing situational awareness to V.O.I.D. agents.
"""

from __future__ import annotations

import datetime
import json
import logging
import re
from typing import Any, Dict, List, Optional

from void_phone.adb_bridge import ADBBridge

logger = logging.getLogger("VOID.NotificationReader")


class PhoneNotificationReader:
    """
    Reads active phone notifications, heads-up status alerts, and SMS inbox records.
    """
    _instance: Optional[PhoneNotificationReader] = None

    def __init__(self, bridge: Optional[ADBBridge] = None):
        self.bridge = bridge or ADBBridge.get_instance()

    @classmethod
    def get_instance(cls) -> PhoneNotificationReader:
        if cls._instance is None:
            cls._instance = PhoneNotificationReader()
        return cls._instance

    def is_device_connected(self, serial: Optional[str] = None) -> bool:
        """Check if target or any device is currently online."""
        return self.bridge.is_connected(serial)

    def get_recent_sms(self, limit: int = 5, serial: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves recent incoming SMS messages from the Android telephony provider.
        """
        target = self.bridge.get_active_device_serial(serial)
        if not target or not self.bridge.is_connected(target):
            return {
                "success": False,
                "error": "No Android device connected over ADB.",
                "messages": []
            }

        messages: List[Dict[str, Any]] = []

        # 1. Primary method: Termux API termux-sms-list (clean JSON)
        termux_cmd = f"termux-sms-list -l {limit} 2>/dev/null"
        code, t_out, _ = self.bridge.shell(termux_cmd, serial=target, timeout=6.0)
        if code == 0 and t_out.strip().startswith("["):
            try:
                data = json.loads(t_out)
                for item in data[:limit]:
                    messages.append({
                        "sender": item.get("number", "Unknown"),
                        "date": item.get("received", ""),
                        "body": item.get("body", ""),
                        "read": item.get("read", True)
                    })
                if messages:
                    return {"success": True, "source": "termux_api", "messages": messages}
            except Exception:
                pass

        # 2. Secondary method: Android Content Provider query
        content_cmd = (
            f"content query --uri content://sms/inbox "
            f"--projection address,date,body,read "
            f"--sort 'date DESC'"
        )
        code, c_out, err = self.bridge.shell(content_cmd, serial=target, timeout=8.0)
        if code == 0 and "Row:" in c_out:
            parsed = self._parse_sms_content_rows(c_out, limit=limit)
            return {"success": True, "source": "content_provider", "messages": parsed}

        # If permissions prevented reading
        if "permission" in c_out.lower() or "permission" in err.lower():
            return {
                "success": False,
                "error": "SMS permission denied by Android. Grant 'READ_SMS' permission via ADB or use Termux:API.",
                "messages": []
            }

        return {
            "success": True,
            "source": "content_provider",
            "messages": messages,
            "raw": c_out.strip()
        }

    def _parse_sms_content_rows(self, raw_output: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Parses ADB 'content query' output rows into structured dicts."""
        results: List[Dict[str, Any]] = []
        rows = raw_output.split("Row: ")
        for row in rows:
            if not row.strip():
                continue
            sender_m = re.search(r"address=([^,\n]+)", row)
            date_m = re.search(r"date=(\d+)", row)
            read_m = re.search(r"read=(\d+)", row)
            # Body may contain commas, extract from body= to end of line or next field
            body_m = re.search(r"body=(.*)", row)

            sender = sender_m.group(1).strip() if sender_m else "Unknown"
            timestamp_ms = int(date_m.group(1)) if date_m else None
            date_str = ""
            if timestamp_ms:
                try:
                    dt = datetime.datetime.fromtimestamp(timestamp_ms / 1000.0)
                    date_str = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    date_str = str(timestamp_ms)

            body = ""
            if body_m:
                raw_body = body_m.group(1).strip()
                # Clean trailing row artifacts if present
                body = re.sub(r",\s*(read=\d+|date=\d+|address=[^,\n]+)", "", raw_body).strip()

            results.append({
                "sender": sender,
                "date": date_str,
                "body": body,
                "read": read_m.group(1) == "1" if read_m else True
            })
            if len(results) >= limit:
                break

        return results

    def get_active_notifications(self, limit: int = 10, serial: Optional[str] = None) -> Dict[str, Any]:
        """
        Extracts active notifications currently posted in the Android shade.
        """
        target = self.bridge.get_active_device_serial(serial)
        if not target or not self.bridge.is_connected(target):
            return {
                "success": False,
                "error": "No Android device connected over ADB.",
                "notifications": []
            }

        # 1. Primary: Termux API termux-notification-list
        code, t_out, _ = self.bridge.shell("termux-notification-list 2>/dev/null", serial=target, timeout=6.0)
        if code == 0 and t_out.strip().startswith("["):
            try:
                data = json.loads(t_out)
                parsed = []
                for item in data[:limit]:
                    parsed.append({
                        "package": item.get("packageName", "system"),
                        "title": item.get("title", ""),
                        "text": item.get("content", ""),
                        "when": item.get("when", "")
                    })
                return {"success": True, "source": "termux_api", "notifications": parsed}
            except Exception:
                pass

        # 2. Secondary: Android dumpsys notification
        code, out, _ = self.bridge.shell("dumpsys notification --noredact", serial=target, timeout=8.0)
        if code != 0 or not out:
            # Fallback without --noredact on older Android
            code, out, _ = self.bridge.shell("dumpsys notification", serial=target, timeout=8.0)

        notifications = self._parse_dumpsys_notifications(out, limit=limit)
        return {
            "success": True,
            "source": "dumpsys",
            "notifications": notifications
        }

    def _parse_dumpsys_notifications(self, dumpsys_text: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Extracts package, title, and preview text from dumpsys notification output."""
        items: List[Dict[str, Any]] = []
        records = dumpsys_text.split("NotificationRecord(")

        for rec in records[1:]:
            # Extract pkg name: pkg=com.whatsapp or 0:com.whatsapp/0x...
            pkg_m = re.search(r"pkg=([a-zA-Z0-9_\.]+)", rec) or re.search(r":([a-zA-Z0-9_\.]+)/0x", rec)
            pkg = pkg_m.group(1) if pkg_m else "system"

            # Filter out persistent background services and system noisy notifications
            if pkg in ["android", "com.android.systemui"] and "tickerText=null" in rec:
                continue

            # Extract title & text
            title_m = re.search(r"android.title=String\s*\((.*?)\)", rec) or re.search(r"android.title=\s*([^\n,]+)", rec)
            text_m = re.search(r"android.text=String\s*\((.*?)\)", rec) or re.search(r"android.text=\s*([^\n,]+)", rec)

            title = title_m.group(1).strip() if title_m else ""
            text = text_m.group(1).strip() if text_m else ""

            if not title and not text:
                ticker_m = re.search(r"tickerText=([^\n,]+)", rec)
                if ticker_m and ticker_m.group(1) != "null":
                    text = ticker_m.group(1).strip()

            if title or text:
                items.append({
                    "package": pkg,
                    "title": title,
                    "text": text
                })
            if len(items) >= limit:
                break

        return items

    def get_unread_digest(self, serial: Optional[str] = None) -> str:
        """
        Creates a concise natural language briefing of pending phone communications.
        Ideal for V.O.I.D.'s Morning Briefing or conversational audio updates.
        """
        sms_res = self.get_recent_sms(limit=3, serial=serial)
        notif_res = self.get_active_notifications(limit=5, serial=serial)

        lines: List[str] = []
        lines.append("📱 **Mobile Status Briefing:**")

        sms_list = sms_res.get("messages", [])
        if sms_list:
            lines.append(f"\n💬 Recent SMS ({len(sms_list)}):")
            for msg in sms_list:
                sender = msg.get("sender", "Unknown")
                body = msg.get("body", "")[:60]
                lines.append(f"- From {sender}: \"{body}\"")
        else:
            lines.append("\n💬 No recent unread SMS.")

        notifs = notif_res.get("notifications", [])
        if notifs:
            lines.append(f"\n🔔 Active Notifications ({len(notifs)}):")
            for n in notifs:
                pkg = n.get("package", "").split(".")[-1].capitalize()
                title = n.get("title", "")
                text = n.get("text", "")[:50]
                lines.append(f"- [{pkg}] {title}: {text}")
        else:
            lines.append("\n🔔 Notification tray is clear.")

        return "\n".join(lines)


# Global Singleton Instance
phone_reader = PhoneNotificationReader.get_instance()
