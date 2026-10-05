# core/agents/executive.py
import time
from typing import Dict, Any, List, Optional

from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.agents.coordinator import agent_coordinator
from core.agents.workspace import SharedWorkspace
from core.security import PermissionLevel
from providers.manager import model_manager
from core.vram_manager import vram_manager
from core.router import executive_router, ExecutionPath
from core.context_manager import context_manager
from core.memory_policy import memory_write_policy, MemoryVerdict


class ExecutiveAgent(BaseAgent):
    """
    V.O.I.D. Executive Agent (Central Orchestrator).
    Routes between Fast Path (deterministic) and Deep Path (multi-agent parallel DAG).
    Governs SharedWorkspace, context compression, objective verification, and memory write policies.
    """
    def __init__(self):
        super().__init__(
            name="executive",
            role="Central decision engine, mission orchestrator, router, and inter-agent coordinator",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=True
        )
        self.coordinator = agent_coordinator
        self.model_mgr = model_manager
        self.vram_mgr = vram_manager
        self.router = executive_router
        self.context_mgr = context_manager
        self.memory_policy = memory_write_policy

    def process(self, message: AgentMessage) -> AgentMessage:
        goal = message.goal or message.payload.get("query", "")
        if not goal.strip():
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result="I am listening. How can I assist you?",
                payload={"reply": "I am listening."}
            )

        force_search = bool(message.payload.get("force_search", False))
        thinking_mode = bool(message.payload.get("thinking_mode", False))

        token_callback = message.payload.get("token_callback")

        # Handle direct scheduler invocation without recursion
        if message.sender == "scheduler":
            provider = self.model_mgr.get_active_provider() or self.model_mgr.get_provider("local_transformer")
            if token_callback and hasattr(provider, "generate_stream"):
                toks = []
                for tok in provider.generate_stream(goal, max_new_tokens=250, temperature=0.5):
                    toks.append(tok)
                    try:
                        token_callback(tok)
                    except Exception:
                        pass
                final_ans = "".join(toks).strip()
            else:
                final_ans = provider.generate(goal, max_new_tokens=250, temperature=0.5)

            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=final_ans,
                payload={"final_answer": final_ans}
            )

        # ===================================================================
        # STAGE 0: FAST PATH CHECK (Deterministic, Ultra-low Latency, 0 VRAM)
        # ===================================================================
        path_decision, fast_result, intent_class = self.router.route(
            goal,
            force_search=force_search,
            thinking_mode=thinking_mode
        )

        if path_decision == ExecutionPath.FAST_PATH and fast_result is not None:
            # Stream fast tokens immediately if callback provided
            if token_callback:
                import re
                words = re.findall(r'\S+|\s+', fast_result)
                for w in words:
                    try:
                        token_callback(w)
                    except Exception:
                        pass

            # Evaluate memory write policy even for fast results
            verdict, score, _ = self.memory_policy.evaluate(goal, fast_result, is_multi_step=False)
            if verdict != MemoryVerdict.REJECT:
                self._record_memory(goal, fast_result, verdict, score)

            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=fast_result,
                payload={
                    "execution_path": "FAST_PATH",
                    "intent": intent_class.value,
                    "final_answer": fast_result
                }
            )

        # ===================================================================
        # STAGE 1: DEEP PATH — INITIALIZE WORKSPACE & PERCEPTION
        # ===================================================================
        workspace = SharedWorkspace(
            task_id=message.task_id,
            goal=goal,
            mission_id=message.mission_id,
            context=message.context
        )

        perceive_msg = AgentMessage(
            sender=self.name,
            receiver="perception_agent",
            goal="Get active environment and context",
            task_id=message.task_id
        )
        perception_res = self.coordinator.route_message(perceive_msg)
        workspace.add_observation("perception_agent", str(perception_res.result), perception_res.payload)

        # ===================================================================
        # STAGE 2: DEEP PATH — HIERARCHICAL PLANNING (DAG TASK GRAPH)
        # ===================================================================
        plan_msg = AgentMessage(
            sender=self.name,
            receiver="planning_agent",
            goal=goal,
            task_id=message.task_id,
            payload={"goal": goal, "perception": perception_res.payload}
        )
        plan_res = self.coordinator.route_message(plan_msg)
        steps = plan_res.payload.get("steps", [])

        # ===================================================================
        # STAGE 3: PARALLEL DAG EXECUTION & SYNTHESIS
        # ===================================================================
        # Exclude 'executive' from subagent step dispatching to guarantee no recursive deadlock
        subagent_steps = [s for s in steps if s.get("agent") != "executive"]
        step_results = self.coordinator.execute_parallel_dag(
            steps=subagent_steps,
            workspace=workspace,
            mission_id=message.mission_id
        )

        # Determine if any agent produced a final direct answer
        final_answer = None
        for res in step_results:
            if res.receiver in ["math_agent", "coding_agent", "system_agent", "computer_agent", "research_agent", "knowledge_agent"] and res.status == "SUCCESS":
                if res.result and len(str(res.result)) > 5:
                    final_answer = str(res.result)

        # If no single direct answer or conversational goal, synthesize via compressed context
        if not final_answer:
            synthesis_context = self.context_mgr.build_synthesis_context(goal, workspace=workspace)

            safe, vram_msg = self.vram_mgr.is_safe_for_inference(estimated_mb=400.0)
            if safe:
                provider = self.model_mgr.get_active_provider()
                if provider is None:
                    provider = self.model_mgr.get_provider("local_transformer")
                prompt = (
                    f"{synthesis_context}\n\n"
                    f"### User Goal:\n{goal}\n"
                    f"### V.O.I.D. Synthesis:\n"
                )
                if token_callback and hasattr(provider, "generate_stream"):
                    toks = []
                    for tok in provider.generate_stream(prompt, max_new_tokens=350, temperature=0.5):
                        toks.append(tok)
                        try:
                            token_callback(tok)
                        except Exception:
                            pass
                    final_answer = "".join(toks).strip() or "I am listening. How can I assist you further?"
                else:
                    final_answer = provider.generate(prompt, max_new_tokens=350, temperature=0.5)
            else:
                summaries = [f"[{s.receiver.upper()}]: {s.result}" for s in step_results if s.result]
                final_answer = "\n\n".join(summaries) if summaries else "Goal executed successfully."
                if token_callback:
                    import re
                    for w in re.findall(r'\S+|\s+', final_answer):
                        try:
                            token_callback(w)
                        except Exception:
                            pass
        elif token_callback and final_answer:
            import re
            for w in re.findall(r'\S+|\s+', final_answer):
                try:
                    token_callback(w)
                except Exception:
                    pass



        # ===================================================================
        # STAGE 4: VERIFICATION AUDIT
        # ===================================================================
        verify_msg = AgentMessage(
            sender=self.name,
            receiver="verification_agent",
            goal=f"Verify result for: {goal}",
            task_id=message.task_id,
            payload={"output": final_answer, "expected_type": "general"}
        )
        verify_res = self.coordinator.route_message(verify_msg)
        workspace.add_verification("verification_agent", verify_res.payload.get("verdict", "PASS"), str(verify_res.result))

        # If verification failed, perform self-healing recovery once
        if verify_res.status != "SUCCESS":
            replan_msg = AgentMessage(
                sender=self.name,
                receiver="planning_agent",
                goal=goal,
                task_id=message.task_id,
                payload={"action": "replan", "failed_step": goal, "error": verify_res.result}
            )
            replan_res = self.coordinator.route_message(replan_msg)
            recovery_steps = replan_res.payload.get("steps", [])
            if recovery_steps:
                recovery_results = self.coordinator.execute_parallel_dag(steps=recovery_steps, workspace=workspace)
                for r in recovery_results:
                    if r.status == "SUCCESS" and r.result:
                        final_answer = str(r.result)

        workspace.set_final_result(final_answer, status="COMPLETED")

        # ===================================================================
        # STAGE 5: MEMORY WRITE POLICY EVALUATION
        # ===================================================================
        verdict, score, _ = self.memory_policy.evaluate(goal, final_answer, is_multi_step=(len(steps) >= 2))
        if verdict != MemoryVerdict.REJECT:
            self._record_memory(goal, final_answer, verdict, score)

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="SUCCESS",
            result=final_answer,
            payload={
                "execution_path": "DEEP_PATH",
                "steps_executed": len(step_results),
                "final_answer": final_answer,
                "workspace": workspace.to_dict()
            }
        )

    def _record_memory(self, goal: str, answer: str, verdict: MemoryVerdict, score: float):
        """Dispatches filtered, verified memory storage."""
        tier = "semantic"
        if verdict == MemoryVerdict.STORE_EPISODIC:
            tier = "episodic"
        elif verdict == MemoryVerdict.STORE_PREFERENCE:
            tier = "preference"

        mem_msg = AgentMessage(
            sender=self.name,
            receiver="memory_agent",
            goal="Store filtered memory fact",
            payload={
                "action": "store",
                "text": f"User: '{goal[:80]}'. Outcome: '{str(answer)[:120]}'",
                "tier": tier,
                "importance": score
            }
        )
        self.coordinator.route_message(mem_msg)


executive_agent = ExecutiveAgent()
