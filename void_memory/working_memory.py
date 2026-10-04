# void_memory/working_memory.py
"""
Task-Isolated Working Memory & Active Context Manager for V.O.I.D.
Provides real-time conversation scratchpads and isolated memory spaces for agents.
"""

from collections import deque
from typing import Dict, Any, List, Optional
import time

from void_memory.database.models import MemoryNode, MemoryTier


class WorkingMemoryManager:
    """
    Manages in-memory working scratchpad and task-specific agent contexts.
    """

    def __init__(self, conversation_limit: int = 15):
        self.conversation_limit = conversation_limit
        # Active rolling conversation history
        self.conversation_history = deque(maxlen=conversation_limit)
        # Task-isolated scratchpads: task_id -> {facts, intermediate_results, timestamp}
        self.task_scratchpads: Dict[str, Dict[str, Any]] = {}

    def append_turn(self, speaker: str, text: str):
        """Append a dialog turn (e.g. 'User', 'V.O.I.D.')."""
        clean = text.strip()
        if clean:
            self.conversation_history.append(f"{speaker}: {clean}")

    def get_recent_conversation(self, num_turns: Optional[int] = None) -> List[str]:
        """Return formatted recent dialog turns."""
        turns = list(self.conversation_history)
        if num_turns:
            turns = turns[-num_turns:]
        return turns

    def clear_conversation(self):
        self.conversation_history.clear()

    # =========================================================================
    # TASK-ISOLATED AGENT WORKING CONTEXTS
    # =========================================================================

    def init_task_context(self, task_id: str, goal: str, metadata: Optional[Dict[str, Any]] = None):
        """Initialize an isolated scratchpad for an agent task."""
        self.task_scratchpads[task_id] = {
            "task_id": task_id,
            "goal": goal,
            "facts": [],
            "intermediate_results": [],
            "plan_steps": [],
            "metadata": metadata or {},
            "created_at": time.time(),
            "updated_at": time.time()
        }

    def add_task_fact(self, task_id: str, fact: str):
        if task_id not in self.task_scratchpads:
            self.init_task_context(task_id, "Generic task")
        self.task_scratchpads[task_id]["facts"].append({
            "fact": fact.strip(),
            "timestamp": time.time()
        })
        self.task_scratchpads[task_id]["updated_at"] = time.time()

    def add_intermediate_result(self, task_id: str, agent_name: str, result: Any):
        if task_id not in self.task_scratchpads:
            self.init_task_context(task_id, "Generic task")
        self.task_scratchpads[task_id]["intermediate_results"].append({
            "agent": agent_name,
            "result": result,
            "timestamp": time.time()
        })
        self.task_scratchpads[task_id]["updated_at"] = time.time()

    def get_task_context(self, task_id: str) -> Optional[Dict[str, Any]]:
        return self.task_scratchpads.get(task_id)

    def close_task_context(self, task_id: str, promote_results: bool = False) -> List[str]:
        """
        Closes task context. Returns list of facts that should be promoted to long-term memory.
        """
        ctx = self.task_scratchpads.pop(task_id, None)
        if not ctx or not promote_results:
            return []

        promoted = []
        for f in ctx.get("facts", []):
            promoted.append(f["fact"])
        return promoted
