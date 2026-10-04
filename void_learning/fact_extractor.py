# void_learning/fact_extractor.py
"""
Structured Fact and Knowledge Relation Extractor for V.O.I.D.
Converts raw cleaned web passages into:
1. KnowledgeFact records (subject, concept, fact, source, source_type, confidence, timestamps)
2. KnowledgeTriple relations for graph linkage (subject, relationship, target)
"""

import re
import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from void_learning.source_quality import evaluate_source_quality


@dataclass
class KnowledgeFact:
    subject: str
    concept: str
    fact: str
    source: str
    source_type: str = "general_webpage"
    confidence: float = 0.85
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source_url: str = ""
    tier: str = "Tier 3"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "subject": self.subject,
            "concept": self.concept,
            "fact": self.fact,
            "source": self.source,
            "source_type": self.source_type,
            "confidence": round(self.confidence, 3),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source_url": self.source_url,
            "tier": self.tier
        }


@dataclass
class KnowledgeTriple:
    source: str
    relationship: str
    target: str
    weight: float = 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "source": self.source,
            "relationship": self.relationship,
            "target": self.target,
            "weight": self.weight
        }


class FactExtractor:
    """
    Lightweight deterministic rule-based and linguistic extractor.
    Operates without loading heavy separate LLMs, preserving 4GB VRAM & 16GB RAM limits.
    """

    # Common semantic relationship patterns
    REL_PATTERNS = [
        (r"(?i)\b(?P<sub>[A-Z][\w\.\+\#\-]+)\s+(is\s+a|is\s+an|is\s+defined\s+as)\s+(?P<obj>[\w\s]{3,40}?)(?:\.|\,|\;|\band\b)", "is_a"),
        (r"(?i)\b(?P<sub>[A-Z][\w\.\+\#\-]+)\s+(provides|supports|implements|features)\s+(?P<obj>[\w\s]{3,40}?)(?:\.|\,|\;)", "has_feature"),
        (r"(?i)\b(?P<sub>[A-Z][\w\.\+\#\-]+)\s+(uses|relies\s+on|requires|depends\s+on)\s+(?P<obj>[\w\s]{3,40}?)(?:\.|\,|\;)", "depends_on"),
        (r"(?i)\b(?P<sub>[A-Z][\w\.\+\#\-]+)\s+(is\s+used\s+for|enables|powers)\s+(?P<obj>[\w\s]{3,40}?)(?:\.|\,|\;)", "used_for"),
        (r"(?i)\b(?P<sub>[A-Z][\w\.\+\#\-]+)\s+(was\s+created\s+by|developed\s+by|released\s+by)\s+(?P<obj>[\w\s]{3,40}?)(?:\.|\,|\;)", "created_by"),
        (r"(?i)\b(?P<sub>[A-Z][\w\.\+\#\-]+)\s+(was\s+released\s+in|introduced\s+in)\s+(?P<obj>20\d\d|19\d\d)", "released_in"),
    ]

    def extract_facts(
        self,
        topic: str,
        text: str,
        source_url: str = "",
        max_facts: int = 12
    ) -> List[KnowledgeFact]:
        """
        Parses text into high-value declarative factual statements.
        """
        facts: List[KnowledgeFact] = []
        if not text:
            return facts

        quality = evaluate_source_quality(source_url)
        base_confidence = quality["trust_score"]

        # Split text into candidate sentences
        sentences = re.split(r"(?<=[.!?])\s+", text)
        topic_words = set(w.lower() for w in re.findall(r"\w+", topic))

        seen_facts = set()

        for s in sentences:
            clean_s = s.strip()
            if len(clean_s) < 30 or len(clean_s) > 280:
                continue

            # Check relevance to topic
            s_words = set(w.lower() for w in re.findall(r"\w+", clean_s))
            relevance = len(topic_words.intersection(s_words))

            # Skip sentences without verbs or informative words
            if relevance == 0 and not any(k in clean_s.lower() for k in ["provides", "supports", "release", "feature", "used", "is", "allow", "engine"]):
                continue

            # Exclude navigation/cookie/boilerplate artifacts
            if any(noise in clean_s.lower() for noise in ["cookie", "privacy policy", "subscribe", "sign in", "all rights reserved", "click here", "read more"]):
                continue

            # Deduplicate similar claims
            norm_key = re.sub(r"[^\w\s]", "", clean_s[:60].lower())
            if norm_key in seen_facts:
                continue
            seen_facts.add(norm_key)

            # Determine subject and concept
            sub = topic
            concept = self._guess_concept(clean_s, topic)

            # Calculate confidence: Tier weighting + linguistic clarity
            conf = min(0.98, max(0.40, base_confidence + (0.05 if relevance > 1 else 0.0)))

            fact_obj = KnowledgeFact(
                subject=sub,
                concept=concept,
                fact=clean_s,
                source=quality["domain"],
                source_type=quality["source_type"],
                confidence=conf,
                source_url=source_url,
                tier=quality["tier"]
            )
            facts.append(fact_obj)

            if len(facts) >= max_facts:
                break

        return facts

    def extract_triples(self, topic: str, text: str) -> List[KnowledgeTriple]:
        """
        Extracts relational triples (Subject -[relationship]-> Target) from text for the Knowledge Graph.
        """
        triples: List[KnowledgeTriple] = []
        if not text:
            return triples

        seen = set()

        for pat, rel in self.REL_PATTERNS:
            for match in re.finditer(pat, text):
                sub = match.group("sub").strip()
                obj = match.group("obj").strip()

                # Clean up target object
                obj = re.sub(r"^(a|an|the)\s+", "", obj, flags=re.I).strip(" ,.;:")
                if len(sub) < 2 or len(obj) < 2 or len(obj) > 40:
                    continue

                key = (sub.lower(), rel, obj.lower())
                if key in seen:
                    continue
                seen.add(key)

                triples.append(KnowledgeTriple(
                    source=sub,
                    relationship=rel,
                    target=obj,
                    weight=1.0
                ))

        # Default fallback relationship linking topic to its extracted concept if none matched
        if not triples and topic:
            triples.append(KnowledgeTriple(
                source=topic,
                relationship="related_to",
                target="Technology / Computing",
                weight=0.8
            ))

        return triples

    def _guess_concept(self, sentence: str, topic: str) -> str:
        """Finds the most specific conceptual focus in the sentence."""
        words = re.findall(r"\b[A-Za-z0-9_\-\+\#]{3,}\b", sentence)
        for w in words:
            if w.lower() != topic.lower() and (w[0].isupper() or "_" in w):
                return w
        return topic
