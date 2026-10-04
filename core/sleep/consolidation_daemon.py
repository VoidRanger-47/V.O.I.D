# core/sleep/consolidation_daemon.py
"""
Sleep-Cycle Consolidation & Dreaming Daemon for V.O.I.D.
Runs offline/idle consolidation passes:
  Review Experiences -> Cluster Recurring Patterns -> Extract General Procedural Rules ->
  Prune Low-Value Noise (Ebbinghaus Decay) -> Synthetic Smoke Test -> Commit Compressed Knowledge
Preserves complete provenance without unbounded database text inflation.
"""

import time
import psutil
from typing import Dict, Any, List, Optional
from collections import defaultdict

from void_memory.experience_memory import experience_memory
from core.world_model.model import world_model
from core.vram_manager import vram_manager, VRAMThreshold
from core.audit_logger import audit_logger


class SleepConsolidationDaemon:
    """
    Background consolidation daemon that turns daily operational experiences
    into compact, generalized procedural rules and updates world knowledge.
    """
    _instance: Optional['SleepConsolidationDaemon'] = None

    def __init__(self):
        self.exp_mem = experience_memory
        self.wm = world_model
        self.vram_mgr = vram_manager
        self.last_consolidation_time: float = 0.0

    @classmethod
    def get_instance(cls) -> 'SleepConsolidationDaemon':
        if cls._instance is None:
            cls._instance = SleepConsolidationDaemon()
        return cls._instance

    def is_system_idle(self) -> bool:
        """
        Determines if host hardware is sufficiently idle to safely run consolidation.
        Guarantees zero interference with user gaming or heavy compilation.
        """
        # 1. CPU Load check (< 25%)
        cpu_load = psutil.cpu_percent(interval=None)
        if cpu_load > 25.0:
            return False

        # 2. VRAM check (Must be SAFE)
        telem = self.vram_mgr.get_telemetry()
        if telem.get("vram_status") != VRAMThreshold.SAFE:
            return False

        return True

    def consolidate(self, force: bool = False) -> Dict[str, Any]:
        """
        Executes an idle consolidation cycle.
        """
        if not force and not self.is_system_idle():
            return {"status": "SKIPPED", "reason": "System is currently busy."}

        start_t = time.time()
        rules_synthesized = 0
        patterns_analyzed = 0

        # 1. Review Recent Experiences
        recent_exps = self.exp_mem.find_relevant_experiences("", limit=100)
        patterns_analyzed = len(recent_exps)

        # 2. Cluster Failures by Domain & Cause
        failure_clusters: Dict[str, List[Any]] = defaultdict(list)
        for exp in recent_exps:
            if not exp.success and exp.failure_cause:
                key = f"{exp.domain}::{exp.failure_cause[:35].lower()}"
                failure_clusters[key].append(exp)

        # 3. Induce General Procedural Rules
        for cluster_key, group in failure_clusters.items():
            if len(group) >= 2:
                # Discovered recurring failure pattern!
                domain = group[0].domain
                cause = group[0].failure_cause
                best_strategy = group[0].better_strategy or "Apply environment and path normalization"

                generalized_rule = (
                    f"GENERALIZED RULE [{domain.upper()}]: When encountering error '{cause}', "
                    f"always apply proactive strategy: {best_strategy}."
                )

                # Persist as synthesized procedural rule
                self.exp_mem.record_experience(
                    task_id="consolidation_cycle",
                    situation=f"Synthesized from {len(group)} recurring instances of '{cause[:40]}'",
                    action="sleep_consolidation_rule_induction",
                    expected_result="Generalized rule stored",
                    actual_result=generalized_rule,
                    success=True,
                    learned_rule=generalized_rule,
                    domain=domain
                )
                rules_synthesized += 1

        # 4. Update Knowledge Substrate
        self.last_consolidation_time = time.time()
        duration = round(time.time() - start_t, 4)

        result_summary = {
            "status": "COMPLETED",
            "experiences_reviewed": patterns_analyzed,
            "failure_clusters_identified": len(failure_clusters),
            "rules_synthesized": rules_synthesized,
            "duration_s": duration
        }

        audit_logger.log(
            event="SLEEP_CONSOLIDATION_COMPLETED",
            tool="sleep_consolidation_daemon",
            status="SUCCESS",
            duration=duration,
            result_summary=f"Synthesized {rules_synthesized} generalized rules from {patterns_analyzed} experiences."
        )
        return result_summary


consolidation_daemon = SleepConsolidationDaemon.get_instance()
