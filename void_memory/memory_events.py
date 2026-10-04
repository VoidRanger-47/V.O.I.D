# void_memory/memory_events.py
"""
Event-Driven Memory Handler for V.O.I.D.
Integrates the memory engine with V.O.I.D.'s EventBus for automated background extraction,
consolidation, and telemetry.
"""

import threading
from typing import Dict, Any, Optional

from core.event_bus import event_bus


class MemoryEventHandler:
    """
    Subscribes to system events and executes memory actions in background threads.
    """

    def __init__(self, memory_manager: Any):
        self.memory_manager = memory_manager
        self._subscribe_events()

    def _subscribe_events(self):
        try:
            event_bus.subscribe("CONVERSATION_TURN", self._on_conversation_turn)
            event_bus.subscribe("TASK_COMPLETED", self._on_task_completed)
            event_bus.subscribe("PROJECT_DECISION", self._on_project_decision)
        except Exception as e:
            print(f"ℹ️ Memory event subscription note: {e}")

    def _on_conversation_turn(self, event_data: Dict[str, Any]):
        """Runs background memory extraction without blocking active responses."""
        user_msg = event_data.get("user_message", "")
        asst_msg = event_data.get("assistant_response", "")
        project_id = event_data.get("project_id", "VOID")

        if user_msg:
            threading.Thread(
                target=self.memory_manager.extract_and_store_from_turn,
                args=(user_msg, asst_msg, project_id),
                daemon=True
            ).start()

    def _on_task_completed(self, event_data: Dict[str, Any]):
        """Promotes verified task working memory to long-term memory."""
        task_id = event_data.get("task_id")
        if task_id:
            threading.Thread(
                target=self.memory_manager.working_memory.close_task_context,
                args=(task_id, True),
                daemon=True
            ).start()

    def _on_project_decision(self, event_data: Dict[str, Any]):
        title = event_data.get("title", "")
        rationale = event_data.get("rationale", "")
        if title and rationale:
            self.memory_manager.project_memory.record_decision(title, rationale)
