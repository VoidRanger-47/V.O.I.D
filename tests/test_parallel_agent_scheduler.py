# tests/test_parallel_agent_scheduler.py
import unittest
import sys
import time
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.agents.scheduler import AgentTaskScheduler
from core.agents.workspace import SharedWorkspace
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority


class TestParallelAgentScheduler(unittest.TestCase):
    def setUp(self):
        self.scheduler = AgentTaskScheduler.get_instance()

    def test_independent_tasks_run_in_parallel(self):
        workspace = SharedWorkspace(task_id="par_test_1", goal="Test parallel tasks")

        # Mock routing function with 0.1s simulated work
        executed_order = []
        def mock_router(msg: AgentMessage) -> AgentMessage:
            time.sleep(0.1)
            executed_order.append(msg.receiver)
            return AgentMessage(
                sender=msg.receiver,
                receiver=msg.sender,
                task_id=msg.task_id,
                status="SUCCESS",
                result=f"Result from {msg.receiver}"
            )

        # 3 independent steps with NO dependencies
        steps = [
            {"step_id": 1, "agent": "system_agent", "goal": "Check system", "dependencies": []},
            {"step_id": 2, "agent": "memory_agent", "goal": "Fetch memory", "dependencies": []},
            {"step_id": 3, "agent": "knowledge_agent", "goal": "Read docs", "dependencies": []}
        ]

        t0 = time.time()
        results = self.scheduler.execute_dag(steps, workspace, mock_router)
        duration = time.time() - t0

        self.assertEqual(len(results), 3)
        self.assertTrue(all(r.status == "SUCCESS" for r in results))
        # If run sequentially, 3 * 0.1s = 0.3s+. In parallel, should be ~0.1s - 0.25s
        self.assertLess(duration, 0.28)
        self.assertEqual(workspace.status, "SUCCESS")

    def test_dependency_chain_waits_for_prerequisites(self):
        workspace = SharedWorkspace(task_id="dag_test_2", goal="Test DAG dependencies")

        step_finish_times = {}
        def mock_router(msg: AgentMessage) -> AgentMessage:
            time.sleep(0.05)
            step_finish_times[msg.task_id] = time.time()
            return AgentMessage(
                sender=msg.receiver,
                receiver=msg.sender,
                task_id=msg.task_id,
                status="SUCCESS",
                result=f"Done {msg.receiver}"
            )

        # Step 3 depends on Step 1 and Step 2
        steps = [
            {"step_id": 1, "agent": "system_agent", "goal": "Step 1", "dependencies": []},
            {"step_id": 2, "agent": "memory_agent", "goal": "Step 2", "dependencies": []},
            {"step_id": 3, "agent": "coding_agent", "goal": "Step 3 (Dependent)", "dependencies": [1, 2]}
        ]

        results = self.scheduler.execute_dag(steps, workspace, mock_router)
        self.assertEqual(len(results), 3)

        # Confirm step 3 finished after steps 1 and 2
        t1 = step_finish_times[f"{workspace.task_id}_s1"]
        t2 = step_finish_times[f"{workspace.task_id}_s2"]
        t3 = step_finish_times[f"{workspace.task_id}_s3"]

        self.assertGreater(t3, t1)
        self.assertGreater(t3, t2)

    def test_failed_prerequisite_skips_downstream_task(self):
        workspace = SharedWorkspace(task_id="fail_dep_test", goal="Test failure propagation")

        def mock_router(msg: AgentMessage) -> AgentMessage:
            if msg.receiver == "system_agent":
                return AgentMessage(
                    sender=msg.receiver,
                    receiver=msg.sender,
                    task_id=msg.task_id,
                    status="FAILED",
                    error="Hardware fault",
                    result="Diagnostic failure"
                )
            return AgentMessage(
                sender=msg.receiver,
                receiver=msg.sender,
                task_id=msg.task_id,
                status="SUCCESS",
                result="Success"
            )

        # Step 2 depends on Step 1 which will fail
        steps = [
            {"step_id": 1, "agent": "system_agent", "goal": "Failing step", "dependencies": []},
            {"step_id": 2, "agent": "coding_agent", "goal": "Dependent step", "dependencies": [1]}
        ]

        results = self.scheduler.execute_dag(steps, workspace, mock_router)
        self.assertEqual(len(results), 2)
        # Step 2 must be marked FAILED due to prerequisite failure
        step_2_res = next(r for r in results if r.receiver == "coding_agent")
        self.assertEqual(step_2_res.status, "FAILED")


if __name__ == "__main__":
    unittest.main()
