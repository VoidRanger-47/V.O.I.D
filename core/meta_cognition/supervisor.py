# core/meta_cognition/supervisor.py
"""
Meta-Cognitive Supervisor for V.O.I.D.
Provides the central cognitive control loop:
- Evaluates goal complexity and constraints
- Selects minimal necessary agents and tools dynamically
- Decides necessity of memory retrieval, web research, and code execution
- Governs compute budgets under RTX 3050 (4GB VRAM) and 16GB RAM limits
- Evaluates intermediate results and triggers closed-loop replanning
"""

import time
import re
from typing import Dict, Any, List, Optional, Tuple

from core.meta_cognition.state import (
    CognitiveState,
    TaskComplexity,
    CognitivePhase,
    VerificationVerdict,
    CognitiveResources
)
from core.vram_manager import vram_manager, VRAMThreshold
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.agents.coordinator import agent_coordinator
from core.audit_logger import audit_logger


class MetaCognitiveSupervisor:
    """
    Central Cognitive Governor.
    Does NOT blindly execute LLM instructions; actively governs reasoning and resources.
    """
    _instance: Optional['MetaCognitiveSupervisor'] = None

    def __init__(self):
        self.vram_mgr = vram_manager
        self.coordinator = agent_coordinator
        self.active_states: Dict[str, CognitiveState] = {}

    @classmethod
    def get_instance(cls) -> 'MetaCognitiveSupervisor':
        if cls._instance is None:
            cls._instance = MetaCognitiveSupervisor()
        return cls._instance

    def initialize_state(
        self,
        goal: str,
        task_id: Optional[str] = None,
        mission_id: Optional[str] = None,
        constraints: Optional[List[str]] = None
    ) -> CognitiveState:
        """
        Creates and registers a new structured CognitiveState for a user goal.
        """
        state = CognitiveState(
            goal=goal.strip(),
            task_id=task_id or f"cog_{str(int(time.time() * 1000))[-8:]}",
            mission_id=mission_id,
            constraints=constraints or []
        )
        self._assess_initial_goal(state)
        self.active_states[state.task_id] = state
        return state

    def _assess_initial_goal(self, state: CognitiveState):
        """
        Performs structural goal complexity assessment and initial agent/tool selection.
        """
        low_goal = state.goal.lower()

        # 1. Trivial check (greetings, simple time, identity)
        if any(low_goal == g or low_goal.startswith(g + " ") for g in ["hi", "hello", "hey", "sup", "who are you", "what is void", "time"]):
            state.complexity = TaskComplexity.TRIVIAL
            state.confidence = 0.98
            state.selected_agents = ["executive"]
            state.resources.execution_path = "FAST_PATH"
            state.resources.vram_budget_mb = 0.0
            return

        # 2. Hardware / System check
        if any(k in low_goal for k in ["cpu usage", "ram usage", "vram", "hardware status", "system stats", "battery"]):
            state.complexity = TaskComplexity.LOW
            state.confidence = 0.95
            state.selected_agents = ["system_agent"]
            state.available_tools = ["system_monitor"]
            state.resources.execution_path = "FAST_PATH"
            state.resources.vram_budget_mb = 0.0
            return

        # 3. Dedicated Phone Control
        if any(k in low_goal for k in ["unlock phone", "lock phone", "call ", "send sms", "phone battery", "phone status"]):
            state.complexity = TaskComplexity.LOW
            state.confidence = 0.90
            state.selected_agents = ["phone_agent"]
            state.available_tools = ["phone_control"]
            state.resources.execution_path = "FAST_PATH"
            return

        # 4. Mathematics & Formulas
        if any(k in low_goal for k in ["calculate", "solve", "derivative", "integral", "matrix", "eigenvalue"]) or re.search(r'\d+\s*[\+\-\*\/\^]\s*\d+', low_goal):
            state.complexity = TaskComplexity.MEDIUM
            state.confidence = 0.92
            state.selected_agents = ["mathematics_agent", "verification_agent"]
            state.available_tools = ["math_solver"]
            state.resources.execution_path = "DEEP_PATH"
            return

        # 5. Coding & Software Engineering
        if any(k in low_goal for k in ["write code", "fix error", "debug", "python", "function", "class ", "refactor", "bug"]):
            state.complexity = TaskComplexity.HIGH
            state.confidence = 0.85
            state.selected_agents = ["coding_agent", "verification_agent"]
            state.available_tools = ["ast_sandbox", "coding_engine"]
            state.resources.execution_path = "DEEP_PATH"
            return

        # 6. Multi-agent / Research / Complex synthesis
        if any(k in low_goal for k in ["research", "investigate", "compare", "latest news", "learn about"]):
            state.complexity = TaskComplexity.HIGH
            state.confidence = 0.70
            state.selected_agents = ["research_agent", "knowledge_agent", "executive", "verification_agent"]
            state.available_tools = ["web_search", "document_parser"]
            state.resources.execution_path = "DEEP_PATH"
            return

        # General task fallback
        state.complexity = TaskComplexity.MEDIUM
        state.confidence = 0.75
        state.selected_agents = ["executive", "memory_agent", "verification_agent"]
        state.resources.execution_path = "DEEP_PATH"

    def decide_memory_retrieval(self, state: CognitiveState) -> bool:
        """
        Determines whether memory retrieval is genuinely required.
        Avoids injecting irrelevant memory chunks into the reasoning context.
        """
        if state.complexity == TaskComplexity.TRIVIAL:
            return False

        low_goal = state.goal.lower()
        memory_keywords = [
            "remember", "recall", "last time", "earlier", "my name", "my project",
            "preference", "style", "history", "previous", "who am i", "architecture",
            "void_memory", "how did we"
        ]
        if any(k in low_goal for k in memory_keywords):
            return True

        # In High or Complex tasks, memory retrieval is useful for context grounding
        if state.complexity in (TaskComplexity.HIGH, TaskComplexity.COMPLEX):
            return True

        return False

    def decide_web_research(self, state: CognitiveState) -> bool:
        """
        Determines whether external web research is necessary and allowed.
        Respects offline-first policy and local knowledge coverage.
        """
        if not state.resources.allow_network:
            return False

        low_goal = state.goal.lower()
        # Explicit search request
        if any(k in low_goal for k in ["search web", "look up online", "google", "latest documentation", "current news"]):
            return True

        # Temporal markers indicating facts beyond static training
        if any(k in low_goal for k in ["latest", "recent", "today", "2026", "news", "release notes"]):
            return True

        return False

    def decide_code_execution(self, state: CognitiveState) -> bool:
        """
        Determines whether sandboxed code execution is needed to fulfill or verify the goal.
        """
        low_goal = state.goal.lower()
        return any(k in low_goal for k in ["run code", "execute", "test", "eval", "calculate with script", "verify script"])

    def evaluate_resource_budget(self, state: CognitiveState) -> Tuple[bool, str]:
        """
        Checks VRAM and hardware load before launching tasks.
        Enforces 4GB VRAM safety on RTX 3050 Laptop.
        """
        telem = self.vram_mgr.get_telemetry()
        vram_status = telem.get("vram_status", "SAFE")
        used_vram = telem.get("used_vram_mb", 0.0)
        state.resources.vram_used_mb = used_vram

        if vram_status == VRAMThreshold.CRITICAL:
            state.resources.cpu_only_mode = True
            state.add_known_unknown("GPU VRAM critical; executing strictly via CPU/Deterministic agents.")
            return False, f"VRAM Critical ({used_vram:.1f} MB used). Switched to CPU-only execution."

        if vram_status == VRAMThreshold.WARNING:
            state.resources.vram_budget_mb = min(state.resources.vram_budget_mb, 200.0)

        return True, "Resource budget within safe operational limits."

    def evaluate_intermediate_result(
        self,
        state: CognitiveState,
        step_id: int,
        agent_name: str,
        output: Any,
        status: str
    ) -> VerificationVerdict:
        """
        Evaluates intermediate step outputs against verification criteria.
        Decides whether to continue, re-plan, or abort.
        """
        output_str = str(output) if output is not None else ""

        # Check for immediate structural failure
        if status == "FAILED" or "❌" in output_str or "Syntax Error" in output_str or "Traceback" in output_str:
            state.record_evaluation(f"step_{step_id}_{agent_name}", output_str[:120], "FAILED", 0.2)
            if state.resources.retry_count < state.resources.max_retries:
                state.resources.retry_count += 1
                state.verification_status = VerificationVerdict.REPLAN_REQUIRED
                state.transition_to(CognitivePhase.REPLANNING, f"Step {step_id} failed: {output_str[:60]}")
                return VerificationVerdict.REPLAN_REQUIRED
            else:
                state.verification_status = VerificationVerdict.FAILED
                state.transition_to(CognitivePhase.FAILED, f"Exceeded max retries ({state.resources.max_retries})")
                return VerificationVerdict.FAILED

        # Step passed
        state.record_evaluation(f"step_{step_id}_{agent_name}", output_str[:120], "PASSED", 0.9)
        return VerificationVerdict.PASSED

    def finalize_task(self, state: CognitiveState, final_result: str, status: str = "SUCCESS"):
        """
        Finalizes the task state, logging metrics and auditing outcomes.
        """
        if status == "SUCCESS":
            state.transition_to(CognitivePhase.COMPLETE, "Task executed and verified successfully")
            state.verification_status = VerificationVerdict.PASSED
        else:
            state.transition_to(CognitivePhase.FAILED, "Task execution failed verification")
            state.verification_status = VerificationVerdict.FAILED

        audit_logger.log(
            event="META_COGNITIVE_TASK_FINALIZED",
            tool="meta_cognitive_supervisor",
            status=status,
            task_id=state.task_id,
            duration=round(time.time() - state.created_at, 4),
            result_summary=final_result[:150] if final_result else None
        )


supervisor = MetaCognitiveSupervisor.get_instance()
