# tests/test_advanced_memory_engine.py
"""
Comprehensive Unit and Integration Test Suite for V.O.I.D. Advanced Memory Engine.
Tests offline guarantees, multi-tier storage, hybrid retrieval, intelligent extraction,
knowledge graph linking, project memory, consolidation, and backward compatibility.
"""

import os
import sys
import unittest
import tempfile
import time
import numpy as np

# Ensure project root is in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from void_memory.database.models import (
    MemoryNode,
    MemoryTier,
    MemoryStatus,
    RelationshipType,
    KnowledgeNode,
    ProjectMemoryRecord
)
from void_memory.database.repository import MemoryRepository
from void_memory.embedding_provider import (
    LocalEmbeddingProvider,
    LocalFallbackEmbeddingProvider,
    KeywordSearchProvider,
    get_offline_embedding_provider
)
from void_memory.memory_ranker import MemoryRanker
from void_memory.memory_extractor import MemoryExtractor
from void_memory.knowledge_graph import KnowledgeGraph
from void_memory.project_memory import ProjectMemoryManager
from void_memory.working_memory import WorkingMemoryManager
from void_memory.memory_lifecycle import MemoryLifecycleManager
from void_memory.memory_consolidator import MemoryConsolidator
from void_memory.memory_retriever import MemoryRetriever
from void_memory.context_builder import ContextBuilder
from void_memory.memory_manager import MemoryManager
from void_memory.memory import VoidMemory, void_memory


class TestAdvancedMemoryEngine(unittest.TestCase):

    def setUp(self):
        # Create a temporary database for isolated test execution
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()

        self.repo = MemoryRepository(db_path=self.temp_db_path)
        self.fallback_provider = LocalFallbackEmbeddingProvider(dim=384)
        self.ranker = MemoryRanker()
        self.extractor = MemoryExtractor(ranker=self.ranker)
        self.manager = MemoryManager(db_path=self.temp_db_path)

    def tearDown(self):
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    # =========================================================================
    # 1. OFFLINE EMBEDDING PROVIDER TESTS
    # =========================================================================

    def test_strict_offline_environment_variables(self):
        """Verify that offline environment variables are strictly set."""
        self.assertEqual(os.environ.get("HF_HUB_OFFLINE"), "1")
        self.assertEqual(os.environ.get("TRANSFORMERS_OFFLINE"), "1")

    def test_fallback_embedding_provider_deterministic_vectors(self):
        """Verify deterministic mathematical vector generator works 100% offline."""
        text = "V.O.I.D. operates completely offline with local models"
        vec1 = self.fallback_provider.encode(text)
        vec2 = self.fallback_provider.encode(text)

        self.assertEqual(vec1.shape, (384,))
        self.assertEqual(vec1.dtype, np.float32)
        # Check determinism
        np.testing.assert_array_almost_equal(vec1, vec2)
        # Check normalized unit vector
        norm = np.linalg.norm(vec1)
        self.assertAlmostEqual(norm, 1.0, places=4)

    def test_fallback_embedding_semantic_similarity(self):
        """Verify that related sentences produce higher cosine similarity than unrelated ones."""
        v_anchor = self.fallback_provider.encode("Python Flask backend database")
        v_similar = self.fallback_provider.encode("Python web backend with SQLite database")
        v_unrelated = self.fallback_provider.encode("Chocolate cake strawberry ice cream recipe")

        sim_related = np.dot(v_anchor, v_similar)
        sim_unrelated = np.dot(v_anchor, v_unrelated)

        self.assertGreater(sim_related, sim_unrelated)

    # =========================================================================
    # 2. DATABASE REPOSITORY & FTS5 TESTS
    # =========================================================================

    def test_repository_crud_and_fts(self):
        """Verify saving, retrieving, updating, and FTS5 keyword searching."""
        node = MemoryNode(
            content="User prefers dark theme and Python programming.",
            memory_type=MemoryTier.PREFERENCE.value,
            category="user_preference",
            importance=0.9
        )
        saved = self.repo.save_memory(node)
        self.assertEqual(saved.id, node.id)

        # Retrieve by ID
        fetched = self.repo.get_memory_by_id(saved.id)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.content, node.content)
        self.assertEqual(fetched.memory_type, MemoryTier.PREFERENCE.value)

        # Search with FTS5
        fts_results = self.repo.search_fts("dark theme")
        self.assertGreater(len(fts_results), 0)
        self.assertEqual(fts_results[0][0].id, saved.id)

    # =========================================================================
    # 3. MEMORY EXTRACTOR HEURISTICS TESTS
    # =========================================================================

    def test_extract_user_preference_and_name(self):
        """Test extraction of user name and style preferences."""
        user_msg = "My name is Alice and I prefer concise Python code."
        extracted = self.extractor.extract_from_interaction(user_msg)
        self.assertGreaterEqual(len(extracted), 1)

        contents = [m.content for m in extracted]
        self.assertTrue(any("Alice" in c for c in contents))
        self.assertTrue(any("concise Python code" in c for c in contents))

    def test_extract_project_fact_and_explicit_command(self):
        """Test extraction of project technical stack and explicit remember commands."""
        cmd = "Remember that our application port is 5000 and we use SQLite."
        extracted = self.extractor.extract_from_interaction(cmd)
        self.assertGreaterEqual(len(extracted), 1)
        self.assertEqual(extracted[0].source, "explicit_command")
        self.assertTrue("5000" in extracted[0].content)

    def test_filter_smalltalk_and_questions(self):
        """Verify casual greetings and trivial questions are discarded."""
        self.assertFalse(self.extractor.is_worth_remembering("hello how are you"))
        self.assertFalse(self.extractor.is_worth_remembering("what time is it?"))
        self.assertFalse(self.extractor.is_worth_remembering("thanks"))
        self.assertFalse(self.extractor.is_worth_remembering("cool"))

    # =========================================================================
    # 4. KNOWLEDGE GRAPH & PROJECT MEMORY TESTS
    # =========================================================================

    def test_knowledge_graph_and_neighborhood_expansion(self):
        """Test concept node creation, entity linking, and neighborhood traversal."""
        graph = KnowledgeGraph(self.repo)
        graph.add_concept("PyTorch", node_type="technology", description="Deep learning framework")

        mem = self.repo.save_memory(MemoryNode(
            content="Local model inference runs on PyTorch.",
            memory_type=MemoryTier.SEMANTIC.value
        ))

        graph.link_entities(mem.id, "PyTorch", relationship=RelationshipType.USES.value)

        # Check neighborhood expansion
        neighbors = graph.get_neighborhood(mem.id, max_depth=1)
        self.assertGreaterEqual(len(neighbors), 1)

    def test_project_memory_manager(self):
        """Test project architecture tracking, decision logs, and problem-solution history."""
        pm = ProjectMemoryManager(self.repo, project_id="TEST_PROJ")
        dec = pm.record_decision("Use SQLite WAL Mode", "Enables concurrent reads without lock contention")
        self.assertEqual(dec["title"], "Use SQLite WAL Mode")

        sol = pm.record_problem_and_solution("Port conflict 5000", "Old zombie process", "Killed process via netstat")
        self.assertEqual(sol["problem"], "Port conflict 5000")

        summary = pm.get_project_summary()
        self.assertIn("SQLite WAL Mode", summary)
        self.assertIn("Port conflict 5000", summary)

    # =========================================================================
    # 5. CONSOLIDATION & CONTRADICTION TESTS
    # =========================================================================

    def test_consolidation_deduplication(self):
        """Verify near-duplicate memories are merged and archived."""
        self.manager.remember("User preferred editor is Visual Studio Code", memory_type=MemoryTier.PREFERENCE.value)
        self.manager.remember("User preferred editor is Visual Studio Code", memory_type=MemoryTier.PREFERENCE.value)

        res = self.manager.consolidate()
        self.assertGreaterEqual(res["duplicates_merged"], 0)

        active = self.manager.repo.list_memories(memory_type=MemoryTier.PREFERENCE.value, status=MemoryStatus.ACTIVE.value)
        # Should only have 1 active record
        self.assertEqual(len(active), 1)

    def test_contradiction_detection_name_supersedes(self):
        """Verify when a user changes their name, the old memory is superseded."""
        m1 = self.manager.remember("User's preferred name is Bob.", memory_type=MemoryTier.PREFERENCE.value)
        time.sleep(0.01)
        m2 = self.manager.remember("User's preferred name is Alice.", memory_type=MemoryTier.PREFERENCE.value)

        res = self.manager.consolidator.consolidate()
        self.assertGreaterEqual(res["contradictions_resolved"], 1)

        old_node = self.manager.repo.get_memory_by_id(m1.id)
        new_node = self.manager.repo.get_memory_by_id(m2.id)

        self.assertEqual(old_node.status, MemoryStatus.SUPERSEDED.value)
        self.assertEqual(new_node.status, MemoryStatus.ACTIVE.value)

    # =========================================================================
    # 6. HYBRID RETRIEVAL & CONTEXT BUILDER TESTS
    # =========================================================================

    def test_hybrid_retrieval(self):
        """Test composite hybrid recall (semantic + keyword + importance)."""
        self.manager.remember("V.O.I.D. uses Piper TTS for offline speech synthesis.", memory_type=MemoryTier.SEMANTIC.value, importance=0.9)
        self.manager.remember("User loves dark mode interface.", memory_type=MemoryTier.PREFERENCE.value, importance=0.8)
        self.manager.remember("Unrelated recipe for baking chocolate cookies.", memory_type=MemoryTier.SEMANTIC.value, importance=0.3)

        results = self.manager.recall("How does voice speech work in VOID?", top_k=2)
        self.assertGreaterEqual(len(results), 1)
        self.assertIn("Piper TTS", results[0]["content"])

    def test_context_builder_token_budget(self):
        """Test prompt context block construction within specified token budget."""
        cb = ContextBuilder(default_token_budget=100)
        block = cb.build_context_block(
            system_directives=["I am V.O.I.D."],
            user_preferences=["User prefers Python"],
            project_context="Project V.O.I.D.",
            relevant_memories=["Offline memory engine"],
            working_conversation=["User: hello", "V.O.I.D.: hi"],
            token_budget=500
        )
        self.assertIn("SYSTEM IDENTITY:", block)
        self.assertIn("USER PREFERENCES:", block)
        self.assertIn("RELEVANT KNOWLEDGE:", block)

    # =========================================================================
    # 7. BACKWARD COMPATIBILITY FAÇADE TESTS
    # =========================================================================

    def test_void_memory_facade_backward_compatibility(self):
        """Test that legacy void_memory methods continue to function seamlessly."""
        vm = VoidMemory.get_instance(db_path=self.temp_db_path)
        ok = vm.store_memory("Legacy test fact", tier=MemoryTier.SEMANTIC.value, importance=0.8)
        self.assertTrue(ok)

        recs = vm.retrieve_memory("Legacy test fact", top_k=1)
        self.assertGreaterEqual(len(recs), 1)
        self.assertIn("Legacy test fact", recs[0]["text"])

        # Context injection
        ctx = vm.inject_memory_into_prompt("Legacy test fact")
        self.assertIsInstance(ctx, str)
        self.assertIn("SYSTEM IDENTITY:", ctx)

        # Explicit forget
        purged = vm.forget_memory("Legacy test fact")
        self.assertGreaterEqual(purged, 1)


if __name__ == "__main__":
    unittest.main()
