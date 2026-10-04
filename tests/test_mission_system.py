# tests/test_mission_system.py
import unittest
import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.mission import MissionManager

class TestMissionSystem(unittest.TestCase):
    def setUp(self):
        self.test_db = "void_memory/test_missions.db"
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
        self.missions = MissionManager(db_path=self.test_db)

    def tearDown(self):
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def test_create_and_get_mission(self):
        steps = ["Audit workspace", "Implement multi-agent architecture", "Run test suite"]
        mid = self.missions.create_mission(
            title="Transform V.O.I.D. to Multi-Agent AI",
            goal="Refactor into genuine local multi-agent system",
            steps=steps,
            assigned_agents=["executive", "planning_agent", "coding_agent", "verification_agent"]
        )
        self.assertGreater(mid, 0)

        mission = self.missions.get_mission(mid)
        self.assertIsNotNone(mission)
        self.assertEqual(mission["title"], "Transform V.O.I.D. to Multi-Agent AI")
        self.assertEqual(mission["status"], "IN_PROGRESS")
        self.assertEqual(mission["progress"], 0)
        self.assertEqual(len(mission["steps"]), 3)
        self.assertEqual(len(mission["assigned_agents"]), 4)

    def test_update_mission_progress_and_step(self):
        steps = ["Step 1", "Step 2", "Step 3", "Step 4"]
        mid = self.missions.create_mission(
            title="Progress Test Mission",
            goal="Test step completion updates",
            steps=steps
        )

        # Complete Step 0 (Step 1)
        self.missions.update_mission(mid, completed_step_index=0)
        m1 = self.missions.get_mission(mid)
        self.assertEqual(m1["progress"], 25)
        self.assertTrue(m1["steps"][0]["completed"])

        # Complete Step 1 (Step 2)
        self.missions.update_mission(mid, completed_step_index=1, current_objective="Working on Step 3")
        m2 = self.missions.get_mission(mid)
        self.assertEqual(m2["progress"], 50)
        self.assertEqual(m2["current_objective"], "Working on Step 3")

    def test_list_missions_filter(self):
        mid1 = self.missions.create_mission("Mission Alpha", "Goal A")
        mid2 = self.missions.create_mission("Mission Beta", "Goal B")
        self.missions.update_mission(mid2, status="COMPLETED", progress=100)

        in_progress = self.missions.list_missions(status="IN_PROGRESS")
        self.assertEqual(len(in_progress), 1)
        self.assertEqual(in_progress[0]["id"], mid1)

        completed = self.missions.list_missions(status="COMPLETED")
        self.assertEqual(len(completed), 1)
        self.assertEqual(completed[0]["id"], mid2)

        all_m = self.missions.list_missions()
        self.assertEqual(len(all_m), 2)

if __name__ == "__main__":
    unittest.main()
