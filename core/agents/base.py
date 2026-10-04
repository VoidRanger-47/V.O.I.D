# core/agents/base.py
from abc import ABC, abstractmethod
from collections import deque
from enum import Enum
from typing import Dict, Any, List, Optional

from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.security import PermissionLevel, security_manager

class AgentStatus(str, Enum):
    IDLE = "IDLE"
    AVAILABLE = "AVAILABLE"
    THINKING = "THINKING"
    EXECUTING = "EXECUTING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    VERIFYING = "VERIFYING"
    FAILED = "FAILED"
    COMPLETED = "COMPLETED"

class BaseAgent(ABC):
    """
    Abstract Base Class for all V.O.I.D. Specialized Agents.
    Encapsulates private working memory, inbox/outbox, role definitions, and permission boundaries.
    """
    def __init__(
        self,
        name: str,
        role: str,
        permission_level: PermissionLevel = PermissionLevel.LEVEL_1_READ_INFO,
        is_llm_assisted: bool = False
    ):
        self.name = name
        self.role = role
        self.permission_level = permission_level
        self.is_llm_assisted = is_llm_assisted
        self.status = AgentStatus.IDLE
        self.private_memory = deque(maxlen=20)
        self.inbox: List[AgentMessage] = []
        self.outbox: List[AgentMessage] = []
        self.current_task_id: Optional[str] = None

    def set_status(self, new_status: AgentStatus):
        self.status = new_status

    def verify_permission(self) -> bool:
        return security_manager.verify_permission(self.permission_level, self.name)

    def receive_message(self, message: AgentMessage) -> AgentMessage:
        """Entry point for incoming messages from the Agent Coordinator."""
        self.verify_permission()
        self.inbox.append(message)
        self.current_task_id = message.task_id
        self.set_status(AgentStatus.EXECUTING)

        try:
            response_msg = self.process(message)
            self.set_status(AgentStatus.COMPLETED if response_msg.status == "SUCCESS" else AgentStatus.FAILED)
            self.outbox.append(response_msg)
            self.private_memory.append(f"Task {message.task_id} ({message.goal}): {response_msg.status}")
            return response_msg
        except Exception as e:
            self.set_status(AgentStatus.FAILED)
            error_msg = AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                error=str(e),
                result=f"❌ Agent '{self.name}' encountered failure: {str(e)}"
            )
            self.outbox.append(error_msg)
            return error_msg
        finally:
            self.set_status(AgentStatus.IDLE)
            self.current_task_id = None

    @abstractmethod
    def process(self, message: AgentMessage) -> AgentMessage:
        """Specialized processing logic implemented by each concrete agent."""
        pass

    def get_state(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "role": self.role,
            "status": self.status.value,
            "permission_level": self.permission_level.name,
            "is_llm_assisted": self.is_llm_assisted,
            "active_task": self.current_task_id,
            "memory_items": len(self.private_memory)
        }
