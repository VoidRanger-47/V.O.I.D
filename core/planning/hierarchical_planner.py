# core/planning/hierarchical_planner.py
"""
Hierarchical 4-Level Planner for V.O.I.D.
Provides multi-level goal decomposition:
  LEVEL 1: Long-term Objective
  LEVEL 2: Major Milestones
  LEVEL 3: Tasks (prerequisites, required tools, cost estimate, verification method, fallback)
  LEVEL 4: Individual Actions
Supports dynamic re-planning when an action fails verification.
"""

import time
import uuid
import re
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


class PlanLevel(str, Enum):
    LEVEL_1_OBJECTIVE = "OBJECTIVE"
    LEVEL_2_MILESTONE = "MILESTONE"
    LEVEL_3_TASK = "TASK"
    LEVEL_4_ACTION = "ACTION"


class NodeStatus(str, Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    REPLANNING = "REPLANNING"


@dataclass
class ActionNode:
    id: str = field(default_factory=lambda: f"act_{str(uuid.uuid4())[:6]}")
    description: str = ""
    agent: str = "coding_agent"
    tool_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    expected_result: str = ""
    resource_cost: str = "LOW"  # LOW, MEDIUM, HIGH
    verification_method: str = "syntax_and_output"  # syntax_and_output, file_presence, test_assertion, non_empty
    fallback_strategy: Optional[str] = None
    status: NodeStatus = NodeStatus.PENDING
    actual_result: Optional[Any] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        return d


@dataclass
class TaskNode:
    id: str = field(default_factory=lambda: f"tsk_{str(uuid.uuid4())[:6]}")
    description: str = ""
    milestone_id: str = ""
    actions: List[ActionNode] = field(default_factory=list)
    prerequisites: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        d["actions"] = [a.to_dict() for a in self.actions]
        return d


@dataclass
class MilestoneNode:
    id: str = field(default_factory=lambda: f"mls_{str(uuid.uuid4())[:6]}")
    name: str = ""
    tasks: List[TaskNode] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value if isinstance(self.status, Enum) else self.status
        d["tasks"] = [t.to_dict() for t in self.tasks]
        return d


@dataclass
class HierarchicalPlan:
    objective: str
    plan_id: str = field(default_factory=lambda: f"plan_{str(uuid.uuid4())[:8]}")
    milestones: List[MilestoneNode] = field(default_factory=list)
    status: NodeStatus = NodeStatus.PENDING
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def total_actions_count(self) -> int:
        return sum(len(t.actions) for m in self.milestones for t in m.tasks)

    def get_pending_actions(self) -> List[ActionNode]:
        pending = []
        for m in self.milestones:
            for t in m.tasks:
                for a in t.actions:
                    if a.status in (NodeStatus.PENDING, NodeStatus.REPLANNING):
                        pending.append(a)
        return pending

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "objective": self.objective,
            "status": self.status.value if isinstance(self.status, Enum) else self.status,
            "total_actions": self.total_actions_count(),
            "milestones": [m.to_dict() for m in self.milestones],
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }


class HierarchicalPlanner:
    """
    Decomposes user objectives across 4 hierarchical tiers:
    Objective -> Milestones -> Tasks -> Actions.
    """
    _instance: Optional['HierarchicalPlanner'] = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> 'HierarchicalPlanner':
        if cls._instance is None:
            cls._instance = HierarchicalPlanner()
        return cls._instance

    def decompose(self, goal: str, context: Optional[Dict[str, Any]] = None) -> HierarchicalPlan:
        """
        Decomposes a user goal into a complete 4-level hierarchical plan.
        """
        clean_goal = goal.strip()
        low = clean_goal.lower()
        plan = HierarchicalPlan(objective=clean_goal)

        # 1. Coding / Software Engineering Goal
        if any(k in low for k in ["build", "develop", "implement", "fix", "code", "refactor", "debug"]):
            m1 = MilestoneNode(name="Environment & Specification Analysis")
            m1.tasks.append(TaskNode(
                description="Inspect workspace and analyze dependencies",
                milestone_id=m1.id,
                actions=[
                    ActionNode(
                        description="Query project structure and available files",
                        agent="coding_agent",
                        tool_name="workspace_inspector",
                        verification_method="non_empty",
                        fallback_strategy="Query system_agent for local path fallback"
                    ),
                    ActionNode(
                        description="Recall project architecture from memory",
                        agent="memory_agent",
                        tool_name="memory_retrieve",
                        verification_method="non_empty",
                        fallback_strategy="Scan local README.md directly"
                    )
                ]
            ))

            m2 = MilestoneNode(name="Implementation & Code Generation")
            m2.tasks.append(TaskNode(
                description="Write and integrate code modules",
                milestone_id=m2.id,
                prerequisites=[m1.id],
                actions=[
                    ActionNode(
                        description=f"Implement solution for: {clean_goal}",
                        agent="coding_agent",
                        tool_name="ast_sandbox",
                        verification_method="syntax_and_output",
                        fallback_strategy="Diagnose syntax errors and apply auto-repair"
                    )
                ]
            ))

            m3 = MilestoneNode(name="Verification & Quality Audit")
            m3.tasks.append(TaskNode(
                description="Execute verification test suite",
                milestone_id=m3.id,
                prerequisites=[m2.id],
                actions=[
                    ActionNode(
                        description="Verify output against test assertions",
                        agent="verification_agent",
                        tool_name="test_runner",
                        verification_method="test_assertion",
                        fallback_strategy="Revert code changes and re-plan implementation"
                    )
                ]
            ))
            plan.milestones = [m1, m2, m3]
            return plan

        # 2. Mathematical Problem Solving
        if any(k in low for k in ["calculate", "solve", "math", "equation", "derivative", "integral", "matrix"]):
            m1 = MilestoneNode(name="Mathematical Formalization")
            m1.tasks.append(TaskNode(
                description="Parse mathematical formulation and variables",
                milestone_id=m1.id,
                actions=[
                    ActionNode(
                        description=f"Parse mathematical equation for: {clean_goal}",
                        agent="mathematics_agent",
                        tool_name="math_solver",
                        verification_method="non_empty",
                        fallback_strategy="Use SymPy computer algebra solver"
                    )
                ]
            ))

            m2 = MilestoneNode(name="Calculation & Invariant Verification")
            m2.tasks.append(TaskNode(
                description="Execute rigorous calculation and proof verification",
                milestone_id=m2.id,
                prerequisites=[m1.id],
                actions=[
                    ActionNode(
                        description="Verify mathematical solution invariants",
                        agent="verification_agent",
                        verification_method="test_assertion",
                        fallback_strategy="Recompute with high-precision arithmetic"
                    )
                ]
            ))
            plan.milestones = [m1, m2]
            return plan

        # 3. Default Multi-Step Goal
        m_default = MilestoneNode(name="Goal Execution & Verification")
        m_default.tasks.append(TaskNode(
            description=f"Execute: {clean_goal}",
            milestone_id=m_default.id,
            actions=[
                ActionNode(
                    description=f"Execute primary directive: {clean_goal}",
                    agent="executive",
                    verification_method="non_empty",
                    fallback_strategy="Escalate to user or alternative agent"
                ),
                ActionNode(
                    description="Audit execution outcome",
                    agent="verification_agent",
                    verification_method="non_empty",
                    fallback_strategy="Log diagnostic failure trace"
                )
            ]
        ))
        plan.milestones = [m_default]
        return plan

    def replan_on_failure(self, plan: HierarchicalPlan, failed_action_id: str, failure_cause: str) -> bool:
        """
        Dynamically adjusts the plan when an action fails, applying fallback strategies.
        """
        for m in plan.milestones:
            for t in m.tasks:
                for idx, a in enumerate(t.actions):
                    if a.id == failed_action_id:
                        a.status = NodeStatus.FAILED
                        a.error = failure_cause

                        if a.fallback_strategy:
                            # Generate recovery action
                            recovery_act = ActionNode(
                                description=f"Recovery: {a.fallback_strategy} (Cause: {failure_cause[:40]})",
                                agent="coding_agent" if "code" in a.fallback_strategy.lower() else "executive",
                                verification_method=a.verification_method,
                                fallback_strategy="Escalate to admin approval",
                                status=NodeStatus.REPLANNING
                            )
                            # Insert recovery action immediately after failed action
                            t.actions.insert(idx + 1, recovery_act)
                            plan.updated_at = time.time()
                            return True
                        return False
        return False


hierarchical_planner = HierarchicalPlanner.get_instance()
