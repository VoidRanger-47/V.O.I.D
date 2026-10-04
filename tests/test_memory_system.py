# tests/test_memory_system.py
import unittest
import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from void_memory.memory import VoidMemory, MemoryTier

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        # Use temporary SQLite DB for test isolation
        self.temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.temp_db.close()
        self.memory = VoidMemory(db_path=self.temp_db.name)

    def tearDown(self):
        if os.path.exists(self.temp_db.name):
            try:
                os.remove(self.temp_db.name)
            except Exception:
                pass

    def test_store_and_retrieve_semantic_memory(self):
        saved = self.memory.store_memory(
            text="The user's favorite programming language is Python.",
            tier=MemoryTier.SEMANTIC,
            importance=0.9
        )
        self.assertTrue(saved)

        results = self.memory.retrieve_memory("What language does the user like?", top_k=2)
        self.assertGreater(len(results), 0)
        self.assertIn("Python", results[0]["text"])

    def test_multi_tier_storage(self):
        # Preference tier
        self.memory.store_memory("User prefers dark mode and concise responses.", tier=MemoryTier.PREFERENCE, importance=0.8)
        # Project tier
        self.memory.store_memory("V.O.I.D. uses an offline PyTorch GPT-style transformer.", tier=MemoryTier.PROJECT, importance=0.9)

        prefs = self.memory.retrieve_memory("preferences", tier=MemoryTier.PREFERENCE)
        self.assertGreater(len(prefs), 0)
        self.assertIn("dark mode", prefs[0]["text"])

        proj = self.memory.retrieve_memory("architecture", tier=MemoryTier.PROJECT)
        self.assertGreater(len(proj), 0)
        self.assertIn("transformer", proj[0]["text"])

    def test_explicit_forget_memory(self):
        self.memory.store_memory("Temporary secret token XYZ-12345", tier=MemoryTier.SEMANTIC, importance=0.7)
        results_before = self.memory.retrieve_memory("secret token", top_k=1)
        self.assertEqual(len(results_before), 1)

        # Explicit forget
        deleted_count = self.memory.forget_memory("secret token")
        self.assertGreaterEqual(deleted_count, 1)

        results_after = self.memory.retrieve_memory("secret token", min_threshold=0.6)
        self.assertEqual(len(results_after), 0)

    def test_prompt_injection_structure(self):
        self.memory.store_memory("User lives in San Francisco.", tier=MemoryTier.SEMANTIC, importance=0.8)
        context_block = self.memory.inject_memory_into_prompt("Where do I live?")
        self.assertIn("SYSTEM IDENTITY:", context_block)
        self.assertIn("RELEVANT KNOWLEDGE:", context_block)

if __name__ == "__main__":
    unittest.main()
