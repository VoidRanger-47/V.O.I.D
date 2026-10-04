"""
core/agents/pipeline.py
Autonomous Multi-Agent Pipeline for V.O.I.D.
Orchestrates: Planner -> Researcher -> Coder -> Executor -> Verifier -> Self-Reflection
"""

import time
import uuid
from typing import Dict, Any, List, Optional, Generator

from core.agents.coordinator import AgentCoordinator
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.agents.planning_agent import PlanningAgent
from core.agents.research_agent import ResearchAgent
from core.agents.coding_agent import CodingAgent
from core.agents.executive import ExecutiveAgent
from core.agents.verification_agent import VerificationAgent
from core.agents.reflection import reflection_engine
from core.security import security_manager


class MultiAgentPipeline:
    """
    Orchestrates the 5-stage agent system:
    Stage 1: Planner      — Decomposes goal into structured multi-agent tasks
    Stage 2: Researcher   — Gathers workspace symbols, project context, and factual references
    Stage 3: Coder        — Synthesizes AST-validated code, scripts, or architectural logic
    Stage 4: Executor     — Executes the code or tools in a sandboxed runtime
    Stage 5: Verifier     — Audits output against objective criteria (syntax, exit code, errors)
    Stage 6: Reflection   — Evaluates what worked/failed and persists procedural lessons.
    """
    _instance: Optional['MultiAgentPipeline'] = None

    def __init__(self):
        self.coordinator = AgentCoordinator.get_instance()
        self._ensure_agents_registered()

    @classmethod
    def get_instance(cls) -> 'MultiAgentPipeline':
        if cls._instance is None:
            cls._instance = MultiAgentPipeline()
        return cls._instance

    def _ensure_agents_registered(self):
        """Registers all core pipeline agents in the central coordinator."""
        if not self.coordinator.get_agent("planning_agent"):
            self.coordinator.register_agent(PlanningAgent())
        if not self.coordinator.get_agent("research_agent"):
            self.coordinator.register_agent(ResearchAgent())
        if not self.coordinator.get_agent("coding_agent"):
            self.coordinator.register_agent(CodingAgent())
        if not self.coordinator.get_agent("executive"):
            self.coordinator.register_agent(ExecutiveAgent())
        if not self.coordinator.get_agent("verification_agent"):
            self.coordinator.register_agent(VerificationAgent())
        if not self.coordinator.get_agent("math_agent"):
            from core.agents.mathematics_agent import MathematicsAgent
            self.coordinator.register_agent(MathematicsAgent())

    def run_pipeline(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Runs the full 5-stage agent pipeline synchronously.
        """
        pipeline_id = f"pipe_{str(uuid.uuid4())[:8]}"
        start_time = time.time()
        stages_record = []
        overall_success = True
        error_message = None

        # -------------------------------------------------------------
        # STAGE 1: PLANNER
        # -------------------------------------------------------------
        plan_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="planning_agent",
            goal=goal,
            task_id=f"{pipeline_id}_plan",
            payload={"goal": goal, "action": "create_plan", "context": context or {}}
        )
        plan_res = self.coordinator.route_message(plan_msg)
        plan_data = plan_res.payload.get("plan", {})
        subtasks = plan_data.get("subtasks", [])

        stages_record.append({
            "stage": 1,
            "agent": "planner",
            "name": "Planning Agent",
            "goal": "Decompose goal into structured milestones",
            "status": plan_res.status,
            "output": plan_res.result or f"Plan generated with {len(subtasks)} subtasks.",
            "details": plan_data
        })

        # -------------------------------------------------------------
        # STAGE 2: RESEARCHER
        # -------------------------------------------------------------
        research_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="research_agent",
            goal=f"Research context and symbols for: {goal}",
            task_id=f"{pipeline_id}_research",
            payload={"query": goal, "context": context or {}}
        )
        research_res = self.coordinator.route_message(research_msg)
        research_info = research_res.result or "Project workspace and references inspected."

        # Also retrieve workspace symbol references for coding context
        try:
            from skills.coding_engine import coding_engine
            symbol_matches = coding_engine.find_symbols(goal[:30])
        except Exception:
            symbol_matches = []

        stages_record.append({
            "stage": 2,
            "agent": "researcher",
            "name": "Research Agent",
            "goal": "Gather relevant symbols, documentation, and references",
            "status": research_res.status,
            "output": str(research_info)[:300],
            "symbols_found": len(symbol_matches)
        })

        # -------------------------------------------------------------
        # STAGE 3: CODER
        # -------------------------------------------------------------
        coder_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="coding_agent",
            goal=goal,
            task_id=f"{pipeline_id}_code",
            payload={
                "query": goal,
                "action": "auto",
                "research_context": research_info,
                "symbols": symbol_matches
            }
        )
        coder_res = self.coordinator.route_message(coder_msg)
        generated_code = coder_res.payload.get("generated_code") or coder_res.result

        stages_record.append({
            "stage": 3,
            "agent": "coder",
            "name": "Coding Agent",
            "goal": "Synthesize AST-validated implementation",
            "status": coder_res.status,
            "output": str(generated_code)[:400],
            "code_payload": generated_code
        })

        # -------------------------------------------------------------
        # STAGE 4: EXECUTOR
        # -------------------------------------------------------------
        exec_output = None
        code_to_exec = str(generated_code or "")
        if "```" in code_to_exec:
            if "```python" in code_to_exec:
                code_to_exec = code_to_exec.split("```python", 1)[1].split("```", 1)[0].strip()
            else:
                code_to_exec = code_to_exec.split("```", 1)[1].split("```", 1)[0].strip()

        if code_to_exec and ("def " in code_to_exec or "print(" in code_to_exec or "import " in code_to_exec):
            # Execute in AST sandboxed python interpreter
            sandbox_res = security_manager.execute_sandboxed_python(code_to_exec)
            exec_output = sandbox_res.get("output", "")
            exec_status = "SUCCESS" if sandbox_res.get("success") else "FAILED"
        else:
            exec_output = coder_res.result or "Logic formulated without runtime execution requirement."
            exec_status = "SUCCESS"

        stages_record.append({
            "stage": 4,
            "agent": "executor",
            "name": "Execution Agent",
            "goal": "Execute code/logic in sandboxed environment",
            "status": exec_status,
            "output": str(exec_output)[:400]
        })

        if exec_status == "FAILED":
            overall_success = False
            error_message = f"Execution failed: {exec_output}"

        # -------------------------------------------------------------
        # STAGE 5: VERIFIER
        # -------------------------------------------------------------
        verify_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="verification_agent",
            goal="Verify task outcome against criteria",
            task_id=f"{pipeline_id}_verify",
            payload={
                "output": exec_output or coder_res.result,
                "expected_type": "general"
            }
        )
        verify_res = self.coordinator.route_message(verify_msg)
        verdict = verify_res.payload.get("verdict", "PASS" if overall_success else "FAIL")

        stages_record.append({
            "stage": 5,
            "agent": "verifier",
            "name": "Verification Agent",
            "goal": "Audit outputs against objective criteria",
            "status": verify_res.status,
            "verdict": verdict,
            "output": verify_res.result or f"Verification verdict: {verdict}"
        })

        if verdict == "FAIL":
            overall_success = False

        duration_ms = round((time.time() - start_time) * 1000, 2)

        # -------------------------------------------------------------
        # STAGE 6: SELF-REFLECTION
        # -------------------------------------------------------------
        reflection = reflection_engine.evaluate_task(
            goal=goal,
            steps=stages_record,
            output=exec_output or coder_res.result,
            success=overall_success,
            task_id=pipeline_id,
            duration_ms=duration_ms,
            error=error_message
        )

        return {
            "pipeline_id": pipeline_id,
            "goal": goal,
            "success": overall_success,
            "duration_ms": duration_ms,
            "stages": stages_record,
            "final_output": exec_output or coder_res.result,
            "reflection": reflection
        }

    def stream_pipeline(self, goal: str, context: Optional[Dict[str, Any]] = None) -> Generator[Dict[str, Any], None, None]:
        """
        Yields real-time stage execution updates for frontend streaming.
        """
        pipeline_id = f"pipe_{str(uuid.uuid4())[:8]}"
        start_time = time.time()
        stages_record = []
        overall_success = True

        yield {"event": "pipeline_start", "pipeline_id": pipeline_id, "goal": goal}

        # Stage 1: Planner
        yield {"event": "stage_start", "stage": 1, "agent": "planner", "title": "Planner: Decomposing Goal"}
        plan_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="planning_agent",
            goal=goal,
            task_id=f"{pipeline_id}_plan",
            payload={"goal": goal, "action": "create_plan", "context": context or {}}
        )
        plan_res = self.coordinator.route_message(plan_msg)
        stage_1_info = {
            "stage": 1, "agent": "planner", "status": plan_res.status,
            "output": plan_res.result or "Milestone plan created."
        }
        stages_record.append(stage_1_info)
        yield {"event": "stage_complete", **stage_1_info}

        # Stage 2: Researcher
        yield {"event": "stage_start", "stage": 2, "agent": "researcher", "title": "Researcher: Indexing Context & Symbols"}
        research_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="research_agent",
            goal=goal,
            task_id=f"{pipeline_id}_research",
            payload={"query": goal}
        )
        research_res = self.coordinator.route_message(research_msg)
        stage_2_info = {
            "stage": 2, "agent": "researcher", "status": research_res.status,
            "output": str(research_res.result or "Context retrieved")[:250]
        }
        stages_record.append(stage_2_info)
        yield {"event": "stage_complete", **stage_2_info}

        # Stage 3: Coder
        yield {"event": "stage_start", "stage": 3, "agent": "coder", "title": "Coder: Synthesizing Implementation"}
        coder_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="coding_agent",
            goal=goal,
            task_id=f"{pipeline_id}_code",
            payload={"query": goal, "action": "auto"}
        )
        coder_res = self.coordinator.route_message(coder_msg)
        gen_code = coder_res.payload.get("generated_code") or coder_res.result
        stage_3_info = {
            "stage": 3, "agent": "coder", "status": coder_res.status,
            "output": str(gen_code)[:300], "code": gen_code
        }
        stages_record.append(stage_3_info)
        yield {"event": "stage_complete", **stage_3_info}

        # Stage 4: Executor
        yield {"event": "stage_start", "stage": 4, "agent": "executor", "title": "Executor: Sandboxed Execution"}
        if gen_code and any(k in str(gen_code) for k in ["def ", "print(", "import "]):
            sandbox_res = security_manager.execute_sandboxed_python(str(gen_code))
            exec_out = sandbox_res.get("output", "")
            exec_stat = "SUCCESS" if sandbox_res.get("success") else "FAILED"
        else:
            exec_out = coder_res.result or "Logic validated."
            exec_stat = "SUCCESS"
        stage_4_info = {
            "stage": 4, "agent": "executor", "status": exec_stat, "output": str(exec_out)[:300]
        }
        stages_record.append(stage_4_info)
        yield {"event": "stage_complete", **stage_4_info}

        # Stage 5: Verifier
        yield {"event": "stage_start", "stage": 5, "agent": "verifier", "title": "Verifier: Objective Audit"}
        verify_msg = AgentMessage(
            sender="pipeline_runner",
            receiver="verification_agent",
            goal="Verify",
            task_id=f"{pipeline_id}_verify",
            payload={"output": exec_out}
        )
        verify_res = self.coordinator.route_message(verify_msg)
        stage_5_info = {
            "stage": 5, "agent": "verifier", "status": verify_res.status,
            "verdict": verify_res.payload.get("verdict", "PASS"),
            "output": verify_res.result or "Audit complete."
        }
        stages_record.append(stage_5_info)
        yield {"event": "stage_complete", **stage_5_info}

        # Stage 6: Self-Reflection
        duration_ms = round((time.time() - start_time) * 1000, 2)
        reflection = reflection_engine.evaluate_task(
            goal=goal,
            steps=stages_record,
            output=exec_out,
            success=overall_success,
            task_id=pipeline_id,
            duration_ms=duration_ms
        )
        yield {
            "event": "pipeline_complete",
            "pipeline_id": pipeline_id,
            "success": overall_success,
            "duration_ms": duration_ms,
            "final_output": exec_out,
            "reflection": reflection
        }


agent_pipeline = MultiAgentPipeline.get_instance()
