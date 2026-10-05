# core/agent.py
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

from core.event_bus import event_bus, SystemEvent
from core.state_manager import state_manager
from core.security import security_manager
from core.tool_registry import tool_registry
from core.planner import agent_planner, ExecutionPlan
from providers.manager import model_manager
from void_memory.memory import void_memory
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.agents.coordinator import agent_coordinator
import core.agents.network  # Ensures all 13 specialized agents are auto-registered

from core.meta_cognition.supervisor import supervisor, MetaCognitiveSupervisor
from core.meta_cognition.state import CognitiveState
from core.world_model.model import world_model, WorldModel
from core.self_model.model import self_model, SelfModel
from void_memory.experience_memory import experience_memory, ExperienceMemory
from core.planning.hierarchical_planner import hierarchical_planner, HierarchicalPlanner
from core.execution.closed_loop import closed_loop_executor, ClosedLoopExecutor
from skills.library.skill_registry import skill_registry, SkillRegistry
from core.verification.empirical_engine import empirical_engine, EmpiricalVerificationEngine
from core.verification.contradiction_resolver import contradiction_resolver, ContradictionResolver
from core.cross_domain.transfer_engine import cross_domain_engine, CrossDomainTransferEngine
from core.curiosity.curiosity_engine import curiosity_engine, CuriosityEngine
from core.sleep.consolidation_daemon import consolidation_daemon, SleepConsolidationDaemon
from core.adaptation.adaptation_guard import adaptation_guard, AdaptationGuard
from core.proactive.assistant import proactive_assistant, ProactiveAssistant

@dataclass
class AgentResult:
    response: str
    status: str  # "SUCCESS", "FAILED", "PARTIAL"
    skill: str
    plan: ExecutionPlan
    executed_tools: List[Tuple[str, Any]] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    duration_s: float = 0.0
    cognitive_state: Optional[Dict[str, Any]] = None

class VoidAgent:
    """
    V.O.I.D. Primary Multi-Agent AI Operating Layer Interface.
    Orchestrates the 10-phase AGI cognitive core:
    Supervisor -> WorldModel -> SelfModel -> ExperienceMemory -> HierarchicalPlanner ->
    ClosedLoopExecutor -> SkillRegistry -> EmpiricalVerification -> CrossDomain ->
    Curiosity -> SleepConsolidation -> AdaptationGuard -> ProactiveAssistant.
    """
    _instance: Optional['VoidAgent'] = None

    def __init__(self):
        self.state_manager = state_manager
        self.event_bus = event_bus
        self.security = security_manager
        self.tools = tool_registry
        self.memory = void_memory
        self.planner = agent_planner
        self.model_mgr = model_manager
        self.coordinator = agent_coordinator
        self.supervisor = supervisor
        self.world_model = world_model
        self.self_model = self_model
        self.experience_memory = experience_memory
        self.hierarchical_planner = hierarchical_planner
        self.closed_loop_executor = closed_loop_executor
        self.skill_registry = skill_registry
        self.empirical_engine = empirical_engine
        self.contradiction_resolver = contradiction_resolver
        self.cross_domain_engine = cross_domain_engine
        self.curiosity_engine = curiosity_engine
        self.consolidation_daemon = consolidation_daemon
        self.adaptation_guard = adaptation_guard
        self.proactive_assistant = proactive_assistant

    @classmethod
    def get_instance(cls) -> 'VoidAgent':
        if cls._instance is None:
            cls._instance = VoidAgent()
        return cls._instance


    def run_task(
        self,
        goal: str,
        force_search: bool = False,
        thinking_mode: bool = False,
        user_settings: Optional[Dict[str, Any]] = None,
        token_callback: Optional[Any] = None
    ) -> AgentResult:
        """
        Executes a user goal through the Meta-Cognitive Supervisor and Multi-Agent Network.
        """
        start_time = time.time()
        self.state_manager.set_current_task(goal)

        # 1. Initialize Structured Cognitive State
        cog_state = self.supervisor.initialize_state(goal)
        self.supervisor.evaluate_resource_budget(cog_state)

        # 2. Extract Learned Procedural Rules from Past Experiences
        relevant_rules = self.experience_memory.get_procedural_rules_for_situation(goal)

        # 3. Dispatch task to ExecutiveAgent via Coordinator with cognitive grounding
        task_msg = AgentMessage(
            sender="user_interface",
            receiver="executive",
            goal=goal,
            task_id=cog_state.task_id,
            mission_id=cog_state.mission_id,
            context={
                "procedural_rules": relevant_rules,
                "complexity": cog_state.complexity.value,
                "confidence": cog_state.confidence
            },
            payload={
                "query": goal,
                "force_search": force_search,
                "thinking_mode": thinking_mode,
                "settings": user_settings or {},
                "procedural_rules": relevant_rules,
                "token_callback": token_callback
            }
        )


        response_msg = self.coordinator.route_message(task_msg)
        duration = round(time.time() - start_time, 4)
        self.state_manager.set_current_task(None)

        # 4. Record Experience into Persistent Experience Memory
        is_success = (response_msg.status == "SUCCESS")
        failure_cause = response_msg.error if not is_success else None
        self.experience_memory.record_experience(
            task_id=cog_state.task_id,
            situation=goal,
            action="execute_multi_agent_network",
            expected_result="Valid verified response",
            actual_result=str(response_msg.result)[:200] if response_msg.result else "None",
            success=is_success,
            failure_cause=failure_cause,
            domain="multi_agent"
        )
        self.self_model.record_skill_outcome("multi_agent", success=is_success)

        # 5. Finalize Cognitive State
        self.supervisor.finalize_task(cog_state, str(response_msg.result), status=response_msg.status)

        # Build execution plan
        plan = self.planner.create_plan(goal, force_search=force_search, thinking_mode=thinking_mode)

        resolved_skill = "multi_agent"
        executed_tools = [("multi_agent_network", response_msg.result)]
        if response_msg.payload:
            resolved_skill = response_msg.payload.get("intent") or response_msg.payload.get("skill") or "multi_agent"
            if "workspace" in response_msg.payload and isinstance(response_msg.payload["workspace"], dict):
                obs = response_msg.payload["workspace"].get("observations", [])
                if obs:
                    executed_tools = [(o.get("agent", "agent"), o.get("observation", "")) for o in obs]

        return AgentResult(
            response=str(response_msg.result),
            status=response_msg.status,
            skill=resolved_skill,
            plan=plan,
            executed_tools=executed_tools,
            sources=["MetaCognitiveSupervisor", "ExecutiveAgent", "MultiAgentCoordinator"],
            duration_s=duration,
            cognitive_state=cog_state.to_dict()
        )

agent = VoidAgent.get_instance()

