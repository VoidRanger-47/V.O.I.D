import unittest
import threading
import time
from core.task_lifecycle import TaskLifecycleController, TaskState
from core.event_bus import event_bus, SystemEvent


class TestCancellationAndStop(unittest.TestCase):
    def setUp(self):
        self.lifecycle = TaskLifecycleController()
        self.test_task_id = "test_task_123"

    def test_register_and_initial_state(self):
        cancel_event = self.lifecycle.register_task(self.test_task_id)
        self.assertFalse(cancel_event.is_set())
        self.assertFalse(self.lifecycle.should_stop(self.test_task_id))
        self.assertEqual(self.lifecycle.get_state(self.test_task_id), TaskState.RUNNING)

    def test_stop_task(self):
        self.lifecycle.register_task(self.test_task_id)
        stopped = self.lifecycle.stop_task(self.test_task_id, reason="Test Stop")
        self.assertTrue(stopped)
        self.assertTrue(self.lifecycle.should_stop(self.test_task_id))
        self.assertEqual(self.lifecycle.get_state(self.test_task_id), TaskState.STOPPED)

    def test_pause_and_resume(self):
        self.lifecycle.register_task(self.test_task_id)
        
        # Test Pause
        paused = self.lifecycle.pause_task(self.test_task_id)
        self.assertTrue(paused)
        self.assertEqual(self.lifecycle.get_state(self.test_task_id), TaskState.PAUSED)
        
        # Wait if paused should time out
        res = self.lifecycle.wait_if_paused(self.test_task_id, timeout=0.05)
        self.assertFalse(res)

        # Test Resume
        resumed = self.lifecycle.resume_task(self.test_task_id)
        self.assertTrue(resumed)
        self.assertEqual(self.lifecycle.get_state(self.test_task_id), TaskState.RUNNING)
        
        # Wait if paused should now return immediately
        res = self.lifecycle.wait_if_paused(self.test_task_id, timeout=0.05)
        self.assertTrue(res)

    def test_cancel_task(self):
        self.lifecycle.register_task(self.test_task_id)
        cancelled = self.lifecycle.cancel_task(self.test_task_id)
        self.assertTrue(cancelled)
        self.assertTrue(self.lifecycle.should_stop(self.test_task_id))
        self.assertEqual(self.lifecycle.get_state(self.test_task_id), TaskState.STOPPED)

    def test_task_completion(self):
        self.lifecycle.register_task(self.test_task_id)
        self.lifecycle.complete_task(self.test_task_id)
        self.assertEqual(self.lifecycle.get_state(self.test_task_id), TaskState.COMPLETED)

    def test_responsive_loop_interruption(self):
        """Simulate a long running inference/agent loop and interrupt it midway."""
        self.lifecycle.register_task("worker_task")
        iterations_completed = 0
        started_event = threading.Event()

        def worker():
            nonlocal iterations_completed
            started_event.set()
            for _ in range(100):
                if self.lifecycle.should_stop("worker_task"):
                    break
                self.lifecycle.wait_if_paused("worker_task", timeout=0.01)
                iterations_completed += 1
                time.sleep(0.01)

        t = threading.Thread(target=worker, daemon=True)
        t.start()
        started_event.wait(timeout=1.0)
        time.sleep(0.05)

        # Stop the worker task
        self.lifecycle.stop_task("worker_task")
        t.join(timeout=1.0)

        self.assertFalse(t.is_alive())
        self.assertLess(iterations_completed, 100)


if __name__ == "__main__":
    unittest.main()
