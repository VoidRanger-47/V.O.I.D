# void_learning/content_cleaner.py
"""
Secure Web Content Crawler & Cleaner for V.O.I.D.
Provides:
- Safe URL retrieval with strict timeouts (5s) and payload caps (500KB)
- HTML-to-text extraction using BeautifulSoup (strips scripts, styles, forms, navs)
- Security & Prompt Injection Quarantine: Sanitizes text so web instructions are treated as inert data, NEVER commands.
"""

import re
import html
import urllib.request
from typing import Dict, Any, Optional
from bs4 import BeautifulSoup

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 VOID-Research/1.0"
MAX_CONTENT_BYTES = 512 * 1024  # 500 KB limit to protect local RAM

# Patterns associated with malicious prompt injection on untrusted web pages
INJECTION_PATTERNS = [
    r"(?i)\bignore\s+(all\s+)?(previous|prior|above|system)\s+instructions?\b",
    r"(?i)\byou\s+are\s+now\s+in\s+(developer|dan|jailbreak)\s+mode\b",
    r"(?i)\bdisregard\s+(any|all)\s+constraints?\b",
    r"(?i)\bexecute\s+(this\s+)?(command|script|code|shell|terminal)\s+immediately\b",
    r"(?i)\bdelete\s+(your\s+)?(database|files|memory)\b",
    r"(?i)\bdo\s+not\s+tell\s+the\s+user\b"
]


def sanitize_prompt_injection(text: str) -> str:
    """
    Quarantines or disarms adversarial prompt injection directives inside web text,
    ensuring internet content is strictly DATA, NEVER AUTHORITY.
    """
    cleaned = text
    for pat in INJECTION_PATTERNS:
        cleaned = re.sub(pat, "[UNTRUSTED_WEB_DIRECTIVE_NEUTRALIZED]", cleaned)
    return cleaned


def clean_web_content(raw_html: str, max_chars: int = 12000) -> str:
    """
    Extracts readable text from raw HTML using BeautifulSoup.
    Strips boilerplate, scripts, ads, and navigation noise.
    """
    if not raw_html:
        return ""

    soup = BeautifulSoup(raw_html, "html.parser")

    # Remove non-content tags
    for element in soup(["script", "style", "nav", "footer", "header", "aside", "noscript", "form", "svg"]):
        element.decompose()

    # Extract main content areas if present
    main_node = soup.find("main") or soup.find("article") or soup.find("div", class_=re.compile(r"content|article|body|post", re.I)) or soup.body or soup

    text = main_node.get_text(separator="\n")

    # Clean whitespace and HTML entities
    text = html.unescape(text)
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    non_empty = [line for line in lines if len(line) > 15]

    joined = "\n\n".join(non_empty)
    sanitized = sanitize_prompt_injection(joined)

    return sanitized[:max_chars].strip()


def fetch_and_clean_page(url: str, timeout_seconds: float = 5.0) -> Dict[str, Any]:
    """
    Safely fetches a web page with timeout and size caps, returning cleaned readable text.
    """
    result = {
        "url": url,
        "success": False,
        "title": "",
        "content": "",
        "char_count": 0,
        "error": None
    }

    if not url or not url.startswith(("http://", "https://")):
        result["error"] = "Invalid URL protocol"
        return result

    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,text/plain;q=0.9",
                "Accept-Language": "en-US,en;q=0.8"
            }
        )

        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            content_type = resp.headers.get("Content-Type", "").lower()
            if "text/html" not in content_type and "text/plain" not in content_type:
                result["error"] = f"Unsupported content type: {content_type}"
                return result

            raw_bytes = resp.read(MAX_CONTENT_BYTES)
            charset = resp.headers.get_content_charset() or "utf-8"
            raw_text = raw_bytes.decode(charset, errors="replace")

        # Parse title
        soup = BeautifulSoup(raw_text[:8000], "html.parser")
        title = soup.title.string.strip() if (soup.title and soup.title.string) else ""

        cleaned = clean_web_content(raw_text)

        result["success"] = True
        result["title"] = title
        result["content"] = cleaned
        result["char_count"] = len(cleaned)
        return result

    except Exception as e:
        result["error"] = str(e)
        return result
