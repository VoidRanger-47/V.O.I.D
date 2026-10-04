# void_learning/conflict_detector.py
"""
Multi-Source Cross-Verification & Conflict Detector for V.O.I.D.
Compares factual claims across multiple sources to detect contradictions,
differing version numbers, conflicting release years, or opposing statements.
Ensures V.O.I.D. never arbitrarily picks one claim over another without labeling the dispute.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from void_learning.fact_extractor import KnowledgeFact


@dataclass
class ConflictReport:
    has_conflict: bool
    topic: str
    conflicts: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conflict": self.has_conflict,
            "topic": self.topic,
            "count": len(self.conflicts),
            "conflicts": self.conflicts
        }


class ConflictDetector:
    """
    Analyzes lists of extracted facts from different sources to discover discordant claims.
    """

    def detect_conflicts(self, facts: List[KnowledgeFact]) -> ConflictReport:
        conflicts = []
        if len(facts) < 2:
            return ConflictReport(has_conflict=False, topic=facts[0].subject if facts else "", conflicts=[])

        topic = facts[0].subject

        # 1. Version / Number Discrepancies
        version_claims = {}
        for f in facts:
            v_match = re.findall(r"\bv?(\d+\.\d+(?:\.\d+)?)\b", f.fact)
            for v in v_match:
                version_claims.setdefault(f.concept.lower(), []).append({
                    "version": v,
                    "fact": f.fact,
                    "source": f.source,
                    "tier": f.tier,
                    "url": f.source_url
                })

        for concept, claims in version_claims.items():
            versions = set(c["version"] for c in claims)
            sources = set(c["source"] for c in claims)
            if len(versions) > 1 and len(sources) > 1:
                conflicts.append({
                    "type": "version_discrepancy",
                    "concept": concept,
                    "claims": [c["fact"] for c in claims[:3]],
                    "sources": list(sources),
                    "resolution": "Different versions cited across sources (check release chronology)."
                })

        # 2. Release Year Discrepancies
        year_claims = {}
        for f in facts:
            y_match = re.findall(r"\b(19\d\d|20\d\d)\b", f.fact)
            for y in y_match:
                year_claims.setdefault(f.concept.lower(), []).append({
                    "year": y,
                    "fact": f.fact,
                    "source": f.source
                })

        for concept, claims in year_claims.items():
            years = set(c["year"] for c in claims)
            sources = set(c["source"] for c in claims)
            if len(years) > 1 and len(sources) > 1:
                conflicts.append({
                    "type": "temporal_discrepancy",
                    "concept": concept,
                    "claims": [c["fact"] for c in claims[:2]],
                    "sources": list(sources),
                    "resolution": "Conflicting release or origin dates detected."
                })

        # 3. Direct Negation / Contradiction Pairs (does vs does not, supported vs deprecated)
        negation_pairs = [
            (r"\bsupports\b", r"\bdoes\s+not\s+support\b"),
            (r"\bactive\b", r"\bdeprecated\b"),
            (r"\benabled\b", r"\bdisabled\b"),
            (r"\bavailable\b", r"\bunavailable\b"),
        ]

        for pos_pat, neg_pat in negation_pairs:
            pos_facts = [f for f in facts if re.search(pos_pat, f.fact, re.I)]
            neg_facts = [f for f in facts if re.search(neg_pat, f.fact, re.I)]

            if pos_facts and neg_facts:
                conflicts.append({
                    "type": "semantic_contradiction",
                    "concept": pos_facts[0].concept,
                    "claims": [pos_facts[0].fact, neg_facts[0].fact],
                    "sources": [pos_facts[0].source, neg_facts[0].source],
                    "resolution": "Contradictory assertions detected between sources. Needs further authoritative review."
                })

        return ConflictReport(
            has_conflict=len(conflicts) > 0,
            topic=topic,
            conflicts=conflicts
        )
