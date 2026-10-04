# void_memory/memory_consolidator.py
"""
Memory Consolidation Engine for V.O.I.D.
Runs background / event-driven deduplication, contradiction detection,
memory merging, and automatic relationship generation.
"""

import re
import time
from typing import List, Dict, Any, Tuple, Optional
import numpy as np

from void_memory.database.models import MemoryNode, MemoryStatus, MemoryTier, MemoryRelationship, RelationshipType
from void_memory.database.repository import MemoryRepository
from void_memory.embedding_provider import EmbeddingProvider, get_offline_embedding_provider


class MemoryConsolidator:
    """
    Consolidates episodic and semantic memories to eliminate redundancies and resolve contradictions.
    """

    def __init__(self, repo: MemoryRepository, embedding_provider: Optional[EmbeddingProvider] = None):
        self.repo = repo
        self.encoder = embedding_provider or get_offline_embedding_provider()

    @staticmethod
    def _compute_jaccard(text1: str, text2: str) -> float:
        w1 = set(re.findall(r'\w+', text1.lower()))
        w2 = set(re.findall(r'\w+', text2.lower()))
        if not w1 or not w2:
            return 0.0
        return len(w1 & w2) / len(w1 | w2)

    def consolidate(self) -> Dict[str, Any]:
        """
        Executes a consolidation pass across active memories:
        1. Merges duplicate memories.
        2. Detects contradictions and supersedes obsolete memories.
        3. Archives stale low-importance items.
        """
        memories = self.repo.list_memories(status=MemoryStatus.ACTIVE.value, limit=500)
        duplicates_merged = 0
        contradictions_resolved = 0

        # 1. Deduplication Pass
        for i in range(len(memories)):
            m1 = memories[i]
            if m1.status != MemoryStatus.ACTIVE.value:
                continue

            for j in range(i + 1, len(memories)):
                m2 = memories[j]
                if m2.status != MemoryStatus.ACTIVE.value:
                    continue
                if m1.memory_type != m2.memory_type:
                    continue

                jaccard = self._compute_jaccard(m1.content, m2.content)
                if jaccard > 0.82 or m1.content.strip().lower() == m2.content.strip().lower():
                    # Merge m2 into m1
                    m1.importance = max(m1.importance, m2.importance)
                    m1.access_count += m2.access_count
                    m1.last_accessed = max(m1.last_accessed, m2.last_accessed)
                    self.repo.save_memory(m1)
                    self.repo.update_status(m2.id, MemoryStatus.ARCHIVED.value)
                    duplicates_merged += 1

        # 2. Contradiction Detection Pass (Targeted at preferences & technology stacks)
        # e.g., "User's preferred name is X" vs "User's preferred name is Y"
        pref_memories = [m for m in memories if m.memory_type == MemoryTier.PREFERENCE.value and m.status == MemoryStatus.ACTIVE.value]
        name_patterns = [r'preferred name is ([A-Za-z0-9_\-\s]+)', r'name is ([A-Za-z0-9_\-\s]+)']

        for pat in name_patterns:
            name_mems = []
            for m in pref_memories:
                match = re.search(pat, m.content, re.IGNORECASE)
                if match:
                    name_mems.append((m, match.group(1).strip()))

            if len(name_mems) > 1:
                # Keep the newest, mark older ones superseded
                name_mems.sort(key=lambda x: x[0].created_at, reverse=True)
                newest_mem, _ = name_mems[0]
                for old_mem, _ in name_mems[1:]:
                    if old_mem.id != newest_mem.id and old_mem.status == MemoryStatus.ACTIVE.value:
                        self.repo.update_status(old_mem.id, MemoryStatus.SUPERSEDED.value)
                        self.repo.add_relationship(MemoryRelationship(
                            source_id=newest_mem.id,
                            target_id=old_mem.id,
                            relationship=RelationshipType.SUPERSEDES.value,
                            created_at=time.time()
                        ))
                        contradictions_resolved += 1

        return {
            "status": "success",
            "duplicates_merged": duplicates_merged,
            "contradictions_resolved": contradictions_resolved,
            "timestamp": time.time()
        }
