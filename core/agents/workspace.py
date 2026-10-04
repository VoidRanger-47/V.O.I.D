# core/agents/workspace.py
"""
Thread-safe Shared Agent Workspace (Blackboard Architecture) for V.O.I.D.
Provides a structured shared memory substrate for cooperating agents during task execution.
Drastically cuts down prompt token bloat and enables parallel agent communication.
"""

import time
import uuid
import threading
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


@dataclass
class SharedWorkspace:
    """
    Shared blackboard for multi-agent missions and tasks.
    Agents concurrently write findings, intermediate results, tool outputs, and decisions here.
    """
    task_id: str
    goal: str
    mission_id: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)
    observations: List[Dict[str, Any]] = field(default_factory=list)
    artifacts: Dict[str, Any] = field(default_factory=dict)
    intermediate_results: Dict[str, Any] = field(default_factory=dict)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    tool_outputs: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    verification_results: List[Dict[str, Any]] = field(default_factory=list)
    final_result: Optional[str] = None
    status: str = "IN_PROGRESS"  # IN_PROGRESS, COMPLETED, FAILED, CANCELLED
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False, compare=False)

    def add_observation(self, agent_name: str, observation: str, data: Optional[Dict[str, Any]] = None):
        """Record an environmental or sensory observation."""
        with self._lock:
            self.observations.append({
                "agent": agent_name,
                "observation": observation,
                "data": data or {},
                "timestamp": time.time()
            })
            self.updated_at = time.time()

    def set_intermediate_result(self, key: str, value: Any, agent_name: str = "agent"):
        """Store an intermediate computation or result from an agent."""
        with self._lock:
            self.intermediate_results[key] = {
                "value": value,
                "agent": agent_name,
                "timestamp": time.time()
            }
            self.updated_at = time.time()

    def get_intermediate_result(self, key: str, default: Any = None) -> Any:
        """Retrieve an intermediate result."""
        with self._lock:
            item = self.intermediate_results.get(key)
            return item["value"] if item else default

    def add_tool_output(self, tool_name: str, output: Any, agent_name: str = "agent", duration: float = 0.0):
        """Append output from an executed deterministic or sensory tool."""
        with self._lock:
            self.tool_outputs.append({
                "tool": tool_name,
                "output": output,
                "agent": agent_name,
                "duration": duration,
                "timestamp": time.time()
            })
            self.updated_at = time.time()

    def add_artifact(self, artifact_id: str, content: Any, artifact_type: str = "text"):
        """Store an artifact (e.g. generated code, patch, table, formula, outline)."""
        with self._lock:
            self.artifacts[artifact_id] = {
                "type": artifact_type,
                "content": content,
                "timestamp": time.time()
            }
            self.updated_at = time.time()

    def add_decision(self, agent_name: str, decision: str, rationale: str = ""):
        """Log a strategic architectural or planning decision."""
        with self._lock:
            self.decisions.append({
                "agent": agent_name,
                "decision": decision,
                "rationale": rationale,
                "timestamp": time.time()
            })
            self.updated_at = time.time()

    def add_error(self, agent_name: str, error: str, details: Optional[Dict[str, Any]] = None):
        """Record an error or exception during execution."""
        with self._lock:
            self.errors.append({
                "agent": agent_name,
                "error": error,
                "details": details or {},
                "timestamp": time.time()
            })
            self.updated_at = time.time()

    def add_verification(self, agent_name: str, verdict: str, details: str = ""):
        """Add verification audit check (PASS / FAIL / REPLAN_REQUIRED)."""
        with self._lock:
            self.verification_results.append({
                "agent": agent_name,
                "verdict": verdict,
                "details": details,
                "timestamp": time.time()
            })
            self.updated_at = time.time()

    def set_final_result(self, result: str, status: str = "COMPLETED"):
        with self._lock:
            self.final_result = result
            self.status = status
            self.updated_at = time.time()

    def get_summary(self, max_tokens_estimate: int = 500) -> str:
        """
        Compresses the workspace into a concise structured summary for synthesis.
        Guarantees that agents do not dump raw full outputs into subsequent prompts.
        """
        with self._lock:
            lines = [f"### Goal: {self.goal}"]

            if self.observations:
                obs_items = [f"- [{o['agent']}]: {o['observation']}" for o in self.observations[-3:]]
                lines.append("Observations:\n" + "\n".join(obs_items))

            if self.intermediate_results:
                res_items = [f"- {k}: {str(v['value'])[:120]}" for k, v in list(self.intermediate_results.items())[-4:]]
                lines.append("Intermediate Findings:\n" + "\n".join(res_items))

            if self.artifacts:
                art_keys = list(self.artifacts.keys())
                lines.append(f"Artifacts Created: {', '.join(art_keys)}")

            if self.decisions:
                dec_items = [f"- [{d['agent']}]: {d['decision']}" for d in self.decisions[-2:]]
                lines.append("Decisions:\n" + "\n".join(dec_items))

            if self.errors:
                err_items = [f"- [{e['agent']}]: {e['error']}" for e in self.errors[-2:]]
                lines.append("Issues Encountered:\n" + "\n".join(err_items))

            return "\n\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "task_id": self.task_id,
                "mission_id": self.mission_id,
                "goal": self.goal,
                "status": self.status,
                "observations_count": len(self.observations),
                "intermediate_results_count": len(self.intermediate_results),
                "artifacts_count": len(self.artifacts),
                "decisions_count": len(self.decisions),
                "tool_outputs_count": len(self.tool_outputs),
                "errors_count": len(self.errors),
                "verification_results": self.verification_results,
                "final_result": self.final_result,
                "created_at": self.created_at,
                "updated_at": self.updated_at
            }
