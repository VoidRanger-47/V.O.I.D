# core/execution/closed_loop.py
"""
Closed-Loop Agent Executor for V.O.I.D.
Enforces:
  PLAN -> ACTION -> OBSERVE -> VERIFY
  Success?
    YES -> Continue
    NO  -> Diagnose -> Replan -> Retry
Never assumes success; audits every action before proceeding.
"""

import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field

from core.planning.hierarchical_planner import (
    HierarchicalPlan,
    ActionNode,
    NodeStatus,
    hierarchical_planner
)
from core.agents.coordinator import agent_coordinator
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from void_memory.experience_memory import experience_memory
from core.audit_logger import audit_logger


@dataclass
class ExecutionSummary:
    plan_id: str
    status: str  # SUCCESS, FAILED, PARTIAL
    total_actions: int
    completed_actions: int
    failed_actions: int
    replanned_actions: int
    final_output: Optional[Any] = None
    diagnostics: List[str] = field(default_factory=list)
    duration_s: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "status": self.status,
            "total_actions": self.total_actions,
            "completed_actions": self.completed_actions,
            "failed_actions": self.failed_actions,
            "replanned_actions": self.replanned_actions,
            "final_output": str(self.final_output)[:300] if self.final_output else None,
            "diagnostics": self.diagnostics,
            "duration_s": round(self.duration_s, 4)
        }


class ClosedLoopExecutor:
    """
    Executes hierarchical plans with closed-loop verification, failure diagnosis, and dynamic replanning.
    """
    _instance: Optional['ClosedLoopExecutor'] = None

    def __init__(self):
        self.coordinator = agent_coordinator
        self.planner = hierarchical_planner
        self.exp_memory = experience_memory

    @classmethod
    def get_instance(cls) -> 'ClosedLoopExecutor':
        if cls._instance is None:
            cls._instance = ClosedLoopExecutor()
        return cls._instance

    def verify_action_result(self, action: ActionNode, output: Any, status: str) -> Tuple[bool, str]:
        """
        Applies objective verification rules to action output.
        """
        if status != "SUCCESS":
            return False, f"Agent reported execution status: {status}"

        out_str = str(output) if output is not None else ""
        if not out_str.strip():
            return False, "Output was empty or null"

        # Check for error indicators
        if any(err in out_str for err in ["❌", "Syntax Error:", "Traceback (most recent call last):", "Command failed with code"]):
            return False, f"Output contains explicit error signature: {out_str[:80]}"

        # Method specific verification
        if action.verification_method == "test_assertion":
            if "FAIL" in out_str.upper() or "ASSERTIONERROR" in out_str.upper():
                return False, "Assertion test failed verification"

        return True, "Objective verification passed"

    def execute_plan(self, plan: HierarchicalPlan, task_id: str = "task_exec", max_retries: int = 3) -> ExecutionSummary:
        """
        Executes a HierarchicalPlan in a verified closed loop.
        """
        start_t = time.time()
        completed = 0
        failed = 0
        replanned = 0
        diagnostics = []
        final_answer = None

        plan.status = NodeStatus.IN_PROGRESS

        for milestone in plan.milestones:
            milestone.status = NodeStatus.IN_PROGRESS

            for task in milestone.tasks:
                task.status = NodeStatus.IN_PROGRESS
                action_idx = 0

                while action_idx < len(task.actions):
                    action = task.actions[action_idx]
                    action.status = NodeStatus.IN_PROGRESS

                    # 1. ACTION
                    msg = AgentMessage(
                        sender="closed_loop_executor",
                        receiver=action.agent,
                        goal=action.description,
                        task_id=task_id,
                        payload={
                            "action": action.tool_name or action.description,
                            "query": action.description,
                            "parameters": action.parameters
                        }
                    )
                    response_msg = self.coordinator.route_message(msg)

                    # 2. OBSERVE
                    raw_result = response_msg.result
                    action.actual_result = raw_result

                    # 3. VERIFY
                    is_verified, reason = self.verify_action_result(action, raw_result, response_msg.status)

                    # 4. CLOSED-LOOP ARBITRATION
                    if is_verified:
                        action.status = NodeStatus.COMPLETED
                        completed += 1
                        final_answer = raw_result
                        action_idx += 1
                    else:
                        action.status = NodeStatus.FAILED
                        action.error = reason
                        failed += 1
                        diag = f"Action '{action.description[:40]}' failed: {reason}"
                        diagnostics.append(diag)

                        # Record failed experience
                        self.exp_memory.record_experience(
                            task_id=task_id,
                            situation=action.description,
                            action=f"{action.agent}:{action.tool_name}",
                            expected_result=action.expected_result,
                            actual_result=str(raw_result)[:150],
                            success=False,
                            failure_cause=reason,
                            better_strategy=action.fallback_strategy,
                            domain="execution"
                        )

                        # DIAGNOSE & REPLAN
                        if replanned < max_retries:
                            replan_success = self.planner.replan_on_failure(plan, action.id, reason)
                            if replan_success:
                                replanned += 1
                                diagnostics.append(f"Dynamic replanning triggered: inserted recovery action.")
                                # Move to newly inserted recovery action
                                action_idx += 1
                                continue

                        # Exceeded retries or no fallback available
                        task.status = NodeStatus.FAILED
                        milestone.status = NodeStatus.FAILED
                        plan.status = NodeStatus.FAILED
                        return ExecutionSummary(
                            plan_id=plan.plan_id,
                            status="FAILED",
                            total_actions=plan.total_actions_count(),
                            completed_actions=completed,
                            failed_actions=failed,
                            replanned_actions=replanned,
                            final_output=raw_result or reason,
                            diagnostics=diagnostics,
                            duration_s=time.time() - start_t
                        )

                task.status = NodeStatus.COMPLETED

            milestone.status = NodeStatus.COMPLETED

        plan.status = NodeStatus.COMPLETED
        return ExecutionSummary(
            plan_id=plan.plan_id,
            status="SUCCESS",
            total_actions=plan.total_actions_count(),
            completed_actions=completed,
            failed_actions=failed,
            replanned_actions=replanned,
            final_output=final_answer or "Plan executed and verified successfully.",
            diagnostics=diagnostics,
            duration_s=time.time() - start_t
        )


closed_loop_executor = ClosedLoopExecutor.get_instance()
