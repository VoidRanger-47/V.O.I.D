# void_memory/memory_retriever.py
"""
Hybrid Memory Retrieval Engine for V.O.I.D.
Combines Vector Semantic Similarity, SQLite FTS5 Keyword Search,
Knowledge Graph Expansion, and Multi-Factor Ranking.
"""

import time
import re
from typing import List, Dict, Any, Optional, Set, Tuple
import numpy as np

from void_memory.database.models import MemoryNode, MemoryStatus, MemoryTier
from void_memory.database.repository import MemoryRepository
from void_memory.embedding_provider import EmbeddingProvider, get_offline_embedding_provider, KeywordSearchProvider
from void_memory.memory_ranker import MemoryRanker


class MemoryRetriever:
    """
    Hybrid retriever that merges multiple search modalities offline.
    """

    def __init__(
        self,
        repo: MemoryRepository,
        embedding_provider: Optional[EmbeddingProvider] = None,
        ranker: Optional[MemoryRanker] = None
    ):
        self.repo = repo
        self.encoder = embedding_provider or get_offline_embedding_provider()
        self.ranker = ranker or MemoryRanker()

    def retrieve(
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
        Executes hybrid multi-stage retrieval:
        1. FTS5 Keyword Match
        2. Dense Vector Cosine Similarity
        3. Knowledge Graph Expansion
        4. Multi-Factor Ranking & Filtering
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        status = None if include_archived else MemoryStatus.ACTIVE.value
        all_candidates: Dict[str, MemoryNode] = {}
        keyword_scores: Dict[str, float] = {}
        semantic_scores: Dict[str, float] = {}

        # 1. Stage 1: SQLite FTS5 Keyword Search
        fts_matches = self.repo.search_fts(clean_query, limit=top_k * 3, status=status or MemoryStatus.ACTIVE.value)
        for node, kw_score in fts_matches:
            if tier and node.memory_type != tier:
                continue
            if category and node.category != category:
                continue
            if project_id and node.project_id != project_id:
                continue
            all_candidates[node.id] = node
            keyword_scores[node.id] = kw_score

        # 2. Stage 2: Dense Vector Semantic Search
        query_vec = None
        try:
            query_vec = self.encoder.encode(clean_query)
        except Exception as e:
            print(f"ℹ️ Vector encoding fallback: {e}")
            query_vec = None

        # Fetch candidate nodes from DB for vector comparison
        db_nodes = self.repo.list_memories(
            memory_type=tier,
            category=category,
            status=status,
            project_id=project_id,
            limit=150
        )

        for node in db_nodes:
            all_candidates[node.id] = node

            # Compute semantic cosine similarity
            sim = 0.0
            if query_vec is not None and node.embedding is not None:
                try:
                    db_vec = np.frombuffer(node.embedding, dtype=np.float32)
                    if len(db_vec) == len(query_vec):
                        denom = np.linalg.norm(query_vec) * np.linalg.norm(db_vec)
                        if denom > 1e-6:
                            sim = float(np.dot(query_vec, db_vec) / denom)
                except Exception:
                    sim = 0.0
            else:
                # Fallback keyword overlap
                sim = KeywordSearchProvider.compute_overlap(clean_query, node.content)

            semantic_scores[node.id] = max(0.0, float(sim))

            # Compute keyword score if not in FTS results
            if node.id not in keyword_scores:
                keyword_scores[node.id] = KeywordSearchProvider.compute_overlap(clean_query, node.content)

        # 3. Stage 3: Knowledge Graph Expansion for Top Candidates
        expanded_candidates: Dict[str, MemoryNode] = {}
        for mid, node in list(all_candidates.items())[:5]:
            related_edges = self.repo.get_related_memories(mid)
            for r_node, rel_type, weight in related_edges:
                if r_node.id not in all_candidates and r_node.status == MemoryStatus.ACTIVE.value:
                    if tier and r_node.memory_type != tier:
                        continue
                    if category and r_node.category != category:
                        continue
                    if project_id and r_node.project_id != project_id:
                        continue
                    expanded_candidates[r_node.id] = r_node
                    semantic_scores[r_node.id] = 0.45 * weight
                    keyword_scores[r_node.id] = 0.35 * weight

        all_candidates.update(expanded_candidates)

        # 4. Stage 4: Multi-Factor Composite Scoring
        results = []
        now = time.time()

        for mid, node in all_candidates.items():
            # Skip superseded memories unless explicitly asked
            if node.status == MemoryStatus.SUPERSEDED.value and not include_archived:
                continue

            sem_sim = semantic_scores.get(mid, 0.0)
            kw_sim = keyword_scores.get(mid, 0.0)

            score = self.ranker.score_memory(
                node=node,
                semantic_sim=sem_sim,
                keyword_sim=kw_sim,
                current_time=now
            )

            if score >= min_threshold or node.pinned or node.memory_type == MemoryTier.PREFERENCE.value:
                # Record access update asynchronously/quietly
                self.repo.update_access(node.id)

                entry = node.to_dict()
                entry["score"] = round(score, 4)
                entry["semantic_sim"] = round(sem_sim, 4)
                entry["keyword_sim"] = round(kw_sim, 4)
                entry["text"] = node.content  # Backward compatibility field
                results.append(entry)

        # Sort by composite score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]
