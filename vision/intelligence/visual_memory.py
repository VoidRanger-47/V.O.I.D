"""
vision/intelligence/visual_memory.py
Persistent SQLite-backed visual memory system for V.O.I.D.
Stores structured visual observations, context, timestamps, and importance scores.
Provides intelligent temporal search and automated observation pruning.
"""

import os
import sqlite3
import time
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger("void.vision.visual_memory")

class VisualMemory:
    """
    Manages episodic visual memories and environmental observations.
    """
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            data_dir = os.path.join(base_dir, "data")
            os.makedirs(data_dir, exist_ok=True)
            self.db_path = os.path.join(data_dir, "observations.db")
        else:
            self.db_path = db_path
            os.makedirs(os.path.dirname(db_path), exist_ok=True)

        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Create visual memory schema if not exists and migrate new columns."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS visual_observations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    iso_time TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    object_name TEXT,
                    person_name TEXT,
                    context TEXT,
                    confidence REAL,
                    importance REAL DEFAULT 0.5,
                    metadata_json TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_ts ON visual_observations(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_obj ON visual_observations(object_name)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_event ON visual_observations(event_type)")
            
            # Migration check: Ensure person_name exists for legacy databases
            cursor.execute("PRAGMA table_info(visual_observations)")
            columns = [info[1] for info in cursor.fetchall()]
            if "person_name" not in columns:
                cursor.execute("ALTER TABLE visual_observations ADD COLUMN person_name TEXT")
            
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_vis_person ON visual_observations(person_name)")
            conn.commit()

    def record_observation(
        self,
        event_type: str,
        object_name: Optional[str] = None,
        person_name: Optional[str] = None,
        context: str = "workspace",
        confidence: float = 1.0,
        importance: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Record a structured visual observation (person or object).
        """
        now = time.time()
        iso_str = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S")
        meta_str = json.dumps(metadata or {})

        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO visual_observations 
                (timestamp, iso_time, event_type, object_name, person_name, context, confidence, importance, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (now, iso_str, event_type, object_name, person_name, context, confidence, importance, meta_str))
            obs_id = cursor.lastrowid
            conn.commit()

        return obs_id

    def record_person_sighting(
        self,
        person_name: str,
        confidence: float = 1.0,
        context: str = "camera_view",
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """Record a sighting of a specific person."""
        return self.record_observation(
            event_type="PERSON_SIGHTING",
            person_name=person_name,
            context=context,
            confidence=confidence,
            importance=0.8 if person_name.lower() != "unknown person" else 0.4,
            metadata=metadata
        )

    def query_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve most recent visual observations."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, iso_time, event_type, object_name, person_name, context, confidence, importance, metadata_json
                FROM visual_observations
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def query_by_object(self, object_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for historical observations of a specific object."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, iso_time, event_type, object_name, person_name, context, confidence, importance, metadata_json
                FROM visual_observations
                WHERE LOWER(object_name) LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{object_name.lower().strip()}%", limit))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def query_person_history(self, person_name: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search for historical sightings of a specific person."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, timestamp, iso_time, event_type, object_name, person_name, context, confidence, importance, metadata_json
                FROM visual_observations
                WHERE LOWER(person_name) LIKE ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (f"%{person_name.lower().strip()}%", limit))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def query_last_seen_person(self, person_name: str) -> Optional[Dict[str, Any]]:
        """Get the single most recent sighting of a named person."""
        history = self.query_person_history(person_name, limit=1)
        return history[0] if history else None

    def query_last_seen_object(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Get the single most recent sighting of an object."""
        history = self.query_by_object(object_name, limit=1)
        return history[0] if history else None

    def query_people_seen_today(self) -> List[Dict[str, Any]]:
        """Get summary of distinct people detected today with their latest timestamp."""
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT person_name, MAX(timestamp) as last_seen, MAX(iso_time) as last_iso, COUNT(*) as sightings_count
                FROM visual_observations
                WHERE timestamp >= ? AND person_name IS NOT NULL AND person_name != ''
                GROUP BY person_name
                ORDER BY last_seen DESC
            """, (start_of_day,))
            rows = cursor.fetchall()
            return [
                {
                    "name": r["person_name"],
                    "last_seen_timestamp": r["last_seen"],
                    "last_seen_time": r["last_iso"],
                    "sightings_count": r["sightings_count"]
                }
                for r in rows
            ]

    def query_today_objects(self) -> List[str]:
        """Get unique objects detected today."""
        start_of_day = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT object_name
                FROM visual_observations
                WHERE timestamp >= ? AND object_name IS NOT NULL AND object_name != ''
            """, (start_of_day,))
            rows = cursor.fetchall()
            return [r[0] for r in rows if r[0]]

    def prune_old_memories(self, max_records: int = 5000, min_importance: float = 0.3):
        """Automatically remove stale low-importance observations to maintain DB size."""
        with self._get_conn() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM visual_observations")
            count = cursor.fetchone()[0]

            if count > max_records:
                to_delete = count - max_records
                cursor.execute("""
                    DELETE FROM visual_observations
                    WHERE id IN (
                        SELECT id FROM visual_observations
                        WHERE importance < ?
                        ORDER BY timestamp ASC
                        LIMIT ?
                    )
                """, (min_importance, to_delete))
                conn.commit()
                logger.info(f"Pruned {cursor.rowcount} low-importance visual records.")

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        meta = {}
        if row["metadata_json"]:
            try:
                meta = json.loads(row["metadata_json"])
            except Exception:
                pass
        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "iso_time": row["iso_time"],
            "event_type": row["event_type"],
            "object": row["object_name"],
            "person": row["person_name"] if "person_name" in row.keys() else None,
            "context": row["context"],
            "confidence": row["confidence"],
            "importance": row["importance"],
            "metadata": meta
        }
