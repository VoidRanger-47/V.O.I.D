# core/verification/contradiction_resolver.py
"""
Cognitive Contradiction Resolver for V.O.I.D.
Prevents silent overwrites of conflicting knowledge.
Creates explicit Cognitive Conflicts, preserves provenance, and arbitrates via 4 strategies:
  1. SUPERSEDES: New knowledge empirically supersedes obsolete knowledge
  2. CONTEXTUAL_COEXISTENCE: Both claims are valid in different environments / versions
  3. UNRESOLVED: Insufficient evidence; flagged for future empirical testing
  4. USER_CLARIFICATION_REQUIRED: Ambiguous high-stakes assertion requiring user input
"""

import os
import json
import time
import uuid
import sqlite3
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.audit_logger import audit_logger


class ConflictDecision(str, Enum):
    SUPERSEDES = "SUPERSEDES"
    CONTEXTUAL_COEXISTENCE = "CONTEXTUAL_COEXISTENCE"
    UNRESOLVED = "UNRESOLVED"
    USER_CLARIFICATION_REQUIRED = "USER_CLARIFICATION_REQUIRED"


@dataclass
class CognitiveConflict:
    id: str = field(default_factory=lambda: f"cnf_{str(uuid.uuid4())[:8]}")
    domain: str = "general"
    old_claim: str = ""
    new_claim: str = ""
    old_source: str = ""
    new_source: str = ""
    old_confidence: float = 0.5
    new_confidence: float = 0.5
    decision: ConflictDecision = ConflictDecision.UNRESOLVED
    resolution_rationale: str = ""
    affected_nodes: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    resolved_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["decision"] = self.decision.value if isinstance(self.decision, Enum) else self.decision
        return d


class ContradictionResolver:
    """
    Manages and arbitrates cognitive conflicts between old and new knowledge.
    """
    _instance: Optional['ContradictionResolver'] = None

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls) -> 'ContradictionResolver':
        if cls._instance is None:
            cls._instance = ContradictionResolver()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        conn.execute('''
            CREATE TABLE IF NOT EXISTS cognitive_conflicts (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                old_claim TEXT NOT NULL,
                new_claim TEXT NOT NULL,
                old_source TEXT DEFAULT '',
                new_source TEXT DEFAULT '',
                old_confidence REAL NOT NULL,
                new_confidence REAL NOT NULL,
                decision TEXT NOT NULL,
                resolution_rationale TEXT DEFAULT '',
                affected_nodes_json TEXT DEFAULT '[]',
                created_at REAL NOT NULL,
                resolved_at REAL
            )
        ''')
        conn.commit()
        conn.close()

    def arbitrate(
        self,
        old_claim: str,
        new_claim: str,
        domain: str = "general",
        old_source: str = "memory",
        new_source: str = "web_research",
        old_confidence: float = 0.70,
        new_confidence: float = 0.85,
        new_verification_passed: bool = True
    ) -> CognitiveConflict:
        """
        Arbitrates between competing assertions with rigorous provenance tracking.
        """
        now = time.time()
        conflict = CognitiveConflict(
            domain=domain,
            old_claim=old_claim.strip(),
            new_claim=new_claim.strip(),
            old_source=old_source,
            new_source=new_source,
            old_confidence=round(old_confidence, 4),
            new_confidence=round(new_confidence, 4),
            created_at=now
        )

        # 1. Check for version / environment contextual variance (e.g. Python 2 vs Python 3, Windows vs Linux)
        context_markers = ["version", "python 3", "python 2", "windows", "linux", "mac", "v1", "v2", "deprecated in"]
        if any(m in old_claim.lower() or m in new_claim.lower() for m in context_markers):
            conflict.decision = ConflictDecision.CONTEXTUAL_COEXISTENCE
            conflict.resolution_rationale = "Both claims are valid in different environmental/version contexts."
            conflict.resolved_at = now

        # 2. Strong empirical verification of new claim over unverified old claim
        elif new_verification_passed and new_confidence > (old_confidence + 0.15):
            conflict.decision = ConflictDecision.SUPERSEDES
            conflict.resolution_rationale = f"New claim backed by empirical verification and higher source confidence ({new_confidence} > {old_confidence})."
            conflict.resolved_at = now

        # 3. High stakes / ambiguous conflict
        elif abs(new_confidence - old_confidence) < 0.10:
            conflict.decision = ConflictDecision.USER_CLARIFICATION_REQUIRED
            conflict.resolution_rationale = "Claims have comparable confidence without decisive empirical proof. Awaiting user clarification."

        # 4. Default unresolved
        else:
            conflict.decision = ConflictDecision.UNRESOLVED
            conflict.resolution_rationale = "Insufficient evidence to discard old claim; held in quarantine."

        # Persist conflict
        conn = self._get_connection()
        conn.execute('''
            INSERT INTO cognitive_conflicts (
                id, domain, old_claim, new_claim, old_source, new_source,
                old_confidence, new_confidence, decision, resolution_rationale,
                affected_nodes_json, created_at, resolved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            conflict.id, conflict.domain, conflict.old_claim, conflict.new_claim,
            conflict.old_source, conflict.new_source, conflict.old_confidence, conflict.new_confidence,
            conflict.decision.value, conflict.resolution_rationale, json.dumps(conflict.affected_nodes),
            conflict.created_at, conflict.resolved_at
        ))
        conn.commit()
        conn.close()

        audit_logger.log(
            event="COGNITIVE_CONFLICT_RECORDED",
            tool="contradiction_resolver",
            status=conflict.decision.value,
            result_summary=conflict.resolution_rationale[:140]
        )
        return conflict

    def list_unresolved_conflicts(self) -> List[CognitiveConflict]:
        conn = self._get_connection()
        rows = conn.execute(
            "SELECT * FROM cognitive_conflicts WHERE decision IN (?, ?)",
            (ConflictDecision.UNRESOLVED.value, ConflictDecision.USER_CLARIFICATION_REQUIRED.value)
        ).fetchall()
        conn.close()

        results = []
        for r in rows:
            results.append(CognitiveConflict(
                id=r["id"],
                domain=r["domain"],
                old_claim=r["old_claim"],
                new_claim=r["new_claim"],
                old_source=r["old_source"],
                new_source=r["new_source"],
                old_confidence=r["old_confidence"],
                new_confidence=r["new_confidence"],
                decision=ConflictDecision(r["decision"]),
                resolution_rationale=r["resolution_rationale"],
                affected_nodes=json.loads(r["affected_nodes_json"] or "[]"),
                created_at=r["created_at"],
                resolved_at=r["resolved_at"]
            ))
        return results


contradiction_resolver = ContradictionResolver.get_instance()
