# core/mission.py
import json
import os
import sqlite3
import time
from typing import Dict, Any, List, Optional

class MissionManager:
    """
    Persistent Long-Running Mission Management for V.O.I.D.
    Tracks multi-step goals, progress %, active objectives, blockers, and assigned agents.
    Persisted in local SQLite database across computer restarts.
    """
    _instance: Optional['MissionManager'] = None

    def __init__(self, db_path: str = "void_memory/void_missions.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls) -> 'MissionManager':
        if cls._instance is None:
            cls._instance = MissionManager()
        return cls._instance

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS missions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT,
                goal TEXT,
                status TEXT,
                progress INTEGER DEFAULT 0,
                current_objective TEXT,
                blockers TEXT,
                steps_json TEXT,
                assigned_agents TEXT,
                created_at REAL,
                updated_at REAL
            )
        ''')
        conn.commit()
        conn.close()

    def create_mission(
        self,
        title: str,
        goal: str,
        steps: Optional[List[str]] = None,
        assigned_agents: Optional[List[str]] = None
    ) -> int:
        now = time.time()
        steps_list = [{"title": s, "completed": False} for s in (steps or [])]
        agents_list = assigned_agents or ["executive", "planning_agent", "coding_agent", "verification_agent"]

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            INSERT INTO missions (title, goal, status, progress, current_objective, blockers, steps_json, assigned_agents, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            title,
            goal,
            "IN_PROGRESS",
            0,
            steps[0] if steps else "Initial analysis",
            "",
            json.dumps(steps_list),
            json.dumps(agents_list),
            now,
            now
        ))
        mission_id = c.lastrowid
        conn.commit()
        conn.close()
        return mission_id

    def update_mission(
        self,
        mission_id: int,
        progress: Optional[int] = None,
        status: Optional[str] = None,
        current_objective: Optional[str] = None,
        blockers: Optional[str] = None,
        completed_step_index: Optional[int] = None
    ) -> bool:
        now = time.time()
        mission = self.get_mission(mission_id)
        if not mission:
            return False

        steps = mission["steps"]
        if completed_step_index is not None and 0 <= completed_step_index < len(steps):
            steps[completed_step_index]["completed"] = True
            # Recalculate progress if not explicitly passed
            if progress is None:
                completed_count = sum(1 for s in steps if s.get("completed"))
                progress = int((completed_count / len(steps)) * 100)

        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            UPDATE missions SET
                progress = COALESCE(?, progress),
                status = COALESCE(?, status),
                current_objective = COALESCE(?, current_objective),
                blockers = COALESCE(?, blockers),
                steps_json = ?,
                updated_at = ?
            WHERE id = ?
        ''', (
            progress,
            status,
            current_objective,
            blockers,
            json.dumps(steps),
            now,
            mission_id
        ))
        updated = c.rowcount > 0
        conn.commit()
        conn.close()
        return updated

    def get_mission(self, mission_id: int) -> Optional[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('SELECT id, title, goal, status, progress, current_objective, blockers, steps_json, assigned_agents, created_at, updated_at FROM missions WHERE id = ?', (mission_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            return None
        return {
            "id": row[0],
            "title": row[1],
            "goal": row[2],
            "status": row[3],
            "progress": row[4],
            "current_objective": row[5],
            "blockers": row[6],
            "steps": json.loads(row[7]) if row[7] else [],
            "assigned_agents": json.loads(row[8]) if row[8] else [],
            "created_at": row[9],
            "updated_at": row[10]
        }

    def list_missions(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        if status:
            c.execute('SELECT id, title, goal, status, progress, current_objective, blockers, steps_json, assigned_agents, created_at, updated_at FROM missions WHERE status = ? ORDER BY updated_at DESC', (status,))
        else:
            c.execute('SELECT id, title, goal, status, progress, current_objective, blockers, steps_json, assigned_agents, created_at, updated_at FROM missions ORDER BY updated_at DESC')
        rows = c.fetchall()
        conn.close()

        missions = []
        for r in rows:
            missions.append({
                "id": r[0],
                "title": r[1],
                "goal": r[2],
                "status": r[3],
                "progress": r[4],
                "current_objective": r[5],
                "blockers": r[6],
                "steps": json.loads(r[7]) if r[7] else [],
                "assigned_agents": json.loads(r[8]) if r[8] else [],
                "created_at": r[9],
                "updated_at": r[10]
            })
        return missions

    def delete_mission(self, mission_id: int) -> bool:
        """Deletes a mission by ID."""
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('DELETE FROM missions WHERE id = ?', (mission_id,))
        deleted = c.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def toggle_step(self, mission_id: int, step_index: int) -> Optional[Dict[str, Any]]:
        """Toggles the completion status of a specific step in a mission."""
        mission = self.get_mission(mission_id)
        if not mission or step_index < 0 or step_index >= len(mission["steps"]):
            return None

        steps = mission["steps"]
        steps[step_index]["completed"] = not steps[step_index].get("completed", False)
        completed_count = sum(1 for s in steps if s.get("completed"))
        progress = int((completed_count / len(steps)) * 100) if steps else 100
        new_status = "COMPLETED" if progress == 100 else ("IN_PROGRESS" if progress > 0 else "QUEUED")

        self.update_mission(
            mission_id=mission_id,
            progress=progress,
            status=new_status,
            completed_step_index=None
        )
        return self.get_mission(mission_id)


mission_manager = MissionManager.get_instance()

