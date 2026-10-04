# void_memory/memory_ranker.py
"""
Memory Importance & Hybrid Scoring Engine for V.O.I.D.
Computes dynamic importance, recency decay, access frequency boosts, and composite rank scores.
"""

import time
import math
import re
from typing import Dict, Any, Optional

from void_memory.database.models import MemoryNode, MemoryTier


class MemoryRanker:
    """
    Configurable weighted scoring engine for hybrid memory ranking.
    """

    def __init__(
        self,
        weight_semantic: float = 0.45,
        weight_keyword: float = 0.20,
        weight_importance: float = 0.20,
        weight_recency: float = 0.10,
        weight_frequency: float = 0.05,
        half_life_days: float = 30.0
    ):
        self.weight_semantic = weight_semantic
        self.weight_keyword = weight_keyword
        self.weight_importance = weight_importance
        self.weight_recency = weight_recency
        self.weight_frequency = weight_frequency
        self.half_life_days = half_life_days

    def score_memory(
        self,
        node: MemoryNode,
        semantic_sim: float = 0.0,
        keyword_sim: float = 0.0,
        current_time: Optional[float] = None
    ) -> float:
        """
        Calculates a composite relevance score for a memory node against a query.
        """
        now = current_time or time.time()
        age_seconds = max(0.0, now - node.created_at)
        age_days = age_seconds / 86400.0

        # Recency score using exponential decay
        recency_score = math.exp(-math.log(2) * (age_days / max(1.0, self.half_life_days)))

        # Access frequency score (logarithmic boost)
        freq_score = min(1.0, math.log1p(node.access_count) / 5.0)

        # Base importance (preference and pinned memories get priority boost)
        effective_importance = node.importance
        if node.pinned:
            effective_importance = max(1.0, effective_importance + 0.3)
        if node.memory_type == MemoryTier.PREFERENCE.value:
            effective_importance = max(0.9, effective_importance + 0.2)

        # Composite score
        score = (
            (self.weight_semantic * semantic_sim) +
            (self.weight_keyword * keyword_sim) +
            (self.weight_importance * effective_importance) +
            (self.weight_recency * recency_score) +
            (self.weight_frequency * freq_score)
        )

        return round(float(score), 4)

    def calculate_initial_importance(
        self,
        content: str,
        category: str = "general",
        is_explicit: bool = False,
        source: str = "conversation"
    ) -> float:
        """
        Estimates initial importance score (0.0 to 1.0) for new information.
        """
        if is_explicit:
            return 0.95

        clean = content.lower().strip()
        score = 0.50

        # 1. Category heuristics
        if category in ("user_preference", "preference"):
            score += 0.30
        elif category in ("project_architecture", "technical_decision", "project"):
            score += 0.25
        elif category in ("problem_solution", "solution", "error_fix"):
            score += 0.25
        elif category in ("user_identity", "contact"):
            score += 0.35

        # 2. Key phrases
        high_priority_phrases = [
            "always", "never", "my name is", "i prefer", "i like", "i work on",
            "remember", "important", "architecture", "database", "api key", "password",
            "fixed the bug", "the solution is", "decided to", "we use"
        ]
        if any(p in clean for p in high_priority_phrases):
            score += 0.20

        # 3. Technical tokens (code, paths, numbers, acronyms)
        if re.search(r'[A-Za-z0-9_]+\.[A-Za-z0-9_]+', clean) or ("/" in clean or "\\" in clean):
            score += 0.10

        # 4. Length penalty for single-word or very short fragments
        if len(clean.split()) < 3:
            score -= 0.15

        return round(max(0.1, min(1.0, score)), 2)
