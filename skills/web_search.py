# skills/web_search.py
import re
from typing import Optional

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        print("❌ Error: Search backend ('ddgs' or 'duckduckgo_search') not found.")
        DDGS = None

from lib.offline_manager import offline_mgr

NO_INTERNET_STATEMENT = (
    "[No Internet Access] Live web search is unavailable because the system is currently offline. "
    "All local features (AI inference, memory RAG, voice, math solver, document analysis, computer control, and system monitoring) remain fully operational."
)

import html

def perform_search(query: str, max_results: int = 4, force_check: bool = False) -> str:
    """
    Searches the live web using DDGS and returns formatted, unescaped text results with source citations.
    If the system has no internet access, returns an explicit statement of no internet access
    without hanging, retrying, or interrupting local operations.
    """
    clean_q = extract_search_query(query) if is_search_request(query) else query.strip()
    if not clean_q:
        return "⚠️ [Web Search: Please provide a search query.]"

    # Verify internet connectivity
    if offline_mgr.is_offline(force_check=force_check):
        print(f"[Offline Mode] Web search skipped for query: '{clean_q}' (No internet access)")
        return f"[Offline Mode] {NO_INTERNET_STATEMENT}"

    if DDGS is None:
        return "❌ [System Error: Web search backend is not installed.]"

    print(f"[Web Search] Accessing live web for query: '{clean_q}'...")

    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(clean_q, max_results=max_results))
            if not results:
                return f"🔍 [Web Search: No online results found for '{clean_q}'.]"

            results_text = f"🌐 **Web Search Results for '{clean_q}'**:\n\n"
            for i, r in enumerate(results, 1):
                raw_title = r.get('title', 'No Title').strip()
                raw_body = r.get('body', 'No content available').strip()
                href = r.get('href', '').strip()

                title = html.unescape(raw_title)
                body = html.unescape(raw_body).replace("\n", " ")

                results_text += f"{i}. **{title}**\n   {body}\n"
                if href:
                    results_text += f"   🔗 [Source Link]({href})\n"
                results_text += "\n"

            return results_text.strip()

    except Exception as e:
        err_msg = str(e).lower()
        if any(term in err_msg for term in ["connect", "timeout", "network", "offline", "unreachable", "dns", "getaddrinfo", "resolution"]):
            print(f"[Offline Fallback] Network request failed ({e}). Returning no internet statement.")
            return f"[Offline Mode] {NO_INTERNET_STATEMENT}"
        return f"⚠️ [Web Search Error: {str(e)}]"



def is_explicit_search(user_input: str) -> bool:
    """
    Checks if the user explicitly commanded a web search (e.g. 'search for ...', 'google ...').
    """
    text = (user_input or "").strip()
    if len(text) < 3:
        return False

    low = text.lower()
    explicit_prefixes = [
        r"^(please\s+)?(search(\s+the\s+web|\s+online|\s+for)?|check\s+online|look\s+up(\s+online)?|google|browse\s+for|find\s+online)\b",
        r"^(search|web_search|google):\s*",
    ]
    return any(re.search(p, low) for p in explicit_prefixes)


def is_search_request(user_input: str) -> bool:
    """
    Programmatically determines if a query requires web search based on structural intent,
    explicit search commands, factual queries, or web references.
    """
    text = (user_input or "").strip()
    if len(text) < 3:
        return False

    low = text.lower()

    if is_explicit_search(text):
        return True

    # Direct web / URL / browse references
    if any(term in low for term in ["http://", "https://", "www.", ".com", ".org", ".net", ".io", ".gov", ".edu"]):
        return True

    # Real-world information patterns (factual questions, current events, weather, stock, latest news)
    search_patterns = [
        r"^(who|where|when|why)\s+(is|are|was|were|located|born|happened)\b",
        r"\b(latest|current|news|weather|today|price|stock|score|release date|forecast|live score)\b"
    ]

    return any(re.search(pat, low) for pat in search_patterns)


def extract_search_query(user_input: str) -> str:
    """
    Extracts clean query payload for the search engine by stripping conversational prefixes.
    """
    text = (user_input or "").strip()
    clean = re.sub(
        r"^(please\s+)?(can\s+you\s+)?(search\s+the\s+web\s+for|search\s+web\s+for|check\s+online\s+for|search\s+online\s+for|search\s+for|search:|web_search:|look\s+up\s+online\s+for|look\s+up|google|browse\s+for|find\s+online\s+for|find\s+online)\s*",
        "",
        text,
        flags=re.IGNORECASE
    )
    # Remove leading/trailing quotation marks or colons
    clean = clean.strip(" :\"'").strip()
    return clean if clean else text
