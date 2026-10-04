# core/meta_cognition/state.py
"""
Structured Cognitive State for V.O.I.D. Meta-Cognitive Supervisor.
Maintains typed, observable, and deterministic execution state across tasks.
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Dict, Any, List, Optional


class TaskComplexity(str, Enum):
    TRIVIAL = "TRIVIAL"      # Fast-path deterministic queries, greetings, single-stat lookups
    LOW = "LOW"              # Single tool execution, simple memory lookup
    MEDIUM = "MEDIUM"        # Multi-step coding or reasoning requiring verification
    HIGH = "HIGH"            # Multi-agent coordination, web research + synthesis
    COMPLEX = "COMPLEX"      # Long-horizon planning, novel problem solving, self-healing


class CognitivePhase(str, Enum):
    IDLE = "IDLE"
    PERCEIVING = "PERCEIVING"
    UNDERSTANDING = "UNDERSTANDING"
    RECALLING = "RECALLING"
    PLANNING = "PLANNING"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    LEARNING = "LEARNING"
    REPLANNING = "REPLANNING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"


class VerificationVerdict(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    REPLAN_REQUIRED = "REPLAN_REQUIRED"


@dataclass
class CognitiveResources:
    vram_budget_mb: float = 400.0
    vram_used_mb: float = 0.0
    timeout_seconds: float = 60.0
    max_retries: int = 3
    retry_count: int = 0
    execution_path: str = "DEEP_PATH"
    allow_network: bool = True
    cpu_only_mode: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CognitiveState:
    """
    Observable structured mental state for V.O.I.D.
    Replaces prompt-only unstructured reasoning with a strict, verifiable state schema.
    """
    goal: str
    task_id: str = field(default_factory=lambda: f"cog_{str(uuid.uuid4())[:8]}")
    mission_id: Optional[str] = None
    complexity: TaskComplexity = TaskComplexity.LOW
    current_state: CognitivePhase = CognitivePhase.UNDERSTANDING
    plan: List[Dict[str, Any]] = field(default_factory=list)
    active_task: Optional[str] = None
    available_tools: List[str] = field(default_factory=list)
    selected_agents: List[str] = field(default_factory=list)
    confidence: float = 0.5
    known_unknowns: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)
    resources: CognitiveResources = field(default_factory=CognitiveResources)
    verification_status: VerificationVerdict = VerificationVerdict.PENDING
    intermediate_evaluations: List[Dict[str, Any]] = field(default_factory=list)
    history: List[Dict[str, Any]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def transition_to(self, new_phase: CognitivePhase, note: str = ""):
        """Transitions to a new cognitive phase and logs state history."""
        old_phase = self.current_state
        self.current_state = new_phase
        self.updated_at = time.time()
        self.history.append({
            "from": old_phase.value if isinstance(old_phase, Enum) else old_phase,
            "to": new_phase.value if isinstance(new_phase, Enum) else new_phase,
            "note": note,
            "timestamp": self.updated_at
        })

    def record_evaluation(self, step: str, result: str, status: str, confidence: float):
        """Records an intermediate reasoning or tool execution evaluation."""
        self.intermediate_evaluations.append({
            "step": step,
            "result": result,
            "status": status,
            "confidence": round(confidence, 4),
            "timestamp": time.time()
        })
        self.updated_at = time.time()

    def add_known_unknown(self, item: str):
        if item not in self.known_unknowns:
            self.known_unknowns.append(item)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "complexity": self.complexity.value if isinstance(self.complexity, Enum) else self.complexity,
            "current_state": self.current_state.value if isinstance(self.current_state, Enum) else self.current_state,
            "plan": self.plan,
            "active_task": self.active_task,
            "available_tools": self.available_tools,
            "selected_agents": self.selected_agents,
            "confidence": round(self.confidence, 4),
            "known_unknowns": self.known_unknowns,
            "constraints": self.constraints,
            "resources": self.resources.to_dict(),
            "verification_status": self.verification_status.value if isinstance(self.verification_status, Enum) else self.verification_status,
            "intermediate_evaluations": self.intermediate_evaluations,
            "history_count": len(self.history),
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
