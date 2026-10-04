# core/adaptation/adaptation_guard.py
"""
Continual Learning & Model Adaptation Guard for V.O.I.D.
Prevents catastrophic forgetting and VRAM exhaustion:
  Strict Rule: Non-Parametric First (Experience -> Memory -> Procedures -> Knowledge Graph).
Never fine-tunes the primary model after single interactions.
Gates distillation behind frequency, stability, and hardware criteria.
"""

import os
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.vram_manager import vram_manager, VRAMThreshold
from core.audit_logger import audit_logger


@dataclass
class DistillationCandidate:
    candidate_id: str
    concept_or_rule: str
    domain: str
    access_count: int
    confidence: float
    verified_stable: bool
    status: str = "QUEUED"  # QUEUED, APPROVED, DISTILLED, REJECTED
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AdaptationGuard:
    """
    Guards model weights against corruption and catastrophic forgetting.
    """
    _instance: Optional['AdaptationGuard'] = None

    MIN_STABLE_ACCESS_COUNT = 10
    MIN_CONFIDENCE_THRESHOLD = 0.95

    def __init__(self, manifest_file: str = "void_memory/adaptation_manifest.json"):
        self.manifest_file = manifest_file
        self.vram_mgr = vram_manager
        self.distillation_queue: List[DistillationCandidate] = []
        self._load_manifest()

    @classmethod
    def get_instance(cls) -> 'AdaptationGuard':
        if cls._instance is None:
            cls._instance = AdaptationGuard()
        return cls._instance

    def _load_manifest(self):
        if os.path.exists(self.manifest_file):
            try:
                with open(self.manifest_file, "r") as f:
                    data = json.load(f)
                    for item in data.get("queue", []):
                        self.distillation_queue.append(DistillationCandidate(**item))
            except Exception as e:
                print(f"ℹ️ AdaptationGuard manifest load notice: {e}")

    def save_manifest(self):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.manifest_file)), exist_ok=True)
            with open(self.manifest_file, "w") as f:
                json.dump({
                    "queue": [c.to_dict() for c in self.distillation_queue],
                    "updated_at": time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ AdaptationGuard manifest save error: {e}")

    def evaluate_training_safety(self) -> Tuple[bool, str]:
        """
        Guarantees that training or adapter fine-tuning will not exhaust 4GB VRAM.
        """
        telem = self.vram_mgr.get_telemetry()
        used_vram = telem.get("used_vram_mb", 0.0)

        # On a 4GB card, training requires at least 2.5GB free VRAM
        if used_vram > 1500.0 or telem.get("vram_status") != VRAMThreshold.SAFE:
            return False, f"VRAM unsafe for training: {used_vram:.1f} MB in use. Minimum 2.5 GB free required."

        return True, "Hardware parameters safe for background distillation."

    def consider_for_distillation(
        self,
        concept_or_rule: str,
        domain: str,
        access_count: int,
        confidence: float,
        has_active_conflict: bool = False
    ) -> Tuple[bool, str]:
        """
        Evaluates whether a piece of knowledge qualifies for parametric model distillation.
        Enforces Non-Parametric First policy.
        """
        if has_active_conflict:
            return False, "REJECTED: Candidate has active cognitive conflicts. Weight distillation strictly forbidden."

        if access_count < self.MIN_STABLE_ACCESS_COUNT:
            return False, (
                f"REJECTED: Non-Parametric First. Access count ({access_count}) "
                f"is below stability threshold ({self.MIN_STABLE_ACCESS_COUNT}). Stored in Knowledge Graph only."
            )

        if confidence < self.MIN_CONFIDENCE_THRESHOLD:
            return False, f"REJECTED: Confidence {confidence} below verified threshold {self.MIN_CONFIDENCE_THRESHOLD}."

        candidate = DistillationCandidate(
            candidate_id=f"dist_{str(int(time.time()*1000))[-6:]}",
            concept_or_rule=concept_or_rule,
            domain=domain,
            access_count=access_count,
            confidence=confidence,
            verified_stable=True
        )
        self.distillation_queue.append(candidate)
        self.save_manifest()

        audit_logger.log(
            event="ADAPTATION_CANDIDATE_QUEUED",
            tool="adaptation_guard",
            status="QUEUED",
            result_summary=f"Queued '{concept_or_rule[:50]}' for idle adapter compilation."
        )
        return True, "APPROVED: Candidate queued for scheduled idle adapter compilation."


adaptation_guard = AdaptationGuard.get_instance()
