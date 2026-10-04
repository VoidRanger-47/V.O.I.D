# core/context_manager.py
"""
Dynamic Context and Token Budget Manager for V.O.I.D.
Enforces strict token bounds (default <= 1500 tokens) to guarantee:
  1. Low VRAM footprint (under 4 GB)
  2. Minimal latency
  3. Signal-to-noise ratio maximization
Prevents raw full-document or agent dump flooding into neural prompts.
"""

from typing import Dict, Any, List, Optional
import time

from core.state_manager import state_manager
from void_memory.memory import void_memory
from core.agents.workspace import SharedWorkspace


class ContextManager:
    """
    Builds minimal, high-signal prompt contexts for V.O.I.D.
    Tracks token budget and compresses workspace artifacts.
    """
    _instance: Optional['ContextManager'] = None

    DEFAULT_MAX_CONTEXT_TOKENS = 1500

    def __init__(self, token_budget: int = DEFAULT_MAX_CONTEXT_TOKENS):
        self.token_budget = token_budget
        self.memory = void_memory
        self.state_mgr = state_manager

    @classmethod
    def get_instance(cls) -> 'ContextManager':
        if cls._instance is None:
            cls._instance = ContextManager()
        return cls._instance

    def estimate_tokens(self, text: str) -> int:
        """Standard ~4 characters per token estimate."""
        return max(1, len(text) // 4)

    def compress_agent_output(self, raw_output: Any, max_chars: int = 400) -> str:
        """
        Compresses verbose tool or agent output into an information-dense summary.
        """
        if raw_output is None:
            return ""
        s = str(raw_output).strip()
        if len(s) <= max_chars:
            return s
        return s[:max_chars] + f"\n... [Truncated: {len(s)} chars total]"

    def build_synthesis_context(
        self,
        goal: str,
        workspace: Optional[SharedWorkspace] = None,
        recent_history: Optional[List[Dict[str, str]]] = None,
        token_budget: Optional[int] = None
    ) -> str:
        """
        Synthesizes a minimal prompt context within token budget:
        [System State] + [Relevant Long-Term Memories] + [Compressed Workspace Findings]
        """
        budget = token_budget or self.token_budget
        sections = []

        # 1. System state telemetry (minimal)
        world = self.state_mgr.get_world_state()
        state_str = f"[SYSTEM: {world['current_time']} | Project: {world['current_project']} | VRAM: {world['vram_used_gb']}/{world['vram_total_gb']}GB | {world['network_status']}]"
        sections.append(state_str)

        # 2. Workspace findings & decisions (structured)
        if workspace:
            ws_summary = workspace.get_summary(max_tokens_estimate=500)
            if ws_summary:
                sections.append(ws_summary)

        # 3. Relevant memory retrieval
        try:
            memories = self.memory.retrieve_memory(goal, top_k=2, min_threshold=0.35)
            if memories:
                mem_lines = [f"• {m.get('content', '')[:150]}" for m in memories if m.get('content')]
                if mem_lines:
                    sections.append("Relevant Context:\n" + "\n".join(mem_lines))
        except Exception:
            pass

        # 4. Recent conversational turns (last 2 turns only to prevent drift)
        if recent_history:
            recent_turns = []
            for item in recent_history[-2:]:
                role = item.get("role", "user").capitalize()
                content = item.get("content", "")[:200]
                recent_turns.append(f"{role}: {content}")
            if recent_turns:
                sections.append("Recent Conversation:\n" + "\n".join(recent_turns))

        full_context = "\n\n".join(sections)

        # Truncate if exceeding token budget
        estimated_toks = self.estimate_tokens(full_context)
        if estimated_toks > budget:
            max_chars = budget * 4
            full_context = full_context[:max_chars] + "\n... [Context trimmed for 4GB VRAM budget]"

        return full_context


context_manager = ContextManager.get_instance()
