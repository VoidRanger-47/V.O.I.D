import unittest
import tempfile
import os
from void_memory.database.models import MemoryTier, MemoryNode, MemoryStatus
from void_memory.database.repository import MemoryRepository
from core.memory_policy import MemoryWritePolicy, MemoryVerdict
from core.context_manager import ContextManager


class TestEightTierMemory(unittest.TestCase):
    def setUp(self):
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db_path = self.temp_db.name
        self.temp_db.close()
        self.repo = MemoryRepository(db_path=self.temp_db_path)
        self.policy = MemoryWritePolicy.get_instance()
        self.context_mgr = ContextManager(token_budget=1500)

    def tearDown(self):
        try:
            if os.path.exists(self.temp_db_path):
                os.remove(self.temp_db_path)
        except Exception:
            pass

    def test_all_eight_tiers_defined(self):
        expected_tiers = [
            "working",
            "episodic",
            "semantic",
            "preference",
            "project",
            "procedural",
            "visual",
            "mission"
        ]
        actual_tiers = [tier.value for tier in MemoryTier]
        for expected in expected_tiers:
            self.assertIn(expected, actual_tiers)

    def test_storage_and_retrieval_across_all_8_tiers(self):
        """Verify each tier can be created, saved to repository, and retrieved."""
        for tier in MemoryTier:
            node = MemoryNode(
                content=f"Content for tier {tier.value}",
                memory_type=tier.value,
                category=f"test_{tier.value}",
                importance=0.75,
                status=MemoryStatus.ACTIVE.value
            )
            saved = self.repo.save_memory(node)
            self.assertIsNotNone(saved)

            retrieved = self.repo.get_memory_by_id(node.id)
            self.assertIsNotNone(retrieved)
            self.assertEqual(retrieved.memory_type, tier.value)
            self.assertEqual(retrieved.content, f"Content for tier {tier.value}")

    def test_memory_write_policy_rejection(self):
        """Verify ephemeral chatter and transient commands are rejected."""
        ephemeral_inputs = [
            "hello void",
            "hey there",
            "what time is it?",
            "calculate 100 * 4",
            "system stats",
            "open notepad",
            "thanks"
        ]
        for text in ephemeral_inputs:
            verdict, score, reason = self.policy.evaluate(text)
            self.assertEqual(
                verdict,
                MemoryVerdict.REJECT,
                f"Failed to reject ephemeral input '{text}': {reason}"
            )
            self.assertLessEqual(score, 0.2)

    def test_memory_write_policy_preference_storage(self):
        """Verify user preferences are recognized for preference storage."""
        preference_inputs = [
            "I prefer dark mode in all applications",
            "Call me Commander",
            "I always write Python code using type annotations"
        ]
        for text in preference_inputs:
            verdict, score, reason = self.policy.evaluate(text)
            self.assertEqual(
                verdict,
                MemoryVerdict.STORE_PREFERENCE,
                f"Failed to detect preference in '{text}': {reason}"
            )
            self.assertGreaterEqual(score, 0.8)

    def test_memory_write_policy_semantic_and_project_facts(self):
        """Verify explicit facts and architectural decisions are recognized."""
        facts = [
            "Remember that our server runs on port 8000",
            "We decided to use SQLite for offline storage",
            "In this project the primary model is phi-3-mini"
        ]
        for text in facts:
            verdict, score, reason = self.policy.evaluate(text)
            self.assertEqual(
                verdict,
                MemoryVerdict.STORE_SEMANTIC,
                f"Failed to detect semantic fact in '{text}': {reason}"
            )
            self.assertGreaterEqual(score, 0.7)

    def test_memory_write_policy_multi_step_milestones(self):
        """Verify multi-step completed tasks are routed to episodic memory."""
        verdict, score, reason = self.policy.evaluate(
            user_input="Deployed the local pipeline and completed unit verification successfully",
            is_multi_step=True
        )
        self.assertEqual(verdict, MemoryVerdict.STORE_EPISODIC)
        self.assertGreaterEqual(score, 0.5)

    def test_context_manager_budgeting(self):
        """Verify context manager enforces strict token budget."""
        long_history = [
            {"role": "user", "content": "Word " * 300},
            {"role": "assistant", "content": "Response " * 300},
            {"role": "user", "content": "Another question " * 200},
        ]
        context_str = self.context_mgr.build_synthesis_context(
            goal="Test query",
            recent_history=long_history,
            token_budget=500
        )
        estimated = self.context_mgr.estimate_tokens(context_str)
        # Should stay well within budget limit
        self.assertLessEqual(estimated, 600)
        self.assertTrue(len(context_str) > 0)


if __name__ == "__main__":
    unittest.main()
