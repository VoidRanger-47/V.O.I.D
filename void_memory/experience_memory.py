# void_memory/experience_memory.py
"""
Experience-Based Learning Memory for V.O.I.D.
Records every meaningful action as a structured experience:
  Situation -> Action -> Expected Result -> Actual Result -> Success/Failure -> Failure Cause -> Better Strategy
Transforms experiences into reusable procedural knowledge.
"""

import os
import json
import time
import uuid
import sqlite3
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class ExperienceRecord:
    id: str = field(default_factory=lambda: f"exp_{str(uuid.uuid4())[:8]}")
    task_id: str = "task_general"
    situation: str = ""
    action: str = ""
    expected_result: str = ""
    actual_result: str = ""
    success: bool = True
    failure_cause: Optional[str] = None
    better_strategy: Optional[str] = None
    learned_rule: Optional[str] = None
    domain: str = "general"
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ExperienceMemory:
    """
    Persistent store for V.O.I.D. operational experiences and derived procedural rules.
    """
    _instance: Optional['ExperienceMemory'] = None

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    @classmethod
    def get_instance(cls) -> 'ExperienceMemory':
        if cls._instance is None:
            cls._instance = ExperienceMemory()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS experience_records (
                id TEXT PRIMARY KEY,
                task_id TEXT NOT NULL,
                situation TEXT NOT NULL,
                action TEXT NOT NULL,
                expected_result TEXT,
                actual_result TEXT,
                success INTEGER NOT NULL,
                failure_cause TEXT,
                better_strategy TEXT,
                learned_rule TEXT,
                domain TEXT DEFAULT 'general',
                created_at REAL NOT NULL
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_exp_domain ON experience_records(domain)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_exp_success ON experience_records(success)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_exp_created ON experience_records(created_at)')

        # FTS table for rapid situational retrieval
        try:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS experience_fts USING fts5(
                    id UNINDEXED,
                    situation,
                    action,
                    failure_cause,
                    learned_rule
                )
            ''')
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_exp_ai AFTER INSERT ON experience_records BEGIN
                    INSERT INTO experience_fts(id, situation, action, failure_cause, learned_rule)
                    VALUES (new.id, new.situation, new.action, new.failure_cause, new.learned_rule);
                END;
            ''')
        except Exception:
            pass

        conn.commit()
        conn.close()

    def record_experience(
        self,
        situation: str,
        action: str,
        expected_result: str,
        actual_result: str,
        success: bool,
        task_id: str = "task_general",
        failure_cause: Optional[str] = None,
        better_strategy: Optional[str] = None,
        learned_rule: Optional[str] = None,
        domain: str = "general"
    ) -> ExperienceRecord:
        """
        Records a completed action and derives or stores a procedural rule.
        """
        # Automatically derive a rule if failed and cause is known
        rule = learned_rule
        if not rule and not success and failure_cause:
            strat = better_strategy or "verify environment and inputs before proceeding"
            rule = f"In situation '{situation[:50]}', if error '{failure_cause[:50]}' occurs, apply strategy: {strat}."

        rec = ExperienceRecord(
            task_id=task_id,
            situation=situation.strip(),
            action=action.strip(),
            expected_result=expected_result.strip(),
            actual_result=actual_result.strip(),
            success=success,
            failure_cause=failure_cause.strip() if failure_cause else None,
            better_strategy=better_strategy.strip() if better_strategy else None,
            learned_rule=rule.strip() if rule else None,
            domain=domain.strip(),
            created_at=time.time()
        )

        conn = self._get_connection()
        conn.execute('''
            INSERT INTO experience_records (
                id, task_id, situation, action, expected_result, actual_result,
                success, failure_cause, better_strategy, learned_rule, domain, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            rec.id, rec.task_id, rec.situation, rec.action, rec.expected_result, rec.actual_result,
            1 if rec.success else 0, rec.failure_cause, rec.better_strategy, rec.learned_rule,
            rec.domain, rec.created_at
        ))
        conn.commit()
        conn.close()

        return rec

    def find_relevant_experiences(self, situation: str, domain: Optional[str] = None, limit: int = 5) -> List[ExperienceRecord]:
        """
        Retrieves past experiences matching the current situation to avoid repeating past mistakes.
        """
        conn = self._get_connection()
        tokens = [t for t in situation.replace("'", " ").replace('"', " ").split() if len(t) > 3][:6]
        results = []

        if tokens:
            try:
                fts_query = " OR ".join(tokens)
                sql = '''
                    SELECT e.* FROM experience_records e
                    JOIN experience_fts f ON e.id = f.id
                    WHERE experience_fts MATCH ?
                '''
                params = [fts_query]
                if domain:
                    sql += " AND e.domain = ?"
                    params.append(domain)
                sql += " ORDER BY e.created_at DESC LIMIT ?"
                params.append(limit)

                rows = conn.execute(sql, params).fetchall()
                for r in rows:
                    results.append(ExperienceRecord(
                        id=r["id"],
                        task_id=r["task_id"],
                        situation=r["situation"],
                        action=r["action"],
                        expected_result=r["expected_result"],
                        actual_result=r["actual_result"],
                        success=bool(r["success"]),
                        failure_cause=r["failure_cause"],
                        better_strategy=r["better_strategy"],
                        learned_rule=r["learned_rule"],
                        domain=r["domain"],
                        created_at=r["created_at"]
                    ))
            except Exception:
                pass

        # Fallback to recent experiences in domain
        if not results:
            sql = "SELECT * FROM experience_records WHERE 1=1"
            params = []
            if domain:
                sql += " AND domain = ?"
                params.append(domain)
            sql += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            for r in rows:
                results.append(ExperienceRecord(
                    id=r["id"],
                    task_id=r["task_id"],
                    situation=r["situation"],
                    action=r["action"],
                    expected_result=r["expected_result"],
                    actual_result=r["actual_result"],
                    success=bool(r["success"]),
                    failure_cause=r["failure_cause"],
                    better_strategy=r["better_strategy"],
                    learned_rule=r["learned_rule"],
                    domain=r["domain"],
                    created_at=r["created_at"]
                ))

        conn.close()
        return results

    def get_procedural_rules_for_situation(self, situation: str, domain: Optional[str] = None) -> List[str]:
        """
        Extracts verified procedural rules to guide planning and prevent repeating known failures.
        """
        experiences = self.find_relevant_experiences(situation, domain=domain, limit=6)
        rules = []
        for exp in experiences:
            if exp.learned_rule and exp.learned_rule not in rules:
                rules.append(exp.learned_rule)
        return rules

    def get_stats(self) -> Dict[str, int]:
        """Returns total experiences and learned procedural rules count."""
        conn = self._get_connection()
        total_exp = conn.execute("SELECT COUNT(*) FROM experience_records").fetchone()[0]
        total_rules = conn.execute("SELECT COUNT(*) FROM experience_records WHERE learned_rule IS NOT NULL AND learned_rule != ''").fetchone()[0]
        conn.close()
        return {"total_experiences": total_exp, "total_procedural_rules": total_rules}

    def list_experiences(self, limit: int = 50) -> List[ExperienceRecord]:
        """Lists recent experiences."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM experience_records ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [
            ExperienceRecord(
                id=r["id"],
                task_id=r["task_id"],
                situation=r["situation"],
                action=r["action"],
                expected_result=r["expected_result"],
                actual_result=r["actual_result"],
                success=bool(r["success"]),
                failure_cause=r["failure_cause"],
                better_strategy=r["better_strategy"],
                learned_rule=r["learned_rule"],
                domain=r["domain"],
                created_at=r["created_at"]
            )
            for r in rows
        ]

    def get_all_procedural_rules(self, limit: int = 50) -> List[str]:
        """Returns unique learned procedural rules."""
        conn = self._get_connection()
        rows = conn.execute("SELECT DISTINCT learned_rule FROM experience_records WHERE learned_rule IS NOT NULL AND learned_rule != '' LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [r["learned_rule"] for r in rows]


experience_memory = ExperienceMemory.get_instance()
