# core/task_lifecycle.py
"""
Task Lifecycle and Interruption Controller for V.O.I.D.
Provides responsive STOP, PAUSE, RESUME, and CANCEL capabilities.
Guarantees real interruption of neural inference and thread-pool execution,
instantly releasing GPU VRAM and CPU resources.
"""

import time
import threading
from enum import Enum
from typing import Dict, Any, Optional, Set

from core.event_bus import event_bus, SystemEvent
from core.vram_manager import vram_manager
from core.agents.scheduler import task_scheduler


class TaskState(str, Enum):
    IDLE = "IDLE"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPED = "STOPPED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class TaskLifecycleController:
    """
    Central controller for task state and execution interruption.
    """
    _instance: Optional['TaskLifecycleController'] = None
    _lock = threading.Lock()

    def __init__(self):
        self._task_states: Dict[str, TaskState] = {}
        self._cancellation_events: Dict[str, threading.Event] = {}
        self._pause_events: Dict[str, threading.Event] = {}
        self._active_tasks: Set[str] = set()

    @classmethod
    def get_instance(cls) -> 'TaskLifecycleController':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = TaskLifecycleController()
        return cls._instance

    def register_task(self, task_id: str) -> threading.Event:
        """Registers a new active task and returns its cancellation event."""
        with self._lock:
            self._task_states[task_id] = TaskState.RUNNING
            self._active_tasks.add(task_id)
            cancel_ev = threading.Event()
            self._cancellation_events[task_id] = cancel_ev
            pause_ev = threading.Event()
            pause_ev.set()  # Not paused by default (set means running)
            self._pause_events[task_id] = pause_ev
            return cancel_ev

    def should_stop(self, task_id: str) -> bool:
        """Returns True if the task has been requested to stop or cancel."""
        with self._lock:
            ev = self._cancellation_events.get(task_id)
            return ev.is_set() if ev else False

    def wait_if_paused(self, task_id: str, timeout: float = 1.0) -> bool:
        """Blocks while paused until resumed or timeout."""
        with self._lock:
            ev = self._pause_events.get(task_id)
        if ev:
            return ev.wait(timeout=timeout)
        return True

    def stop_task(self, task_id: str, reason: str = "User stop requested") -> bool:
        """
        Interrupts inference, halts scheduler tasks, and releases GPU memory.
        """
        with self._lock:
            if task_id in self._cancellation_events:
                self._cancellation_events[task_id].set()
            if task_id in self._pause_events:
                self._pause_events[task_id].set()  # Unblock if waiting
            self._task_states[task_id] = TaskState.STOPPED
            self._active_tasks.discard(task_id)

        # Notify scheduler and clean memory
        task_scheduler.cancel_task(task_id)
        vram_manager.cleanup_vram(force=True)

        event_bus.publish(SystemEvent.STOPPED, {
            "task_id": task_id,
            "reason": reason,
            "timestamp": time.time()
        })
        return True

    def cancel_task(self, task_id: str) -> bool:
        """Hard cancellation of task."""
        return self.stop_task(task_id, reason="User cancelled task")

    def pause_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._pause_events:
                self._pause_events[task_id].clear()
                self._task_states[task_id] = TaskState.PAUSED
                event_bus.publish(SystemEvent.PAUSED, {"task_id": task_id})
                return True
            return False

    def resume_task(self, task_id: str) -> bool:
        with self._lock:
            if task_id in self._pause_events:
                self._pause_events[task_id].set()
                self._task_states[task_id] = TaskState.RUNNING
                event_bus.publish(SystemEvent.RESUMED, {"task_id": task_id})
                return True
            return False

    def complete_task(self, task_id: str):
        with self._lock:
            self._task_states[task_id] = TaskState.COMPLETED
            self._active_tasks.discard(task_id)

    def get_state(self, task_id: str) -> TaskState:
        with self._lock:
            return self._task_states.get(task_id, TaskState.IDLE)


task_lifecycle = TaskLifecycleController.get_instance()
