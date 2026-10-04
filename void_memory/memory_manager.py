# void_memory/memory_manager.py
"""
Central Memory Manager for V.O.I.D. Advanced Memory Engine.
Orchestrates multi-tier storage, hybrid retrieval, intelligent extraction,
knowledge graph linking, project memory, and consolidation strictly offline.
"""

import os
import json
import time
from typing import List, Dict, Any, Optional, Tuple

from void_memory.database.models import (
    MemoryNode,
    MemoryTier,
    MemoryStatus,
    RelationshipType,
    KnowledgeNode,
    ProjectMemoryRecord
)
from void_memory.database.repository import MemoryRepository
from void_memory.embedding_provider import EmbeddingProvider, get_offline_embedding_provider
from void_memory.memory_ranker import MemoryRanker
from void_memory.memory_extractor import MemoryExtractor
from void_memory.memory_retriever import MemoryRetriever
from void_memory.memory_consolidator import MemoryConsolidator
from void_memory.memory_lifecycle import MemoryLifecycleManager
from void_memory.knowledge_graph import KnowledgeGraph
from void_memory.project_memory import ProjectMemoryManager
from void_memory.working_memory import WorkingMemoryManager
from void_memory.context_builder import ContextBuilder
from void_memory.memory_events import MemoryEventHandler


class MemoryManager:
    """
    Unified Orchestrator for the V.O.I.D. Advanced Memory Engine.
    """
    _instance: Optional['MemoryManager'] = None

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path

        # 1. Database Repository
        self.repo = MemoryRepository(db_path=self.db_path)

        # 2. Strict Offline Embedding Provider
        self.embedding_provider = get_offline_embedding_provider()

        # 3. Subsystem Modules
        self.ranker = MemoryRanker()
        self.extractor = MemoryExtractor(ranker=self.ranker)
        self.retriever = MemoryRetriever(
            repo=self.repo,
            embedding_provider=self.embedding_provider,
            ranker=self.ranker
        )
        self.consolidator = MemoryConsolidator(
            repo=self.repo,
            embedding_provider=self.embedding_provider
        )
        self.lifecycle = MemoryLifecycleManager(repo=self.repo)
        self.knowledge_graph = KnowledgeGraph(repo=self.repo)
        self.project_memory = ProjectMemoryManager(repo=self.repo, project_id="VOID")
        self.working_memory = WorkingMemoryManager(conversation_limit=15)
        self.context_builder = ContextBuilder(default_token_budget=1200)

        # 4. Event Handler
        self.event_handler = MemoryEventHandler(self)

        # 5. Core System Directives
        self.identity = {
            'version': '0.3.0',
            'full_name': 'V.O.I.D.',
            'core_directives': [
                'I am V.O.I.D., a local offline AI operating layer and personal assistant.',
                'I preserve privacy, operate without internet dependencies, and use modular tools.',
                'I remember context across sessions and organize thoughts into structured memory tiers.',
                'I am concise, technically accurate, honest, and operate safely under local control.'
            ]
        }

    @classmethod
    def get_instance(cls, db_path: str = "void_memory/void_memory.db") -> 'MemoryManager':
        if cls._instance is None:
            cls._instance = MemoryManager(db_path=db_path)
        return cls._instance

    # =========================================================================
    # CORE MEMORY CRUD & PUBLIC API
    # =========================================================================

    def remember(
        self,
        content: str,
        memory_type: str = MemoryTier.SEMANTIC.value,
        category: str = "general",
        importance: Optional[float] = None,
        confidence: float = 0.90,
        tags: Optional[List[str]] = None,
        pinned: bool = False,
        project_id: Optional[str] = None,
        source: str = "conversation"
    ) -> MemoryNode:
        """
        Stores a memory node, calculates embeddings offline, and links knowledge entities.
        """
        clean_text = content.strip()
        if not clean_text:
            raise ValueError("Memory content cannot be empty.")

        # Compute initial importance if not specified
        calc_imp = importance
        if calc_imp is None:
            calc_imp = self.ranker.calculate_initial_importance(clean_text, category=category, source=source)

        # Compute vector embedding offline
        embedding_blob = None
        try:
            vec = self.embedding_provider.encode(clean_text)
            embedding_blob = vec.tobytes()
        except Exception as e:
            print(f"ℹ️ Offline embedding note: {e}")

        # Check existing by exact content to update
        existing = self.repo.get_memory_by_exact_content(clean_text)
        if existing:
            existing.importance = max(existing.importance, calc_imp)
            existing.access_count += 1
            existing.last_accessed = time.time()
            if pinned:
                existing.pinned = True
            if tags:
                existing.tags = list(set(existing.tags + tags))
            saved = self.repo.save_memory(existing)
            return saved

        node = MemoryNode(
            content=clean_text,
            memory_type=memory_type,
            category=category,
            importance=calc_imp,
            confidence=confidence,
            source=source,
            pinned=pinned,
            tags=tags or [],
            project_id=project_id,
            embedding=embedding_blob
        )

        saved = self.repo.save_memory(node)

        # Automatically extract and link known knowledge entities (e.g. Python, Flask, SQLite)
        try:
            self.knowledge_graph.extract_and_link_entities(saved.id, saved.content)
        except Exception:
            pass

        return saved

    def recall(
        self,
        query: str,
        tier: Optional[str] = None,
        category: Optional[str] = None,
        project_id: Optional[str] = None,
        top_k: int = 5,
        min_threshold: float = 0.25,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Retrieves relevant memories using hybrid multi-tier search.
        """
        return self.retriever.retrieve(
            query=query,
            tier=tier,
            category=category,
            project_id=project_id,
            top_k=top_k,
            min_threshold=min_threshold,
            include_archived=include_archived
        )

    def forget(self, target_phrase_or_id: str) -> int:
        """
        Explicitly removes or soft-deletes memories matching target phrase or ID.
        """
        return self.lifecycle.forget_memory(target_phrase_or_id)

    def archive(self, memory_id: str) -> bool:
        return self.lifecycle.archive_memory(memory_id)

    def restore(self, memory_id: str) -> bool:
        return self.lifecycle.restore_memory(memory_id)

    def update(
        self,
        memory_id: str,
        content: Optional[str] = None,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        importance: Optional[float] = None,
        tags: Optional[List[str]] = None,
        pinned: Optional[bool] = None
    ) -> Optional[MemoryNode]:
        node = self.repo.get_memory_by_id(memory_id)
        if not node:
            return None

        if content is not None:
            node.content = content.strip()
            # Re-encode
            try:
                vec = self.embedding_provider.encode(node.content)
                node.embedding = vec.tobytes()
            except Exception:
                pass
        if memory_type is not None:
            node.memory_type = memory_type
        if category is not None:
            node.category = category
        if importance is not None:
            node.importance = float(importance)
        if tags is not None:
            node.tags = tags
        if pinned is not None:
            node.pinned = pinned

        node.last_accessed = time.time()
        return self.repo.save_memory(node)

    def link(
        self,
        source_id: str,
        target_id: str,
        relationship: str = RelationshipType.RELATED_TO.value,
        weight: float = 1.0
    ) -> bool:
        return self.knowledge_graph.link_entities(source_id, target_id, relationship=relationship, weight=weight)

    # =========================================================================
    # CONTEXT INJECTION & CONVERSATION PIPELINE
    # =========================================================================

    def get_context(self, query: str, token_budget: int = 1200) -> str:
        """
        Constructs a complete contextual prompt block for the LLM.
        """
        # 1. Semantic and factual memories
        semantic_recs = self.recall(query, tier=MemoryTier.SEMANTIC.value, top_k=3, min_threshold=0.20)
        sem_lines = [r["content"] for r in semantic_recs]

        # 2. Procedural & Solutions
        proc_recs = self.recall(query, tier=MemoryTier.PROCEDURAL.value, top_k=2, min_threshold=0.20)
        for p in proc_recs:
            sem_lines.append(p["content"])

        # 3. User Preferences
        pref_recs = self.recall(query, tier=MemoryTier.PREFERENCE.value, top_k=3, min_threshold=0.10)
        pref_lines = [p["content"] for p in pref_recs]

        # 4. Project context
        proj_summary = self.project_memory.get_project_summary()

        # 5. Working chat history
        recent_chat = self.working_memory.get_recent_conversation(num_turns=6)

        return self.context_builder.build_context_block(
            system_directives=self.identity["core_directives"],
            user_preferences=pref_lines,
            project_context=proj_summary,
            relevant_memories=sem_lines,
            working_conversation=recent_chat,
            token_budget=token_budget
        )

    def extract_and_store_from_turn(
        self,
        user_message: str,
        assistant_response: str = "",
        project_id: str = "VOID"
    ) -> List[MemoryNode]:
        """
        Extracts candidate memories from a conversational turn and stores them.
        """
        extracted = self.extractor.extract_from_interaction(
            user_message=user_message,
            assistant_response=assistant_response,
            project_id=project_id
        )
        saved_nodes = []
        for node in extracted:
            try:
                saved = self.remember(
                    content=node.content,
                    memory_type=node.memory_type,
                    category=node.category,
                    importance=node.importance,
                    confidence=node.confidence,
                    tags=node.tags,
                    pinned=node.pinned,
                    project_id=node.project_id,
                    source=node.source
                )
                saved_nodes.append(saved)
            except Exception as e:
                print(f"⚠️ Failed to store extracted memory: {e}")

        return saved_nodes

    def consolidate(self) -> Dict[str, Any]:
        """Runs deduplication, contradiction resolution, and auto-archiving."""
        res = self.consolidator.consolidate()
        archived_count = self.lifecycle.auto_archive_stale_memories()
        res["stale_archived"] = archived_count
        return res

    def get_stats(self) -> Dict[str, Any]:
        stats = self.repo.get_stats()
        stats["embedding_provider"] = self.embedding_provider.get_provider_name()
        stats["offline_guarantee"] = True
        return stats

    def export_data(self) -> Dict[str, Any]:
        memories = self.repo.list_memories(limit=1000)
        knodes = self.repo.list_knowledge_nodes()
        proj = self.project_memory.get_project_record()
        return {
            "version": "0.3.0",
            "exported_at": time.time(),
            "memories": [m.to_dict() for m in memories],
            "knowledge_nodes": [k.to_dict() for k in knodes],
            "project_record": proj.to_dict()
        }

    def import_data(self, data: Dict[str, Any]) -> int:
        count = 0
        for m in data.get("memories", []):
            try:
                self.remember(
                    content=m["content"],
                    memory_type=m.get("memory_type", MemoryTier.SEMANTIC.value),
                    category=m.get("category", "imported"),
                    importance=m.get("importance", 0.5),
                    tags=m.get("tags", []),
                    pinned=m.get("pinned", False),
                    project_id=m.get("project_id")
                )
                count += 1
            except Exception:
                pass
        return count
