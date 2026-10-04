"""
core/agents/reflection.py
Self-Reflection & Metacognitive Evaluation Engine for V.O.I.D.
Analyzes completed task trajectories, extracts root causes of failures/successes,
and consolidates learned lessons into persistent long-term memory.
"""

import os
import sqlite3
import time
from typing import Dict, Any, List, Optional


class SelfReflectionEngine:
    """
    Evaluates completed tasks:
    - Analyzes execution trajectories
    - Summarizes what worked and what failed
    - Synthesizes actionable procedural lessons
    - Persists reflections to SQLite and void_memory for continuous improvement.
    """
    _instance: Optional['SelfReflectionEngine'] = None

    def __init__(self, db_path: str = "void_memory/reflections.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls) -> 'SelfReflectionEngine':
        if cls._instance is None:
            cls._instance = SelfReflectionEngine()
        return cls._instance

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS reflections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT,
                goal TEXT,
                success INTEGER,
                approach TEXT,
                what_worked TEXT,
                what_failed TEXT,
                lesson_learned TEXT,
                metrics_json TEXT,
                timestamp REAL
            )
        ''')
        conn.commit()
        conn.close()

    def evaluate_task(
        self,
        goal: str,
        steps: List[Dict[str, Any]],
        output: Any,
        success: bool,
        task_id: Optional[str] = None,
        duration_ms: Optional[float] = None,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Synthesizes a structured metacognitive self-reflection report.
        """
        task_id = task_id or f"task_{int(time.time())}"
        out_str = str(output) if output is not None else ""
        err_str = str(error) if error else ""

        # 1. Analyze successful aspects
        successful_steps = [s for s in steps if s.get("status") == "SUCCESS" or s.get("verdict") == "PASS"]
        what_worked = []
        if successful_steps:
            for s in successful_steps:
                agent = s.get("agent", "tool")
                goal_desc = s.get("goal", s.get("action", "step"))
                what_worked.append(f"{agent.upper()} completed: {goal_desc}")
        elif success:
            what_worked.append("Primary execution loop concluded without exceptions.")
        else:
            what_worked.append("Goal decomposition and initial intent routing completed successfully.")

        # 2. Analyze failure points or bottlenecks
        failed_steps = [s for s in steps if s.get("status") in ["FAILED", "REPLAN_REQUIRED"] or s.get("verdict") == "FAIL"]
        what_failed = []
        if failed_steps:
            for s in failed_steps:
                agent = s.get("agent", "tool")
                err = s.get("error", s.get("result", "unknown error"))
                what_failed.append(f"{agent.upper()} failed on '{s.get('goal', '')}': {str(err)[:120]}")
        elif not success and err_str:
            what_failed.append(f"Execution error: {err_str[:120]}")
        else:
            what_failed.append("No critical runtime blockers detected.")

        # 3. Derive actionable lesson
        if success:
            lesson = f"Strategy verified: Decomposing '{goal[:60]}' through {len(steps)} sub-stages provided verifiable output."
        else:
            first_fail = failed_steps[0] if failed_steps else {}
            fail_cause = first_fail.get("error") or err_str or "unresolved constraint"
            lesson = f"Mitigation required: When attempting '{goal[:60]}', pre-validate inputs to prevent: {str(fail_cause)[:90]}."

        approach_desc = f"Executed {len(steps)} pipeline stages: " + " -> ".join(s.get("agent", "step") for s in steps)

        reflection = {
            "task_id": task_id,
            "goal": goal,
            "success": success,
            "approach": approach_desc,
            "what_worked": "\n".join(f"- {w}" for w in what_worked),
            "what_failed": "\n".join(f"- {f}" for f in what_failed),
            "lesson_learned": lesson,
            "duration_ms": duration_ms or 0,
            "timestamp": time.time()
        }

        # 4. Save to SQLite reflections database
        try:
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('''
                INSERT INTO reflections (task_id, goal, success, approach, what_worked, what_failed, lesson_learned, metrics_json, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                task_id,
                goal,
                1 if success else 0,
                approach_desc,
                reflection["what_worked"],
                reflection["what_failed"],
                lesson,
                f'{{"steps_count": {len(steps)}, "duration_ms": {duration_ms or 0}}}',
                time.time()
            ))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ReflectionEngine] SQLite write error: {e}")

        # 5. Consolidate lesson into VOID Long-Term Memory (void_memory)
        try:
            from void_memory.memory import VoidMemory
            mem = VoidMemory.get_instance()
            mem_content = f"Self-Reflection [{task_id}] — Goal: {goal} | Status: {'SUCCESS' if success else 'FAILED'} | Lesson: {lesson}"
            mem.store_memory(
                text=mem_content,
                tier="procedural",
                category="procedural_learning",
                importance=0.88 if success else 0.95
            )
        except Exception as e:
            print(f"[ReflectionEngine] Memory consolidation note: {e}")

        return reflection

    def list_reflections(self, limit: int = 30) -> List[Dict[str, Any]]:
        """Retrieve recent self-reflections sorted by timestamp descending."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            c = conn.cursor()
            c.execute('SELECT * FROM reflections ORDER BY timestamp DESC LIMIT ?', (limit,))
            rows = c.fetchall()
            conn.close()
            return [dict(r) for r in rows]
        except Exception as e:
            print(f"[ReflectionEngine] Read error: {e}")
            return []


reflection_engine = SelfReflectionEngine.get_instance()
