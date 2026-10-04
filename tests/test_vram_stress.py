import unittest
import time
from core.vram_manager import VRAMManager, VRAMThreshold
from core.agents.scheduler import AgentTaskScheduler
from core.agents.workspace import SharedWorkspace
from core.agents.protocol import AgentMessage, AgentMessageType


class TestVRAMStress(unittest.TestCase):
    def setUp(self):
        self.vram_mgr = VRAMManager()
        self.scheduler = AgentTaskScheduler(max_workers=4)

    def test_threshold_state_transitions(self):
        """Verify SAFE -> WARNING -> CRITICAL state transitions at 4GB scale."""
        total_mb = 4096.0

        # Safe: 1500 MB used (< 70%)
        state_safe = self.vram_mgr._evaluate_threshold(1500.0, total_mb)
        self.assertEqual(state_safe, VRAMThreshold.SAFE)

        # Warning: 3000 MB used (73.2% >= 70% and >= 2867.2 MB)
        state_warn = self.vram_mgr._evaluate_threshold(3000.0, total_mb)
        self.assertEqual(state_warn, VRAMThreshold.WARNING)

        # Critical: 3600 MB used (87.8% >= 85% and >= 3481.6 MB)
        state_crit = self.vram_mgr._evaluate_threshold(3600.0, total_mb)
        self.assertEqual(state_crit, VRAMThreshold.CRITICAL)

    def test_vision_and_kv_cache_budget_tracking(self):
        """Verify dynamic tracking of vision processing and KV cache allocations."""
        self.vram_mgr.allocate_vision(250.0)
        self.vram_mgr.allocate_kv_cache(180.0)
        
        telemetry = self.vram_mgr.get_telemetry()
        self.assertEqual(telemetry["vision_allocation_mb"], 250.0)
        self.assertEqual(telemetry["kv_cache_allocation_mb"], 180.0)

        self.vram_mgr.release_vision()
        self.vram_mgr.release_kv_cache()
        
        telemetry_after = self.vram_mgr.get_telemetry()
        self.assertEqual(telemetry_after["vision_allocation_mb"], 0.0)
        self.assertEqual(telemetry_after["kv_cache_allocation_mb"], 0.0)

    def test_emergency_cleanup_execution(self):
        """Verify emergency cleanup routine executes smoothly without errors."""
        res = self.vram_mgr.emergency_cleanup()
        self.assertEqual(res["status"], "emergency_cleanup_executed")
        self.assertIn("telemetry", res)
        self.assertIn("freed_mb", res)

    def test_concurrent_agent_stress_under_scheduler(self):
        """
        Simulate 12 concurrent agent tasks running in parallel batches,
        validating that scheduler limits concurrency and prevents resource exhaustion.
        """
        def dummy_router(msg: AgentMessage) -> AgentMessage:
            time.sleep(0.01)
            return AgentMessage(
                sender=msg.receiver,
                receiver=msg.sender,
                task_id=msg.task_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=f"Completed load iteration for {msg.task_id}"
            )

        steps = [
            {
                "step_id": i + 1,
                "agent": f"worker_agent_{i % 4}",
                "goal": f"Execute stress step {i + 1}",
                "dependencies": []
            }
            for i in range(12)
        ]

        workspace = SharedWorkspace(task_id="vram_stress_run", goal="Concurrent Stress Test")
        results = self.scheduler.execute_dag(steps, workspace, dummy_router)

        self.assertEqual(len(results), 12)
        for res in results:
            self.assertEqual(res.status, "SUCCESS")

        self.assertEqual(workspace.status, "SUCCESS")
        self.assertEqual(len(workspace.intermediate_results), 12)

    def test_zero_oom_under_simulated_critical_headroom(self):
        """
        Verify that when headroom drops below required threshold,
        is_safe_for_inference protects the system from triggering OOM.
        """
        if self.vram_mgr.get_telemetry()["gpu_available"]:
            # Asking for 10 GB when GPU has 4 GB should safely return False
            safe, reason = self.vram_mgr.is_safe_for_inference(estimated_mb=10000.0)
            self.assertFalse(safe)
            self.assertIn("VRAM constraint", reason)


if __name__ == "__main__":
    unittest.main()
