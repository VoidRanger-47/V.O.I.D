# core/memory_policy.py
"""
Memory Write Policy Engine for V.O.I.D.
Enforces intelligent filtering before saving memories to local SQLite.
Prevents database pollution with ephemeral chatter, transient queries, or duplicate facts.
"""

import re
from enum import Enum
from typing import Tuple, Dict, Any, Optional


class MemoryVerdict(str, Enum):
    REJECT = "REJECT"        # Ephemeral chatter, transient greeting, temporary math
    STORE_EPISODIC = "STORE_EPISODIC"  # Significant milestone or multi-step task completion
    STORE_SEMANTIC = "STORE_SEMANTIC"  # Stable factual knowledge or project decision
    STORE_PREFERENCE = "STORE_PREFERENCE"  # User styling, identity, preference


class MemoryWritePolicy:
    """
    Evaluates whether a piece of information is stable, useful, and worth long-term storage.
    """
    _instance: Optional['MemoryWritePolicy'] = None

    # Transient patterns that should NEVER pollute long-term memory
    TRANSIENT_PATTERNS = [
        r"^(hi|hello|hey|yo|greetings|good morning|good evening)\b",
        r"^(what time|current time|what is the time|today's date)",
        r"^(calculate|\d+\s*[\+\-\*\/]\s*\d+)",
        r"^(system stats|cpu usage|ram usage|vram usage)",
        r"^(open |launch |start notepad|start vs code)",
        r"^(thanks|thank you|ok|okay|got it|cool|nice)\b"
    ]

    # Patterns indicating strong personal preference
    PREFERENCE_PATTERNS = [
        r"\b(i prefer|i like|i always|my preferred|call me|my name is)\b",
        r"\b(never use|always use|do not use|i hate|i want you to always)\b"
    ]

    # Patterns indicating project decisions or architecture
    PROJECT_PATTERNS = [
        r"\b(we decided|the architecture is|we use|in this project|configured to use)\b",
        r"\b(fix for bug|root cause was|solution is|database schema)\b"
    ]

    @classmethod
    def get_instance(cls) -> 'MemoryWritePolicy':
        if cls._instance is None:
            cls._instance = MemoryWritePolicy()
        return cls._instance

    def evaluate(self, user_input: str, agent_output: Optional[str] = None, is_multi_step: bool = False) -> Tuple[MemoryVerdict, float, str]:
        """
        Evaluates input/output pair against storage criteria.
        Returns: (verdict, importance_score, rationale)
        """
        text = (user_input or "").strip()
        low = text.lower()

        if len(text) < 4:
            return MemoryVerdict.REJECT, 0.0, "Input too short to contain persistent knowledge."

        # Check explicit transient patterns
        for pat in self.TRANSIENT_PATTERNS:
            if re.search(pat, low):
                return MemoryVerdict.REJECT, 0.0, f"Matched transient conversational pattern '{pat}'."

        # Check explicit memory instruction
        if "remember" in low and not any(k in low for k in ["do you remember", "can you remember"]):
            return MemoryVerdict.STORE_SEMANTIC, 0.85, "Explicit user request to remember fact."

        # Check user preference
        for pat in self.PREFERENCE_PATTERNS:
            if re.search(pat, low):
                return MemoryVerdict.STORE_PREFERENCE, 0.90, f"User preference detected via '{pat}'."

        # Check project architecture or decision
        for pat in self.PROJECT_PATTERNS:
            if re.search(pat, low):
                return MemoryVerdict.STORE_SEMANTIC, 0.80, f"Project decision or architectural fact detected."

        # Multi-step tasks or complex milestones
        if is_multi_step and len(text) > 20:
            return MemoryVerdict.STORE_EPISODIC, 0.60, "Completed multi-step mission milestone."

        return MemoryVerdict.REJECT, 0.1, "Routine conversational utterance (ephemeral)."


memory_write_policy = MemoryWritePolicy.get_instance()
