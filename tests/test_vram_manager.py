# tests/test_vram_manager.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.vram_manager import VRAMManager, VRAMThreshold, vram_manager


class TestVRAMManager(unittest.TestCase):
    def setUp(self):
        self.mgr = VRAMManager.get_instance()

    def test_singleton(self):
        other = VRAMManager.get_instance()
        self.assertIs(self.mgr, other)

    def test_telemetry_fields(self):
        stats = self.mgr.get_telemetry()
        self.assertIn("gpu_available", stats)
        self.assertIn("total_vram_mb", stats)
        self.assertIn("used_vram_mb", stats)
        self.assertIn("free_vram_mb", stats)
        self.assertIn("threshold_state", stats)
        self.assertIn("host_ram_used_mb", stats)
        self.assertIn("host_ram_total_mb", stats)
        self.assertIn("cpu_percent", stats)

    def test_threshold_evaluation(self):
        # 1000MB used of 4096MB is ~24% -> SAFE
        self.assertEqual(self.mgr._evaluate_threshold(1000.0, 4096.0), VRAMThreshold.SAFE)
        # 3000MB used of 4096MB is ~73% -> WARNING
        self.assertEqual(self.mgr._evaluate_threshold(3000.0, 4096.0), VRAMThreshold.WARNING)
        # 3600MB used of 4096MB is ~88% -> CRITICAL
        self.assertEqual(self.mgr._evaluate_threshold(3600.0, 4096.0), VRAMThreshold.CRITICAL)

    def test_model_registration_and_touch(self):
        fake_model = {"weights": "dummy_tensor"}
        self.mgr.register_model("test_dummy_model", fake_model, estimated_vram_mb=350.0)
        self.assertEqual(self.mgr._active_model_name, "test_dummy_model")
        
        retrieved = self.mgr.get_registered_model("test_dummy_model")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved, fake_model)

        unregistered = self.mgr.unregister_model("test_dummy_model")
        self.assertTrue(unregistered)
        self.assertIsNone(self.mgr.get_registered_model("test_dummy_model"))

    def test_vision_and_kv_allocations(self):
        self.mgr.allocate_vision(120.5)
        stats = self.mgr.get_telemetry()
        self.assertEqual(stats["vision_allocation_mb"], 120.5)

        self.mgr.allocate_kv_cache(64.0)
        stats = self.mgr.get_telemetry()
        self.assertEqual(stats["kv_cache_allocation_mb"], 64.0)

        self.mgr.release_vision()
        self.mgr.release_kv_cache()
        stats = self.mgr.get_telemetry()
        self.assertEqual(stats["vision_allocation_mb"], 0.0)
        self.assertEqual(stats["kv_cache_allocation_mb"], 0.0)

    def test_cleanup_vram_does_not_crash(self):
        # Safe to invoke on both CUDA and CPU
        self.mgr.cleanup_vram(force=True)
        res = self.mgr.emergency_cleanup()
        self.assertEqual(res["status"], "emergency_cleanup_executed")


if __name__ == "__main__":
    unittest.main()
