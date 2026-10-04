# core/agents/protocol.py
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List

class AgentMessageType(str, Enum):
    REQUEST = "REQUEST"
    RESPONSE = "RESPONSE"
    RESPOND = "RESPONSE"
    EVENT = "EVENT"
    DELEGATE = "DELEGATE"
    REPORT = "STATUS_UPDATE"
    VERIFY = "VERIFY"
    STATUS_UPDATE = "STATUS_UPDATE"
    FAIL = "FAIL"
    RETRY = "RETRY"
    CANCEL = "CANCEL"

class AgentPriority(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"
    BACKGROUND = "BACKGROUND"

@dataclass
class AgentMessage:
    sender: str
    receiver: str
    message_type: AgentMessageType = AgentMessageType.REQUEST
    priority: AgentPriority = AgentPriority.NORMAL
    goal: str = ""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    mission_id: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    payload: Dict[str, Any] = field(default_factory=dict)
    artifact_refs: List[str] = field(default_factory=list)
    confidence: float = 1.0
    result: Optional[Any] = None
    status: str = "PENDING"  # PENDING, IN_PROGRESS, SUCCESS, FAILED, REPLAN_REQUIRED, CANCELLED
    error: Optional[str] = None
    max_retries: int = 2
    timeout: float = 30.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "mission_id": self.mission_id,
            "sender": self.sender,
            "receiver": self.receiver,
            "message_type": self.message_type.value if isinstance(self.message_type, AgentMessageType) else str(self.message_type),
            "priority": self.priority.value if isinstance(self.priority, AgentPriority) else str(self.priority),
            "goal": self.goal,
            "dependencies": self.dependencies,
            "artifact_refs": self.artifact_refs,
            "confidence": self.confidence,
            "status": self.status,
            "error": self.error,
            "timestamp": self.timestamp,
            "result_summary": str(self.result)[:200] if self.result is not None else None
        }
