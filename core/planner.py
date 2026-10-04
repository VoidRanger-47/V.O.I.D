# core/planner.py
import re
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

@dataclass
class PlanStep:
    step_id: int
    description: str
    tool_name: Optional[str]
    tool_args: Dict[str, Any] = field(default_factory=dict)
    status: str = "PENDING"  # PENDING, IN_PROGRESS, COMPLETED, FAILED, SKIPPED
    result: Optional[Any] = None
    error: Optional[str] = None

@dataclass
class ExecutionPlan:
    goal: str
    is_multi_step: bool
    steps: List[PlanStep] = field(default_factory=list)
    confidence: str = "HIGH"  # HIGH, MEDIUM, LOW, UNKNOWN
    rationale: str = ""

class AgentPlanner:
    """
    Decomposes user goals into structured, verifiable execution plans.
    """
    def __init__(self):
        pass

    def create_plan(
        self,
        goal: str,
        force_search: bool = False,
        thinking_mode: bool = False
    ) -> ExecutionPlan:
        clean_goal = goal.strip()
        low = clean_goal.lower()

        # 1. Direct Memory / Forget commands
        if any(term in low for term in ["forget that", "forget what", "delete memory", "clear memory"]):
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description="Explicit memory deletion", tool_name="memory_forget", tool_args={"target": clean_goal})],
                rationale="User requested explicit memory deletion."
            )

        if "remember" in low and not any(k in low for k in ["do you remember", "can you remember"]):
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description="Store preference or fact in memory", tool_name="memory_store", tool_args={"text": clean_goal})],
                rationale="User requested memory retention."
            )

        # 2. System Hardware / Stats inspection
        if any(term in low for term in ["system stats", "cpu usage", "ram usage", "hardware status", "vram usage", "system metrics"]):
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description="Query local hardware metrics", tool_name="system_monitor", tool_args={})],
                rationale="System diagnostic query."
            )

        # 3. Time / System info
        if any(term in low for term in ["what time", "current time", "what date", "today's date", "system time"]):
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description="Retrieve current system timestamp", tool_name="system_info", tool_args={})],
                rationale="Time query."
            )

        # 4. Android Phone Control
        try:
            from void_phone.intent_parser import intent_parser, IntentType
            parsed_phone = intent_parser.parse(clean_goal)
            if parsed_phone.intent_type != IntentType.UNKNOWN and parsed_phone.confidence >= 0.85:
                # If explicit desktop app launch is requested (e.g. 'open vscode' vs 'open jiocinema')
                is_phone_explicit = any(k in low for k in ["phone", "android", "unlock", "call", "dial", "sms", "jiocinema", "jio cinema", "whatsapp", "whats app", "camera", "instagram", "battery level"])
                if is_phone_explicit or parsed_phone.intent_type in [IntentType.UNLOCK, IntentType.LOCK, IntentType.CALL, IntentType.DIAL, IntentType.SEND_SMS, IntentType.STATUS]:
                    return ExecutionPlan(
                        goal=clean_goal,
                        is_multi_step=False,
                        steps=[PlanStep(step_id=1, description=f"Execute phone action '{parsed_phone.intent_type.value}'", tool_name="phone_control", tool_args={"query": clean_goal})],
                        rationale=f"Phone automation intent: {parsed_phone.intent_type.value}."
                    )
        except Exception:
            pass

        # 5. Computer control (launch app)
        from skills.computer_control import is_app_launch_request, extract_app_target
        if is_app_launch_request(clean_goal):
            app_target = extract_app_target(clean_goal)
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description=f"Launch application '{app_target}'", tool_name="computer_control", tool_args={"app_name": app_target})],
                rationale="Desktop application launch."
            )


        # 5. Math solving
        has_math_formula = bool(
            re.search(r"(\d+\s*[\+\-\*\/\^%]\s*\d+)", clean_goal) or
            ("=" in clean_goal and any(c.isalpha() for c in clean_goal)) or
            re.search(r"\b(d/dx|integral|sin|cos|tan|matrix|determinant|sqrt)\b", low)
        )
        if has_math_formula and not force_search:
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description="Solve mathematical expression using SymPy", tool_name="math_solver", tool_args={"query": clean_goal})],
                rationale="Mathematical calculation."
            )

        # 6. Multi-step goal: "Inspect project and run diagnostics" or "Debug project"
        if any(term in low for term in ["why isn't my project", "diagnose project", "debug my code", "check why", "fix project"]):
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=True,
                steps=[
                    PlanStep(step_id=1, description="Inspect local system and project metrics", tool_name="system_monitor", tool_args={}),
                    PlanStep(step_id=2, description="Retrieve project memory and architecture decisions", tool_name="memory_rag", tool_args={"query": clean_goal}),
                    PlanStep(step_id=3, description="Synthesize root cause and propose verified solution", tool_name=None, tool_args={})
                ],
                confidence="HIGH",
                rationale="Multi-step diagnostic and reasoning workflow."
            )

        # 7. Web search (if forced or factual query)
        if force_search or any(term in low for term in ["search web", "check online", "latest news", "weather today"]):
            return ExecutionPlan(
                goal=clean_goal,
                is_multi_step=False,
                steps=[PlanStep(step_id=1, description="Query web search engine", tool_name="web_search", tool_args={"query": clean_goal})],
                rationale="External information retrieval."
            )

        # 8. Default Generative Conversation / Coding
        is_coding = any(term in low for term in ["code", "debug", "python", "function", "implement", "class", "script"])
        return ExecutionPlan(
            goal=clean_goal,
            is_multi_step=False,
            steps=[PlanStep(step_id=1, description="Generate response with neural model", tool_name=None, tool_args={"coding": is_coding, "thinking": thinking_mode})],
            confidence="HIGH",
            rationale="Neural language generation."
        )

agent_planner = AgentPlanner()
