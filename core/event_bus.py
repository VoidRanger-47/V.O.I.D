# core/event_bus.py
import time
from enum import Enum
from typing import Dict, List, Callable, Any, Optional
from core.audit_logger import audit_logger

class SystemEvent(str, Enum):
    SYSTEM_STARTED = "SYSTEM_STARTED"
    SYSTEM_SHUTDOWN = "SYSTEM_SHUTDOWN"
    WAKE_WORD_DETECTED = "WAKE_WORD_DETECTED"
    VOICE_INPUT_STARTED = "VOICE_INPUT_STARTED"
    VOICE_INPUT_RECEIVED = "VOICE_INPUT_RECEIVED"
    USER_MESSAGE_RECEIVED = "USER_MESSAGE_RECEIVED"
    AGENT_TASK_CREATED = "AGENT_TASK_CREATED"
    PLAN_CREATED = "PLAN_CREATED"
    TOOL_STARTED = "TOOL_STARTED"
    TOOL_FINISHED = "TOOL_FINISHED"
    TOOL_FAILED = "TOOL_FAILED"
    MEMORY_CREATED = "MEMORY_CREATED"
    MEMORY_RETRIEVED = "MEMORY_RETRIEVED"
    TASK_CREATED = "TASK_CREATED"
    TASK_UPDATED = "TASK_UPDATED"
    TASK_COMPLETED = "TASK_COMPLETED"
    SYSTEM_ALERT = "SYSTEM_ALERT"
    RESPONSE_STARTED = "RESPONSE_STARTED"
    RESPONSE_FINISHED = "RESPONSE_FINISHED"
    # Progressive Streaming & Agent Pipeline Events
    START = "START"
    TOKEN = "TOKEN"
    TOOL_START = "TOOL_START"
    TOOL_RESULT = "TOOL_RESULT"
    AGENT_STATUS = "AGENT_STATUS"
    VERIFICATION = "VERIFICATION"
    COMPLETE = "COMPLETE"
    ERROR = "ERROR"
    STOPPED = "STOPPED"
    PAUSED = "PAUSED"
    RESUMED = "RESUMED"

class EventBus:
    """
    Central Pub-Sub Event Bus for V.O.I.D.
    Allows UI, Agent, Voice, System Guardian, and Memory to subscribe and publish events.
    """
    _instance: Optional['EventBus'] = None

    def __init__(self, max_history: int = 200):
        self.subscribers: Dict[str, List[Callable[[Dict[str, Any]], None]]] = {}
        self.history: List[Dict[str, Any]] = []
        self.max_history = max_history

    @classmethod
    def get_instance(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = EventBus()
        return cls._instance

    def subscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        """Subscribe a callable handler to a specific event type or '*' for all events."""
        ev_key = event_type.value if isinstance(event_type, SystemEvent) else str(event_type)
        if ev_key not in self.subscribers:
            self.subscribers[ev_key] = []
        self.subscribers[ev_key].append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[[Dict[str, Any]], None]):
        ev_key = event_type.value if isinstance(event_type, SystemEvent) else str(event_type)
        if ev_key in self.subscribers and handler in self.subscribers[ev_key]:
            self.subscribers[ev_key].remove(handler)

    def publish(self, event_type: SystemEvent | str, payload: Optional[Dict[str, Any]] = None):
        """Publish an event to all registered subscribers and audit log."""
        ev_name = event_type.value if isinstance(event_type, SystemEvent) else str(event_type)
        data = payload or {}
        event_record = {
            "event": ev_name,
            "timestamp": time.time(),
            "data": data
        }

        # Maintain in-memory circular history
        self.history.append(event_record)
        if len(self.history) > self.max_history:
            self.history.pop(0)

        # Audit log integration
        audit_logger.log(
            event=ev_name,
            tool=data.get("tool"),
            status=data.get("status", "INFO"),
            task_id=data.get("task_id"),
            duration=data.get("duration"),
            error=data.get("error"),
            result_summary=data.get("summary")
        )

        # Notify specific subscribers
        if ev_name in self.subscribers:
            for handler in self.subscribers[ev_name]:
                try:
                    handler(event_record)
                except Exception as e:
                    print(f"⚠️ Event handler error on '{ev_name}': {e}")

        # Notify wildcard subscribers
        if "*" in self.subscribers:
            for handler in self.subscribers["*"]:
                try:
                    handler(event_record)
                except Exception as e:
                    print(f"⚠️ Wildcard event handler error on '{ev_name}': {e}")

    def get_recent_events(self, count: int = 50) -> List[Dict[str, Any]]:
        return self.history[-count:]

event_bus = EventBus.get_instance()
