# core/agents/perception.py
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from core.state_manager import state_manager

class PerceptionAgent(BaseAgent):
    """
    Dedicated Perception Agent.
    Aggregates environmental context, foreground application awareness, and multimodal sensory inputs
    into structured observations for the Executive Core.
    """
    def __init__(self):
        super().__init__(
            name="perception_agent",
            role="Perceives computer state, active window context, and multimodal sensory inputs",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )
        self.state_mgr = state_manager

    def process(self, message: AgentMessage) -> AgentMessage:
        world_state = self.state_mgr.get_world_state()
        observation = {
            "time": world_state["current_time"],
            "active_window": world_state["active_window"],
            "active_application": world_state["active_application"],
            "network_status": world_state["network_status"],
            "offline_mode": world_state["offline_mode"],
            "cpu_load": f"{world_state['cpu_usage_percent']}%",
            "ram_used": f"{world_state['ram_used_gb']} GB / {world_state['ram_total_gb']} GB",
            "vram_used": f"{world_state['vram_used_gb']} GB / {world_state['vram_total_gb']} GB"
        }

        obs_summary = (
            f"Perception State: Working on '{world_state['current_project']}' in '{world_state['active_window']}'. "
            f"Network: {world_state['network_status']}."
        )

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="SUCCESS",
            result=obs_summary,
            payload=observation
        )
