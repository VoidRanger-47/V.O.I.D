# void_memory/memory_lifecycle.py
"""
Memory Lifecycle & Archiving Engine for V.O.I.D.
Manages transitions between ACTIVE, LOW_PRIORITY, ARCHIVED, SUPERSEDED, and DELETED states.
"""

import time
from typing import List, Dict, Any, Optional

from void_memory.database.models import MemoryStatus, MemoryTier, MemoryNode
from void_memory.database.repository import MemoryRepository


class MemoryLifecycleManager:
    """
    Handles memory aging, soft-archiving, unarchiving, and explicit forgetting.
    """

    def __init__(self, repo: MemoryRepository):
        self.repo = repo

    def archive_memory(self, memory_id: str) -> bool:
        """Move memory to ARCHIVED state (preserved, but omitted from normal retrieval)."""
        return self.repo.update_status(memory_id, MemoryStatus.ARCHIVED.value)

    def restore_memory(self, memory_id: str) -> bool:
        """Restore memory to ACTIVE state."""
        return self.repo.update_status(memory_id, MemoryStatus.ACTIVE.value)

    def mark_superseded(self, old_memory_id: str, new_memory_id: str) -> bool:
        """Mark an older memory as superseded and record relationship."""
        ok = self.repo.update_status(old_memory_id, MemoryStatus.SUPERSEDED.value)
        if ok:
            from void_memory.database.models import MemoryRelationship, RelationshipType
            self.repo.add_relationship(MemoryRelationship(
                source_id=new_memory_id,
                target_id=old_memory_id,
                relationship=RelationshipType.SUPERSEDES.value,
                created_at=time.time()
            ))
        return ok

    def forget_memory(self, target_phrase_or_id: str) -> int:
        """
        Explicitly purge or soft-delete memory matching a target phrase or ID.
        """
        clean = target_phrase_or_id.strip()
        # Check if ID
        existing = self.repo.get_memory_by_id(clean)
        if existing:
            self.repo.delete_memory(clean, hard_delete=False)
            return 1

        # Phrase matching
        return self.repo.forget_matching(clean)

    def auto_archive_stale_memories(
        self,
        max_age_days: float = 45.0,
        min_importance_threshold: float = 0.40
    ) -> int:
        """
        Archives unaccessed low-importance memories older than max_age_days.
        Pinned and PREFERENCE memories are never auto-archived.
        """
        cutoff_epoch = time.time() - (max_age_days * 86400)
        conn = self.repo._get_connection()
        c = conn.cursor()

        sql = '''
            SELECT id FROM memories
            WHERE status = ?
              AND pinned = 0
              AND memory_type != ?
              AND importance < ?
              AND last_accessed < ?
        '''
        c.execute(sql, (
            MemoryStatus.ACTIVE.value,
            MemoryTier.PREFERENCE.value,
            min_importance_threshold,
            cutoff_epoch
        ))
        rows = c.fetchall()
        count = 0
        for r in rows:
            mid = r["id"]
            self.archive_memory(mid)
            count += 1

        conn.close()
        return count
