# core/agents/automation_agent.py
import time
from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel

class AutomationAgent(BaseAgent):
    """
    Dedicated Automation & Scheduling Agent.
    Manages reminders, background health checks, recurring memory optimization sweeps, and timer triggers.
    """
    def __init__(self):
        super().__init__(
            name="automation_agent",
            role="Manages background tasks, scheduled jobs, timers, and periodic system sweeps",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )
        self.scheduled_tasks: List[Dict[str, Any]] = []

    def process(self, message: AgentMessage) -> AgentMessage:
        action = message.payload.get("action", "list_tasks")

        if action == "schedule":
            task_name = message.payload.get("name", message.goal)
            delay_seconds = float(message.payload.get("delay", 60.0))
            task_entry = {
                "id": len(self.scheduled_tasks) + 1,
                "name": task_name,
                "trigger_at": time.time() + delay_seconds,
                "created_at": time.time(),
                "status": "SCHEDULED"
            }
            self.scheduled_tasks.append(task_entry)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=f"Scheduled task '{task_name}' in {int(delay_seconds)} seconds.",
                payload={"task": task_entry}
            )

        elif action == "optimize_memory":
            from void_memory.memory import void_memory
            pruned_count = void_memory.prune_weak_memories()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=f"Memory optimization complete. Pruned {pruned_count} weak memory entries.",
                payload={"pruned": pruned_count}
            )

        else:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=f"Automation Agent active. {len(self.scheduled_tasks)} tasks in queue.",
                payload={"tasks": self.scheduled_tasks}
            )
