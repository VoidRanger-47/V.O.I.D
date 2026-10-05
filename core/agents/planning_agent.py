# core/agents/planning_agent.py
import re
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.security import PermissionLevel

class PlanningAgent(BaseAgent):
    """
    Dedicated Planning Agent.
    Converts complex user goals into verifiable multi-agent DAG task graphs and dynamic recovery plans.
    """
    def __init__(self):
        super().__init__(
            name="planning_agent",
            role="Constructs multi-agent task graphs, schedules dependencies, and generates recovery plans",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )

    def process(self, message: AgentMessage) -> AgentMessage:
        goal = message.payload.get("goal", message.goal)
        action = message.payload.get("action", "create_plan")

        if action == "replan":
            failed_step = message.payload.get("failed_step", "unknown")
            error_reason = message.payload.get("error", "unspecified error")
            recovery_steps = [
                {
                    "step_id": 1,
                    "agent": "system_agent",
                    "goal": "Check system health and environment state",
                    "payload": {"action": "stats"},
                    "priority": AgentPriority.HIGH
                },
                {
                    "step_id": 2,
                    "agent": "memory_agent",
                    "goal": f"Retrieve architectural context for: {goal}",
                    "payload": {"action": "retrieve", "query": goal},
                    "priority": AgentPriority.HIGH
                },
                {
                    "step_id": 3,
                    "agent": "coding_agent",
                    "goal": f"Apply alternative strategy for: {goal}",
                    "payload": {"query": goal},
                    "priority": AgentPriority.NORMAL
                },
                {
                    "step_id": 4,
                    "agent": "verification_agent",
                    "goal": "Verify recovery results",
                    "payload": {"expected_type": "general"},
                    "priority": AgentPriority.HIGH
                }
            ]
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result="Generated dynamic recovery plan.",
                payload={"plan_type": "RECOVERY", "steps": recovery_steps}
            )

        # Generate standard multi-agent execution plan
        steps = self._decompose_goal(goal)
        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="SUCCESS",
            result=f"Plan generated with {len(steps)} step(s).",
            payload={"plan_type": "STANDARD", "steps": steps}
        )

    def _decompose_goal(self, goal: str) -> List[Dict[str, Any]]:
        clean = (goal or "").strip()
        low = clean.lower()

        # 1. Memory forget command
        if any(term in low for term in ["forget that", "forget what", "delete memory", "clear memory"]):
            return [{
                "step_id": 1,
                "agent": "memory_agent",
                "goal": "Purge memory",
                "payload": {"action": "forget", "target": clean},
                "dependencies": [],
                "can_parallelize": False,
                "priority": AgentPriority.HIGH
            }]

        # 2. Memory store command
        if "remember" in low and not any(k in low for k in ["do you remember", "can you remember"]):
            return [{
                "step_id": 1,
                "agent": "memory_agent",
                "goal": "Store memory fact",
                "payload": {"action": "store", "text": clean, "importance": 0.9},
                "dependencies": [],
                "can_parallelize": False,
                "priority": AgentPriority.HIGH
            }]

        # 3. System Hardware / Stats
        if any(term in low for term in ["system stats", "cpu usage", "ram usage", "vram", "hardware status", "system metrics"]):
            return [{
                "step_id": 1,
                "agent": "system_agent",
                "goal": "Query hardware telemetry",
                "payload": {"action": "stats"},
                "dependencies": [],
                "can_parallelize": False,
                "priority": AgentPriority.NORMAL
            }]

        # 4. Computer control (open application)
        if any(term in low for term in ["open vs code", "open vscode", "open notepad", "open calculator", "launch ", "start vs code", "open terminal"]):
            app = clean.lower().replace("open", "").replace("launch", "").replace("start", "").strip()
            return [
                {
                    "step_id": 1,
                    "agent": "computer_agent",
                    "goal": f"Launch desktop app: {app}",
                    "payload": {"action": "launch", "app_name": app},
                    "dependencies": [],
                    "can_parallelize": False,
                    "priority": AgentPriority.HIGH
                },
                {
                    "step_id": 2,
                    "agent": "verification_agent",
                    "goal": "Verify app launch result",
                    "payload": {"expected_type": "general"},
                    "dependencies": [1],
                    "can_parallelize": False,
                    "priority": AgentPriority.NORMAL
                }
            ]

        # 5. Multi-step diagnostic & project debug (Independent steps 1, 2, 3 run in parallel!)
        if any(term in low for term in ["why isn't my project", "diagnose project", "debug my code", "fix project", "improve v.o.i.d", "analyze this project", "bottlenecks", "suggest improvements"]):
            return [
                {
                    "step_id": 1,
                    "agent": "system_agent",
                    "goal": "Inspect hardware and environment status",
                    "payload": {"action": "world_state"},
                    "dependencies": [],
                    "can_parallelize": True,
                    "priority": AgentPriority.HIGH
                },
                {
                    "step_id": 2,
                    "agent": "memory_agent",
                    "goal": f"Retrieve project memory context for: {clean}",
                    "payload": {"action": "retrieve", "query": clean},
                    "dependencies": [],
                    "can_parallelize": True,
                    "priority": AgentPriority.HIGH
                },
                {
                    "step_id": 3,
                    "agent": "knowledge_agent",
                    "goal": f"Retrieve local documentation snippets for: {clean}",
                    "payload": {"query": clean},
                    "dependencies": [],
                    "can_parallelize": True,
                    "priority": AgentPriority.NORMAL
                },
                {
                    "step_id": 4,
                    "agent": "coding_agent",
                    "goal": f"Synthesize diagnostic and patch for: {clean}",
                    "payload": {"query": clean},
                    "dependencies": [1, 2, 3],
                    "can_parallelize": False,
                    "priority": AgentPriority.HIGH
                },
                {
                    "step_id": 5,
                    "agent": "verification_agent",
                    "goal": "Verify diagnostic resolution",
                    "payload": {"expected_type": "general"},
                    "dependencies": [4],
                    "can_parallelize": False,
                    "priority": AgentPriority.HIGH
                }
            ]

        # 6. Web research
        if any(term in low for term in ["search web", "check online", "latest news", "weather today"]):
            return [{
                "step_id": 1,
                "agent": "research_agent",
                "goal": f"Perform web search: {clean}",
                "payload": {"query": clean},
                "dependencies": [],
                "can_parallelize": False,
                "priority": AgentPriority.NORMAL
            }]

        # 7. Deterministic Math calculation (routed to dedicated math_agent)
        has_math = bool(
            re.search(r"(\d+\s*[\+\-\*\/\^%]\s*\d+)", clean) or
            ("=" in clean and any(c.isalpha() for c in clean)) or
            re.search(r"\b(d/dx|integral|sin|cos|tan|matrix|determinant|sqrt)\b", low)
        )
        if has_math:
            return [
                {
                    "step_id": 1,
                    "agent": "math_agent",
                    "goal": f"Solve math formula: {clean}",
                    "payload": {"action": "solve", "query": clean},
                    "dependencies": [],
                    "can_parallelize": False,
                    "priority": AgentPriority.NORMAL
                },
                {
                    "step_id": 2,
                    "agent": "verification_agent",
                    "goal": "Verify math calculation",
                    "payload": {"expected_type": "math"},
                    "dependencies": [1],
                    "can_parallelize": False,
                    "priority": AgentPriority.HIGH
                }
            ]

        # 8. General conversational / coding request
        if any(k in low for k in ["code", "python", "debug", "script", "function", "class", "refactor"]):
            return [
                {
                    "step_id": 1,
                    "agent": "memory_agent",
                    "goal": f"Fetch context for: {clean}",
                    "payload": {"action": "inject_context", "query": clean},
                    "dependencies": [],
                    "can_parallelize": False,
                    "priority": AgentPriority.NORMAL
                },
                {
                    "step_id": 2,
                    "agent": "coding_agent",
                    "goal": clean,
                    "payload": {"query": clean},
                    "dependencies": [1],
                    "can_parallelize": False,
                    "priority": AgentPriority.NORMAL
                }
            ]

        # For conversation, fetch relevant context into workspace and let Executive synthesize
        return [
            {
                "step_id": 1,
                "agent": "memory_agent",
                "goal": f"Fetch context for: {clean}",
                "payload": {"action": "inject_context", "query": clean},
                "dependencies": [],
                "can_parallelize": False,
                "priority": AgentPriority.NORMAL
            }
        ]

