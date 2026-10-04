# core/world_model/model.py
"""
Persistent World Model for V.O.I.D.
Provides structured representation of entities, domains, capabilities, and causal relationships.
Supports cross-domain reasoning, dependency resolution, and compatibility auditing.
"""

import os
import json
import time
import sqlite3
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict

from core.world_model.relations import WorldRelationType


@dataclass
class WorldEntity:
    name: str
    domain: str = "general"     # programming, mathematics, physics, robotics, vision, system, general
    properties: Dict[str, Any] = field(default_factory=dict)
    capabilities: List[str] = field(default_factory=list)
    state: str = "nominal"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class WorldRelation:
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class WorldModel:
    """
    Central Persistent World Model for V.O.I.D.
    Backed by SQLite with in-memory graph indexing for high-speed cross-domain reasoning.
    """
    _instance: Optional['WorldModel'] = None

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()
        self._bootstrap_foundational_knowledge()

    @classmethod
    def get_instance(cls) -> 'WorldModel':
        if cls._instance is None:
            cls._instance = WorldModel()
        return cls._instance

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        conn = self._get_connection()
        c = conn.cursor()

        # Entities table
        c.execute('''
            CREATE TABLE IF NOT EXISTS world_entities (
                name TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                properties_json TEXT DEFAULT '{}',
                capabilities_json TEXT DEFAULT '[]',
                state TEXT DEFAULT 'nominal',
                created_at REAL NOT NULL,
                updated_at REAL NOT NULL
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_went_domain ON world_entities(domain)')

        # Relationships table
        c.execute('''
            CREATE TABLE IF NOT EXISTS world_relations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                target TEXT NOT NULL,
                relation_type TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                context_json TEXT DEFAULT '{}',
                created_at REAL NOT NULL,
                UNIQUE(source, target, relation_type)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wrel_src ON world_relations(source)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wrel_tgt ON world_relations(target)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_wrel_type ON world_relations(relation_type)')

        conn.commit()
        conn.close()

    def add_entity(
        self,
        name: str,
        domain: str = "general",
        properties: Optional[Dict[str, Any]] = None,
        capabilities: Optional[List[str]] = None,
        state: str = "nominal"
    ) -> WorldEntity:
        """Adds or updates a world entity."""
        clean_name = name.strip()
        now = time.time()
        props = properties or {}
        caps = capabilities or []

        conn = self._get_connection()
        conn.execute('''
            INSERT INTO world_entities (name, domain, properties_json, capabilities_json, state, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                domain = excluded.domain,
                properties_json = excluded.properties_json,
                capabilities_json = excluded.capabilities_json,
                state = excluded.state,
                updated_at = excluded.updated_at
        ''', (clean_name, domain, json.dumps(props), json.dumps(caps), state, now, now))
        conn.commit()
        conn.close()

        return WorldEntity(
            name=clean_name,
            domain=domain,
            properties=props,
            capabilities=caps,
            state=state,
            created_at=now,
            updated_at=now
        )

    def get_entity(self, name: str) -> Optional[WorldEntity]:
        conn = self._get_connection()
        row = conn.execute("SELECT * FROM world_entities WHERE name = ?", (name.strip(),)).fetchone()
        conn.close()
        if not row:
            return None
        return WorldEntity(
            name=row["name"],
            domain=row["domain"],
            properties=json.loads(row["properties_json"] or "{}"),
            capabilities=json.loads(row["capabilities_json"] or "[]"),
            state=row["state"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    def link_entities(
        self,
        source: str,
        target: str,
        relation_type: WorldRelationType,
        weight: float = 1.0,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Creates a directed semantic/causal relationship between two entities."""
        rel_str = relation_type.value if isinstance(relation_type, WorldRelationType) else str(relation_type)
        conn = self._get_connection()
        now = time.time()
        try:
            conn.execute('''
                INSERT INTO world_relations (source, target, relation_type, weight, context_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, target, relation_type) DO UPDATE SET
                    weight = excluded.weight,
                    context_json = excluded.context_json
            ''', (source.strip(), target.strip(), rel_str, weight, json.dumps(context or {}), now))
            conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ WorldModel link error: {e}")
            return False
        finally:
            conn.close()

    def get_relationships(
        self,
        entity_name: str,
        direction: str = "both"  # "outgoing", "incoming", or "both"
    ) -> List[WorldRelation]:
        """Retrieves active relationships for an entity."""
        conn = self._get_connection()
        name = entity_name.strip()
        results = []

        if direction in ("outgoing", "both"):
            rows = conn.execute("SELECT * FROM world_relations WHERE source = ?", (name,)).fetchall()
            for r in rows:
                results.append(WorldRelation(
                    source=r["source"],
                    target=r["target"],
                    relation_type=r["relation_type"],
                    weight=r["weight"],
                    context=json.loads(r["context_json"] or "{}"),
                    created_at=r["created_at"]
                ))

        if direction in ("incoming", "both"):
            rows = conn.execute("SELECT * FROM world_relations WHERE target = ?", (name,)).fetchall()
            for r in rows:
                results.append(WorldRelation(
                    source=r["source"],
                    target=r["target"],
                    relation_type=r["relation_type"],
                    weight=r["weight"],
                    context=json.loads(r["context_json"] or "{}"),
                    created_at=r["created_at"]
                ))

        conn.close()
        return results

    def find_causal_chain(self, start_entity: str, end_entity: str, max_depth: int = 4) -> Optional[List[str]]:
        """
        Finds a causal or dependency path between two entities (e.g. CAUSES, REQUIRES, DEPENDS_ON).
        """
        start = start_entity.strip()
        target = end_entity.strip()
        if start == target:
            return [start]

        conn = self._get_connection()
        causal_relations = {
            WorldRelationType.CAUSES.value,
            WorldRelationType.REQUIRES.value,
            WorldRelationType.DEPENDS_ON.value,
            WorldRelationType.PREVENTS.value
        }

        queue: List[List[str]] = [[start]]
        visited: Set[str] = {start}

        while queue:
            path = queue.pop(0)
            current = path[-1]

            if len(path) > max_depth:
                continue

            rows = conn.execute(
                "SELECT target, relation_type FROM world_relations WHERE source = ?",
                (current,)
            ).fetchall()

            for r in rows:
                nbr = r["target"]
                rel = r["relation_type"]
                if rel in causal_relations:
                    if nbr == target:
                        conn.close()
                        return path + [nbr]
                    if nbr not in visited:
                        visited.add(nbr)
                        queue.append(path + [nbr])

        conn.close()
        return None

    def check_compatibility(self, entity_a: str, entity_b: str) -> Tuple[bool, str]:
        """
        Checks whether two entities are known to be compatible or incompatible.
        """
        a = entity_a.strip()
        b = entity_b.strip()
        conn = self._get_connection()

        # Check explicit incompatibility
        incompat = conn.execute('''
            SELECT * FROM world_relations
            WHERE ((source = ? AND target = ?) OR (source = ? AND target = ?))
              AND relation_type = ?
        ''', (a, b, b, a, WorldRelationType.INCOMPATIBLE_WITH.value)).fetchone()

        if incompat:
            conn.close()
            return False, f"Direct incompatibility recorded between '{a}' and '{b}'."

        # Check explicit compatibility
        compat = conn.execute('''
            SELECT * FROM world_relations
            WHERE ((source = ? AND target = ?) OR (source = ? AND target = ?))
              AND relation_type = ?
        ''', (a, b, b, a, WorldRelationType.COMPATIBLE_WITH.value)).fetchone()

        conn.close()
        if compat:
            return True, f"'{a}' and '{b}' are verified compatible."

    def list_entities(self, limit: int = 100) -> List[WorldEntity]:
        """Lists registered world entities up to limit."""
        conn = self._get_connection()
        rows = conn.execute("SELECT * FROM world_entities LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [
            WorldEntity(
                name=r["name"],
                domain=r["domain"],
                properties=json.loads(r["properties_json"] or "{}"),
                capabilities=json.loads(r["capabilities_json"] or "[]"),
                state=r["state"],
                created_at=r["created_at"],
                updated_at=r["updated_at"]
            )
            for r in rows
        ]

    def get_stats(self) -> Dict[str, int]:
        """Returns entity and relation counts."""
        conn = self._get_connection()
        e_count = conn.execute("SELECT COUNT(*) FROM world_entities").fetchone()[0]
        r_count = conn.execute("SELECT COUNT(*) FROM world_relations").fetchone()[0]
        conn.close()
        return {"entity_count": e_count, "relation_count": r_count}

    def _bootstrap_foundational_knowledge(self):
        """Initializes core engineering and cross-domain knowledge bridges."""
        # Check if already initialized
        conn = self._get_connection()
        count = conn.execute("SELECT COUNT(*) FROM world_entities").fetchone()[0]
        conn.close()
        if count > 0:
            return

        # Foundational Entities
        entities = [
            ("Python", "programming", {"type": "language", "version": "3.11+"}, ["scripting", "machine_learning", "automation"]),
            ("SQLite", "system", {"type": "database", "storage": "single_file"}, ["relational_storage", "fts5_search", "wal_mode"]),
            ("NVIDIA_RTX_3050_Laptop", "hardware", {"vram_mb": 4096.0, "architecture": "Ampere"}, ["cuda_acceleration", "tensor_cores"]),
            ("PyTorch_CUDA", "programming", {"backend": "cuda"}, ["tensor_operations", "neural_inference"]),
            ("Vector_Mathematics", "mathematics", {"subfield": "linear_algebra"}, ["dot_product", "transformations", "spatial_geometry"]),
            ("Computer_Vision", "vision", {"tasks": ["detection", "tracking"]}, ["feature_extraction", "spatial_reasoning"]),
            ("Faster_Whisper", "system", {"engine": "ctranslate2"}, ["speech_to_text", "wake_word_sensing"]),
            ("Piper_TTS", "system", {"engine": "onnx"}, ["speech_synthesis"])
        ]
        for name, domain, props, caps in entities:
            self.add_entity(name, domain=domain, properties=props, capabilities=caps)

        # Foundational Relations
        self.link_entities("PyTorch_CUDA", "NVIDIA_RTX_3050_Laptop", WorldRelationType.REQUIRES)
        self.link_entities("Vector_Mathematics", "Computer_Vision", WorldRelationType.USED_FOR)
        self.link_entities("Computer_Vision", "Robotics_Movement", WorldRelationType.CAUSES)
        self.link_entities("Faster_Whisper", "Voice_Interaction", WorldRelationType.USED_FOR)


world_model = WorldModel.get_instance()
