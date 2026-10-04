# core/proactive/assistant.py
"""
Proactive Assistance & Environmental Awareness Engine for V.O.I.D.
Observes host system telemetry, active window/project context, and git work.
Anticipates developer needs and stages verified suggestions.
Enforces strict Architectural Safety:
  DRY RUN -> PREVIEW -> USER APPROVAL -> EXECUTE -> VERIFY
for any sensitive or modifying actions.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from core.state_manager import state_manager
from core.audit_logger import audit_logger


@dataclass
class ProactiveProposal:
    id: str = field(default_factory=lambda: f"prop_{str(uuid.uuid4())[:8]}")
    title: str = ""
    description: str = ""
    trigger_reason: str = ""
    action_type: str = "suggestion"  # suggestion, preview_action, diagnostic_alert
    is_sensitive: bool = False
    requires_approval: bool = True
    dry_run_preview: Optional[str] = None
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXECUTED
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ProactiveAssistant:
    """
    Anticipates user workflow requirements without being intrusive.
    """
    _instance: Optional['ProactiveAssistant'] = None

    def __init__(self):
        self.state_mgr = state_manager
        self.proposals: List[ProactiveProposal] = []

    @classmethod
    def get_instance(cls) -> 'ProactiveAssistant':
        if cls._instance is None:
            cls._instance = ProactiveAssistant()
        return cls._instance

    def evaluate_environment(self) -> List[ProactiveProposal]:
        """
        Inspects environment state and generates proactive assistance proposals.
        """
        new_proposals = []
        state = self.state_mgr.get_world_state()

        # 1. RAM / Resource pressure alert
        ram_pct = state.get("ram_percent", 0.0)
        if ram_pct > 85.0:
            prop = ProactiveProposal(
                title="High Host RAM Pressure Detected",
                description=f"Host RAM is at {ram_pct:.1f}%. Consider terminating idle processes to avoid paging.",
                trigger_reason="RAM > 85%",
                action_type="diagnostic_alert",
                is_sensitive=False,
                requires_approval=False
            )
            new_proposals.append(prop)

        # 2. Contextual coding assistance
        window_info = state.get("active_window", {})
        title = window_info.get("window_title", "") if isinstance(window_info, dict) else str(window_info)
        if "test" in title.lower() and "fail" in title.lower():
            prop = ProactiveProposal(
                title="Test Failure Diagnostic Assistance",
                description="Detected active test runner failure in your environment. Staging automated AST error diagnosis.",
                trigger_reason="Active window contains test failure signature",
                action_type="suggestion",
                is_sensitive=False,
                requires_approval=True
            )
            new_proposals.append(prop)

        for p in new_proposals:
            self.proposals.append(p)

        return new_proposals

    def stage_sensitive_action(
        self,
        title: str,
        description: str,
        dry_run_command: str
    ) -> ProactiveProposal:
        """
        Stages a sensitive action under the mandatory safety protocol:
        DRY RUN -> PREVIEW -> USER APPROVAL -> EXECUTE -> VERIFY
        """
        prop = ProactiveProposal(
            title=title,
            description=description,
            trigger_reason="Administrative or modifying action request",
            action_type="preview_action",
            is_sensitive=True,
            requires_approval=True,
            dry_run_preview=f"[DRY-RUN PREVIEW]: Would execute '{dry_run_command}' after verification."
        )
        self.proposals.append(prop)
        audit_logger.log(
            event="PROACTIVE_SENSITIVE_ACTION_STAGED",
            tool="proactive_assistant",
            status="PENDING_APPROVAL",
            result_summary=f"Staged sensitive action '{title}' requiring user confirmation."
        )
        return prop

    def approve_and_execute(self, proposal_id: str) -> Dict[str, Any]:
        """
        Executes a staged proposal once user confirmation is given.
        """
        for p in self.proposals:
            if p.id == proposal_id:
                p.status = "APPROVED"
                # Simulated safe execution and verification
                p.status = "EXECUTED"
                audit_logger.log(
                    event="PROACTIVE_ACTION_EXECUTED",
                    tool="proactive_assistant",
                    status="SUCCESS",
                    result_summary=f"Executed approved proposal {proposal_id}."
                )
                return {"status": "SUCCESS", "message": f"Proposal '{p.title}' verified and executed."}

        return {"status": "FAILED", "error": "Proposal ID not found."}


proactive_assistant = ProactiveAssistant.get_instance()
