# void_memory/memory.py
"""
Backward-Compatible Facade for the V.O.I.D. Advanced Memory Engine.
Seamlessly bridges legacy VoidMemory calls to the new modular MemoryManager.
"""

import os
from typing import List, Dict, Any, Tuple, Optional

from void_memory.database.models import MemoryTier, MemoryStatus, MemoryNode
from void_memory.memory_manager import MemoryManager


class VoidMemory:
    """
    Backward-compatible wrapper around MemoryManager.
    """
    _instance: Optional['VoidMemory'] = None

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        self.manager = MemoryManager(db_path=db_path)
        self.working_memory = self.manager.working_memory.conversation_history
        self.stm = self.working_memory
        self.identity = self.manager.identity

    @classmethod
    def get_instance(cls, db_path: str = "void_memory/void_memory.db") -> 'VoidMemory':
        if cls._instance is None or cls._instance.db_path != db_path:
            cls._instance = VoidMemory(db_path=db_path)
        return cls._instance

    def store_memory(
        self,
        text: str,
        tier: str = MemoryTier.SEMANTIC.value,
        category: str = "general",
        importance: float = 0.5
    ) -> bool:
        try:
            self.manager.remember(
                content=text,
                memory_type=tier,
                category=category,
                importance=importance,
                source="legacy_api"
            )
            return True
        except Exception as e:
            print(f"⚠️ store_memory error: {e}")
            return False

    def retrieve_memory(
        self,
        query: str,
        tier: Optional[str] = None,
        top_k: int = 4,
        min_threshold: float = 0.25
    ) -> List[Dict[str, Any]]:
        return self.manager.recall(
            query=query,
            tier=tier,
            top_k=top_k,
            min_threshold=min_threshold
        )

    def forget_memory(self, target_phrase: str) -> int:
        return self.manager.forget(target_phrase)

    def delete_by_id(self, memory_id: int | str) -> bool:
        return self.manager.repo.delete_memory(str(memory_id), hard_delete=False)

    def prune_weak_memories(self, threshold: float = 0.25, max_age_days: float = 30.0) -> int:
        return self.manager.lifecycle.auto_archive_stale_memories(
            max_age_days=max_age_days,
            min_importance_threshold=threshold
        )

    def inject_memory_into_prompt(self, user_input: str) -> str:
        return self.manager.get_context(user_input, token_budget=1200)

    def get_summary_context(self, user_input: str, top_k: int = 3) -> str:
        recs = self.retrieve_memory(user_input, top_k=top_k)
        if not recs:
            return ""
        return "\n".join([f"- {r.get('content', r.get('text', ''))}" for r in recs])

    def decide_if_importance(self, user_input: str) -> Tuple[bool, float]:
        """Evaluates whether an utterance is important enough to extract and store."""
        worth = self.manager.extractor.is_worth_remembering(user_input)
        score = self.manager.ranker.calculate_initial_importance(user_input)
        return (worth and score >= 0.65), score


# Singleton instance
void_memory = VoidMemory.get_instance()