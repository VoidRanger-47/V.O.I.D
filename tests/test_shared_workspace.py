# tests/test_shared_workspace.py
import unittest
import sys
import threading
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agents.workspace import SharedWorkspace


class TestSharedWorkspace(unittest.TestCase):
    def setUp(self):
        self.workspace = SharedWorkspace(
            task_id="test_task_123",
            goal="Analyze and optimize project architecture"
        )

    def test_initial_state(self):
        self.assertEqual(self.workspace.task_id, "test_task_123")
        self.assertEqual(self.workspace.goal, "Analyze and optimize project architecture")
        self.assertEqual(self.workspace.status, "IN_PROGRESS")
        self.assertEqual(len(self.workspace.observations), 0)

    def test_observations_and_findings(self):
        self.workspace.add_observation("system_agent", "RAM usage is 42%, VRAM free is 3.1GB")
        self.workspace.set_intermediate_result("bottleneck", "Disk I/O latency", agent_name="system_agent")
        
        self.assertEqual(len(self.workspace.observations), 1)
        self.assertEqual(self.workspace.get_intermediate_result("bottleneck"), "Disk I/O latency")

    def test_artifacts_and_decisions(self):
        self.workspace.add_artifact("patch_v1", "def optimize(): pass", artifact_type="code")
        self.workspace.add_decision("coding_agent", "Use lazy-loading for Whisper model", rationale="Save 450MB VRAM")
        
        self.assertIn("patch_v1", self.workspace.artifacts)
        self.assertEqual(len(self.workspace.decisions), 1)
        self.assertEqual(self.workspace.decisions[0]["decision"], "Use lazy-loading for Whisper model")

    def test_verification_and_completion(self):
        self.workspace.add_verification("verification_agent", "PASS", "All tests passed")
        self.workspace.set_final_result("Optimization completed successfully.", status="COMPLETED")
        
        self.assertEqual(self.workspace.status, "COMPLETED")
        self.assertEqual(self.workspace.final_result, "Optimization completed successfully.")
        self.assertEqual(len(self.workspace.verification_results), 1)

    def test_compressed_summary(self):
        self.workspace.add_observation("system_agent", "Telemetry nominal")
        self.workspace.set_intermediate_result("score", 98.5)
        self.workspace.add_artifact("report", "Report text")
        
        summary = self.workspace.get_summary()
        self.assertIn("Goal: Analyze and optimize project architecture", summary)
        self.assertIn("Telemetry nominal", summary)
        self.assertIn("report", summary)

    def test_thread_safety(self):
        def worker(idx):
            self.workspace.add_observation(f"agent_{idx}", f"Observation from {idx}")
            self.workspace.set_intermediate_result(f"key_{idx}", idx)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(self.workspace.observations), 10)
        self.assertEqual(len(self.workspace.intermediate_results), 10)


if __name__ == "__main__":
    unittest.main()
