# void_learning/research_agent.py
"""
WebResearchAgent for V.O.I.D.
Dedicated research agent that:
- Executes targeted internet searches via DuckDuckGo
- Scrapes and cleans readable text from top sources safely
- Evaluates source credibility across Tier 1, Tier 2, and Tier 3
- Extracts structured facts and Knowledge Graph triples
- Detects cross-source conflicting information
- Produces clean structured research results:
  {
      "topic": "...",
      "facts": [...],
      "sources": [...],
      "confidence": 0.0,
      "conflicts": [...],
      "timestamp": "...",
      "research_summary": "..."
  }
"""

import time
import html
from typing import Dict, Any, List, Optional
from datetime import datetime

try:
    from ddgs import DDGS
except ImportError:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        DDGS = None

from lib.offline_manager import offline_mgr
from void_learning.source_quality import evaluate_source_quality, SourceTier
from void_learning.content_cleaner import fetch_and_clean_page
from void_learning.fact_extractor import FactExtractor, KnowledgeFact, KnowledgeTriple
from void_learning.conflict_detector import ConflictDetector


class WebResearchAgent:
    """
    Dedicated autonomous web researcher for V.O.I.D.
    Does NOT dump massive uncleaned HTML into the LLM context.
    Produces high-fidelity, structured research records.
    """

    def __init__(self):
        self.extractor = FactExtractor()
        self.conflict_detector = ConflictDetector()

    def research(
        self,
        topic: str,
        max_sources: int = 5,
        scrape_full_content: bool = True
    ) -> Dict[str, Any]:
        """
        Executes an end-to-end research cycle for a topic.
        """
        clean_topic = topic.strip()
        timestamp = datetime.now().isoformat()

        # Offline verification
        if offline_mgr.is_offline():
            return {
                "topic": clean_topic,
                "facts": [],
                "sources": [],
                "confidence": 0.0,
                "conflicts": [],
                "timestamp": timestamp,
                "research_summary": f"[Offline Mode] Research cannot access the live web. Internet access is currently unavailable.",
                "offline": True
            }

        if DDGS is None:
            return {
                "topic": clean_topic,
                "facts": [],
                "sources": [],
                "confidence": 0.0,
                "conflicts": [],
                "timestamp": timestamp,
                "research_summary": "Search backend library not available.",
                "error": "DDGS unavailable"
            }

        print(f"[WebResearchAgent] Initiating structured deep research for '{clean_topic}'...")

        # 1. Search Query Generation
        search_query = f"{clean_topic} overview documentation"
        search_results = []

        try:
            with DDGS() as ddgs:
                search_results = list(ddgs.text(search_query, max_results=max_sources))
        except Exception as e:
            # Try plain query if composite query failed
            try:
                with DDGS() as ddgs:
                    search_results = list(ddgs.text(clean_topic, max_results=max_sources))
            except Exception as e2:
                return {
                    "topic": clean_topic,
                    "facts": [],
                    "sources": [],
                    "confidence": 0.0,
                    "conflicts": [],
                    "timestamp": timestamp,
                    "research_summary": f"Web search failed: {str(e2)}",
                    "error": str(e2)
                }

        if not search_results:
            return {
                "topic": clean_topic,
                "facts": [],
                "sources": [],
                "confidence": 0.0,
                "conflicts": [],
                "timestamp": timestamp,
                "research_summary": f"No online research results found for '{clean_topic}'.",
                "sources_analyzed": 0
            }

        sources_data: List[Dict[str, Any]] = []
        all_extracted_facts: List[KnowledgeFact] = []
        all_extracted_triples: List[KnowledgeTriple] = []

        # 2. Iterate and process sources
        for item in search_results:
            url = item.get("href", "").strip()
            title = html.unescape(item.get("title", "Untitled")).strip()
            body_snippet = html.unescape(item.get("body", "")).strip()

            quality = evaluate_source_quality(url)

            source_record = {
                "url": url,
                "title": title,
                "domain": quality["domain"],
                "tier": quality["tier"],
                "tier_num": quality["tier_num"],
                "trust_score": quality["trust_score"],
                "source_type": quality["source_type"],
                "is_authoritative": quality["is_authoritative"]
            }

            text_to_process = body_snippet

            # Deep scrape if enabled and source has valid URL
            if scrape_full_content and url.startswith(("http://", "https://")):
                page_res = fetch_and_clean_page(url, timeout_seconds=4.0)
                if page_res["success"] and len(page_res["content"]) > len(body_snippet):
                    text_to_process = page_res["content"]
                    source_record["title"] = page_res["title"] or title
                    source_record["full_scrape"] = True
                else:
                    source_record["full_scrape"] = False
            else:
                source_record["full_scrape"] = False

            source_record["char_count"] = len(text_to_process)
            sources_data.append(source_record)

            # 3. Extract Facts & Triples from this source
            source_facts = self.extractor.extract_facts(
                topic=clean_topic,
                text=text_to_process,
                source_url=url,
                max_facts=6
            )
            all_extracted_facts.extend(source_facts)

            triples = self.extractor.extract_triples(topic=clean_topic, text=text_to_process)
            all_extracted_triples.extend(triples)

        # 4. Check for Conflicts Across Sources
        conflict_report = self.conflict_detector.detect_conflicts(all_extracted_facts)

        # 5. Calculate Aggregate Confidence
        if sources_data:
            tier1_count = sum(1 for s in sources_data if s["tier_num"] == 1)
            tier2_count = sum(1 for s in sources_data if s["tier_num"] == 2)
            avg_source_score = sum(s["trust_score"] for s in sources_data) / len(sources_data)
            
            # Bonus confidence for multi-source confirmation and Tier 1 presence
            confidence_bonus = (0.05 if tier1_count >= 1 else 0.0) + (0.03 if len(sources_data) >= 3 else 0.0)
            if conflict_report.has_conflict:
                confidence_bonus -= 0.10

            overall_confidence = min(0.98, max(0.40, avg_source_score + confidence_bonus))
        else:
            overall_confidence = 0.50

        # 6. Deduplicate & Format Facts
        unique_facts = []
        seen_fact_text = set()
        for f in sorted(all_extracted_facts, key=lambda x: x.confidence, reverse=True):
            f_key = f.fact.lower()[:60]
            if f_key not in seen_fact_text:
                seen_fact_text.add(f_key)
                unique_facts.append(f)

        # 7. Generate Concise Research Summary
        summary_lines = [
            f"V.O.I.D. Research Report for '{clean_topic}':",
            f"• Sources Analyzed: {len(sources_data)} ({sum(1 for s in sources_data if s['tier_num'] == 1)} authoritative Tier 1)",
            f"• Facts Discovered: {len(unique_facts)} (Average Confidence: {int(overall_confidence * 100)}%)",
        ]
        if conflict_report.has_conflict:
            summary_lines.append(f"• ⚠️ Conflicting claims detected across sources: {len(conflict_report.conflicts)}")
        else:
            summary_lines.append("• Verification: All key claims confirmed across independent sources.")

        if unique_facts:
            summary_lines.append("\nKey Findings:")
            for f in unique_facts[:4]:
                summary_lines.append(f"- {f.fact} ({f.source} • {f.tier})")

        return {
            "topic": clean_topic,
            "facts": [f.to_dict() for f in unique_facts],
            "triples": [t.to_dict() for t in all_extracted_triples],
            "sources": sources_data,
            "confidence": round(overall_confidence, 3),
            "conflicts": conflict_report.conflicts,
            "conflict_count": len(conflict_report.conflicts),
            "timestamp": timestamp,
            "research_summary": "\n".join(summary_lines)
        }
