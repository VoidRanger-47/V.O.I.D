# core/curiosity/curiosity_engine.py
"""
Autonomous Curiosity & Vetted Research Engine for V.O.I.D.
Detects knowledge gaps and schedules targeted, high-tier research:
  Knowledge Gap -> Create Task -> Research -> Extract -> Verify -> Resolve Contradictions -> Store in World Model
Restricts scraping to verified technical domains (official docs, technical specs, trusted repositories).
"""

import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from void_learning.source_quality import evaluate_source_quality, SourceTier
from core.world_model.model import world_model, WorldRelationType
from core.verification.contradiction_resolver import contradiction_resolver
from core.audit_logger import audit_logger


class GapStatus(str, Enum):
    IDENTIFIED = "IDENTIFIED"
    RESEARCHING = "RESEARCHING"
    VERIFIED = "VERIFIED"
    CONSOLIDATED = "CONSOLIDATED"
    DEFERRED = "DEFERRED"


@dataclass
class KnowledgeGap:
    id: str = field(default_factory=lambda: f"gap_{str(uuid.uuid4())[:8]}")
    topic: str = ""
    domain: str = "general"
    reason: str = ""
    priority: float = 0.5  # 0.0 to 1.0
    status: GapStatus = GapStatus.IDENTIFIED
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        return d


class CuriosityEngine:
    """
    Identifies epistemic gaps and manages autonomous, quality-vetted learning missions.
    """
    _instance: Optional['CuriosityEngine'] = None

    # Strict allowlist of authoritative technical domains
    VETTED_SOURCE_PATTERNS = [
        "docs.python.org", "github.com", "arxiv.org", "developer.mozilla.org",
        "pytorch.org", "sqlite.org", "en.cppreference.com", "learn.microsoft.com",
        "kernel.org", "stackoverflow.com", "wikipedia.org"
    ]

    def __init__(self):
        self.wm = world_model
        self.conflicts = contradiction_resolver
        self.gap_queue: List[KnowledgeGap] = []

    @classmethod
    def get_instance(cls) -> 'CuriosityEngine':
        if cls._instance is None:
            cls._instance = CuriosityEngine()
        return cls._instance

    def register_knowledge_gap(self, topic: str, domain: str = "general", reason: str = "", priority: float = 0.5) -> KnowledgeGap:
        """
        Records a newly discovered gap in V.O.I.D.'s world model or task capabilities.
        """
        # Avoid duplicate gaps
        for g in self.gap_queue:
            if g.topic.lower() == topic.lower() and g.status != GapStatus.CONSOLIDATED:
                g.priority = max(g.priority, priority)
                return g

        gap = KnowledgeGap(
            topic=topic.strip(),
            domain=domain.strip(),
            reason=reason.strip(),
            priority=priority
        )
        self.gap_queue.append(gap)
        audit_logger.log(
            event="KNOWLEDGE_GAP_IDENTIFIED",
            tool="curiosity_engine",
            status="QUEUED",
            result_summary=f"Gap: '{topic}' in domain '{domain}' (Priority {priority})"
        )
        return gap

    def filter_vetted_sources(self, candidate_urls: List[str]) -> List[str]:
        """
        Filters candidate search URLs, rejecting spam, clickbait, and unvetted blogs.
        """
        vetted = []
        for url in candidate_urls:
            low_url = url.lower()
            if any(trusted in low_url for trusted in self.VETTED_SOURCE_PATTERNS):
                vetted.append(url)
            else:
                # Evaluate via SourceQuality evaluator
                quality_res = evaluate_source_quality(url)
                score = quality_res.get("trust_score", 0.0) if isinstance(quality_res, dict) else float(quality_res)
                if score >= 0.70:
                    vetted.append(url)
        return vetted

    def process_next_learning_mission(self, is_offline: bool = False) -> Optional[Dict[str, Any]]:
        """
        Picks the highest priority pending knowledge gap and prepares an autonomous research plan.
        """
        if is_offline:
            return {"status": "DEFERRED", "reason": "System is offline; external research paused."}

        # Find highest priority pending gap
        pending = [g for g in self.gap_queue if g.status == GapStatus.IDENTIFIED]
        if not pending:
            return None

        pending.sort(key=lambda x: x.priority, reverse=True)
        target_gap = pending[0]
        target_gap.status = GapStatus.RESEARCHING

        mission_spec = {
            "gap_id": target_gap.id,
            "topic": target_gap.topic,
            "domain": target_gap.domain,
            "recommended_query": f"{target_gap.topic} official documentation technical specifications",
            "vetted_domains": self.VETTED_SOURCE_PATTERNS[:6],
            "status": "READY_FOR_EXECUTION"
        }
        return mission_spec

    def record_learned_knowledge(self, gap_id: str, topic: str, domain: str, assertions: List[Tuple[str, str, str]]):
        """
        Commits verified assertions from a research mission into the World Model.
        assertions: List of (source_entity, target_entity, relation_type)
        """
        for src, tgt, rel in assertions:
            self.wm.add_entity(src, domain=domain)
            self.wm.add_entity(tgt, domain=domain)
            try:
                rel_enum = getattr(WorldRelationType, rel, WorldRelationType.RELATED_TO)
                self.wm.link_entities(src, tgt, rel_enum)
            except Exception:
                self.wm.link_entities(src, tgt, WorldRelationType.RELATED_TO)

        # Mark gap resolved
        for g in self.gap_queue:
            if g.id == gap_id:
                g.status = GapStatus.CONSOLIDATED
                g.resolved_at = time.time()
                break


curiosity_engine = CuriosityEngine.get_instance()
