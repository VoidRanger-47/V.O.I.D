# core/agents/scheduler.py
"""
Dependency-Aware Parallel Agent Task Scheduler for V.O.I.D.
Coordinates concurrent execution of independent agents while strictly respecting:
  1. Task dependency graphs (DAG)
  2. 4 GB VRAM budget via VRAMManager
  3. Priority scheduling (HIGH user tasks > MEDIUM indexing > LOW reflection)
  4. Task timeouts and cancellation
"""

import time
import uuid
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed, Future
from typing import Dict, Any, List, Optional, Set, Callable

from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.agents.workspace import SharedWorkspace
from core.vram_manager import vram_manager, VRAMThreshold
from core.event_bus import event_bus, SystemEvent
from core.audit_logger import audit_logger


class AgentTaskScheduler:
    """
    Executes a directed acyclic graph (DAG) of agent tasks with parallel concurrency.
    """
    _instance: Optional['AgentTaskScheduler'] = None
    _lock = threading.Lock()

    def __init__(self, max_workers: int = 4):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="VOID-AgentPool")
        self.vram_mgr = vram_manager
        self._cancelled_tasks: Set[str] = set()

    @classmethod
    def get_instance(cls) -> 'AgentTaskScheduler':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = AgentTaskScheduler()
        return cls._instance

    def cancel_task(self, task_id: str):
        """Marks a task or plan as cancelled."""
        with self._lock:
            self._cancelled_tasks.add(task_id)

    def is_cancelled(self, task_id: str) -> bool:
        with self._lock:
            return task_id in self._cancelled_tasks

    def execute_dag(
        self,
        steps: List[Dict[str, Any]],
        workspace: SharedWorkspace,
        route_func: Callable[[AgentMessage], AgentMessage],
        mission_id: Optional[str] = None
    ) -> List[AgentMessage]:
        """
        Executes a planned list of steps as a dependency-aware parallel DAG.

        Each step format:
        {
            "step_id": 1,
            "agent": "system_agent",
            "goal": "...",
            "payload": {...},
            "dependencies": [],        # list of step_ids this task depends on
            "priority": AgentPriority.NORMAL,
            "timeout": 30.0
        }
        """
        start_time = time.time()
        completed_step_ids: Set[Any] = set()
        failed_step_ids: Set[Any] = set()
        step_results: Dict[Any, AgentMessage] = {}
        pending_steps: Dict[Any, Dict[str, Any]] = {s.get("step_id", idx): s for idx, s in enumerate(steps)}

        event_bus.publish(SystemEvent.TASK_CREATED, {
            "task_id": workspace.task_id,
            "total_steps": len(steps),
            "goal": workspace.goal
        })

        # Process steps until all are completed or blocked
        while pending_steps:
            if self.is_cancelled(workspace.task_id):
                workspace.status = "CANCELLED"
                break

            # Check VRAM state
            stats = self.vram_mgr.get_telemetry()
            if stats["threshold_state"] == VRAMThreshold.CRITICAL.value:
                self.vram_mgr.emergency_cleanup()

            # Find ready steps: all dependencies completed successfully
            ready_step_ids = []
            for s_id, s_data in pending_steps.items():
                deps = set(s_data.get("dependencies", []))
                # If any dependency failed, this step fails
                if deps.intersection(failed_step_ids):
                    failed_step_ids.add(s_id)
                    continue

                if deps.issubset(completed_step_ids):
                    ready_step_ids.append(s_id)

            # Purge permanently failed dependent steps
            for f_id in list(failed_step_ids):
                if f_id in pending_steps:
                    fail_msg = AgentMessage(
                        sender="scheduler",
                        receiver=pending_steps[f_id].get("agent", "unknown"),
                        task_id=workspace.task_id,
                        mission_id=mission_id,
                        status="FAILED",
                        error=f"Prerequisite step(s) failed.",
                        result=f"Prerequisite failure for step {f_id}."
                    )
                    step_results[f_id] = fail_msg
                    workspace.add_error(pending_steps[f_id].get("agent", "unknown"), f"Step {f_id} skipped due to dependency failure.")
                    del pending_steps[f_id]

            if not ready_step_ids:
                # No steps ready and pending steps remain -> deadlock or cycle
                if pending_steps:
                    for s_id, s_data in list(pending_steps.items()):
                        workspace.add_error("scheduler", f"Deadlock or unresolvable dependencies for step {s_id}")
                        failed_step_ids.add(s_id)
                        del pending_steps[s_id]
                break

            # Execute ready steps in parallel
            futures: Dict[Future, Any] = {}
            for s_id in ready_step_ids:
                step_data = pending_steps[s_id]
                # Inject workspace context into step payload
                payload = dict(step_data.get("payload", {}))
                payload["workspace_context"] = workspace.get_summary()

                msg = AgentMessage(
                    sender="scheduler",
                    receiver=step_data.get("agent"),
                    goal=step_data.get("goal", workspace.goal),
                    task_id=f"{workspace.task_id}_s{s_id}",
                    mission_id=mission_id,
                    priority=step_data.get("priority", AgentPriority.NORMAL),
                    payload=payload,
                    timeout=float(step_data.get("timeout", 30.0))
                )

                # Submit to thread pool
                fut = self.executor.submit(self._dispatch_step, msg, route_func, s_id, workspace)
                futures[fut] = s_id
                del pending_steps[s_id]

            # Wait for the batch of parallel steps to finish
            for fut in as_completed(futures):
                s_id = futures[fut]
                try:
                    res_msg = fut.result()
                    step_results[s_id] = res_msg

                    if res_msg.status == "SUCCESS":
                        completed_step_ids.add(s_id)
                        # Record structured findings into SharedWorkspace
                        target_agent = res_msg.sender
                        workspace.set_intermediate_result(f"step_{s_id}_result", res_msg.result, agent_name=target_agent)
                        if res_msg.payload.get("artifact"):
                            workspace.add_artifact(f"step_{s_id}_artifact", res_msg.payload["artifact"])
                    else:
                        failed_step_ids.add(s_id)
                        workspace.add_error(res_msg.sender, res_msg.error or str(res_msg.result))

                except Exception as e:
                    failed_step_ids.add(s_id)
                    err_msg = AgentMessage(
                        sender="scheduler",
                        receiver="unknown",
                        task_id=workspace.task_id,
                        status="FAILED",
                        error=str(e),
                        result=f"Execution error on step {s_id}: {str(e)}"
                    )
                    step_results[s_id] = err_msg
                    workspace.add_error("scheduler", str(e))

        duration = round(time.time() - start_time, 4)
        status = "SUCCESS" if not failed_step_ids else ("PARTIAL" if completed_step_ids else "FAILED")
        workspace.status = status

        event_bus.publish(SystemEvent.TASK_COMPLETED, {
            "task_id": workspace.task_id,
            "status": status,
            "completed_steps": len(completed_step_ids),
            "failed_steps": len(failed_step_ids),
            "duration_s": duration
        })

        # Return results ordered by step_id
        ordered_results = [step_results[k] for k in sorted(step_results.keys())]
        return ordered_results

    def _dispatch_step(
        self,
        msg: AgentMessage,
        route_func: Callable[[AgentMessage], AgentMessage],
        step_id: Any,
        workspace: SharedWorkspace
    ) -> AgentMessage:
        """Helper to invoke route_message and report status to event bus."""
        event_bus.publish(SystemEvent.AGENT_TASK_CREATED, {
            "step_id": step_id,
            "agent": msg.receiver,
            "goal": msg.goal,
            "task_id": msg.task_id
        })
        start_t = time.time()
        res = route_func(msg)
        elapsed = round(time.time() - start_t, 4)

        workspace.add_tool_output(
            tool_name=msg.receiver,
            output=res.result,
            agent_name=msg.receiver,
            duration=elapsed
        )
        return res


task_scheduler = AgentTaskScheduler.get_instance()
