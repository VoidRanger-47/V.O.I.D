# void_memory/context_builder.py
"""
Context Builder for V.O.I.D. Prompt Pipeline.
Assembles, formats, and compresses multi-tier memory context within token budgets.
"""

from typing import List, Dict, Any, Optional

from void_memory.database.models import MemoryTier


class ContextBuilder:
    """
    Constructs well-structured prompt context blocks for the local LLM.
    """

    def __init__(self, default_token_budget: int = 100):
        self.default_token_budget = default_token_budget

    @staticmethod
    def _estimate_tokens(text: str) -> int:
        """Rough token estimate (1 token ≈ 4 characters)."""
        return max(1, len(text) // 4)

    def build_context_block(
        self,
        system_directives: List[str],
        user_preferences: List[str],
        project_context: Optional[str] = None,
        relevant_memories: Optional[List[str]] = None,
        working_conversation: Optional[List[str]] = None,
        token_budget: Optional[int] = None
    ) -> str:
        """
        Builds a structured contextual prompt block fitting within token budget.
        """
        budget = token_budget or self.default_token_budget
        sections = []

        # 1. System Directives (Highest priority)
        if system_directives:
            if budget <= 150:
                sys_text = "SYSTEM IDENTITY:\n• I am V.O.I.D., a local offline assistant."
            else:
                sys_text = "SYSTEM IDENTITY:\n" + "\n".join(f"• {d}" for d in system_directives)
            sections.append(("SYSTEM", sys_text))

        # 2. User Preferences (High priority)
        if user_preferences:
            prefs = user_preferences[:2] if budget <= 150 else user_preferences
            pref_text = "USER PREFERENCES:\n" + "\n".join(f"• {p}" for p in prefs)
            sections.append(("PREFERENCES", pref_text))

        # 3. Project Context
        if project_context and budget > 120:
            proj_line = project_context.split("\n")[0] if budget <= 200 else project_context.strip()
            proj_text = f"PROJECT CONTEXT:\n{proj_line}"
            sections.append(("PROJECT", proj_text))

        # 4. Relevant Factual Memories & Decisions
        if relevant_memories:
            mems = relevant_memories[:2] if budget <= 150 else relevant_memories
            mem_text = "RELEVANT KNOWLEDGE:\n" + "\n".join(f"• {m}" for m in mems)
            sections.append(("KNOWLEDGE", mem_text))

        # 5. Recent Conversation History
        if working_conversation and budget > 150:
            chat_text = "RECENT CONVERSATION:\n" + "\n".join(working_conversation[-3:])
            sections.append(("CHAT", chat_text))

        # Token budget compression
        final_parts = []
        accumulated_tokens = 0

        for title, section_text in sections:
            sect_tokens = self._estimate_tokens(section_text)
            if accumulated_tokens + sect_tokens <= budget:
                final_parts.append(section_text)
                accumulated_tokens += sect_tokens
            else:
                remaining_budget = budget - accumulated_tokens
                if remaining_budget > 15:
                    max_chars = remaining_budget * 4
                    trimmed = section_text[:max_chars].rsplit("\n", 1)[0]
                    if trimmed:
                        final_parts.append(trimmed)
                        accumulated_tokens += self._estimate_tokens(trimmed)
                break

        return "\n\n".join(final_parts) + "\n\n" if final_parts else ""
