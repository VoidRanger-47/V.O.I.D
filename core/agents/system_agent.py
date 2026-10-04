# core/agents/system_agent.py
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from core.state_manager import state_manager
from skills.computer_control import get_local_system_stats

class SystemAgent(BaseAgent):
    """
    Dedicated System Agent (Zero-LLM Deterministic).
    Monitors hardware telemetry (CPU, GPU, VRAM, RAM, Disk, Battery), active processes, and Guardian alerts.
    """
    def __init__(self):
        super().__init__(
            name="system_agent",
            role="Monitors local hardware telemetry, system metrics, and Guardian health thresholds",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )
        self.state_mgr = state_manager

    def process(self, message: AgentMessage) -> AgentMessage:
        action = message.payload.get("action", "stats")

        if action == "world_state":
            state = self.state_mgr.get_world_state()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=state,
                payload=state
            )

        elif action == "hardware_summary":
            stats_text = get_local_system_stats()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=stats_text,
                payload={"stats_text": stats_text}
            )

        else:
            stats_text = get_local_system_stats()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=stats_text,
                payload={"stats": stats_text}
            )
