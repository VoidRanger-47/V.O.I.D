# void_memory/database/repository.py
"""
SQLite Database Repository for V.O.I.D. Advanced Memory Engine.
Provides transactional storage, FTS5 full-text indexing, relationship graph persistence,
and backward-compatible migration.
"""

import os
import json
import sqlite3
import time
import uuid
from typing import List, Dict, Any, Optional, Tuple

from void_memory.database.models import (
    MemoryNode,
    MemoryRelationship,
    KnowledgeNode,
    ProjectMemoryRecord,
    MemoryTier,
    MemoryStatus,
    RelationshipType
)


class MemoryRepository:
    """
    SQLite Repository with FTS5 search, indexes, graph tables, and audit logs.
    """

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        """Initializes tables, FTS5 virtual index, triggers, and migrates legacy rows."""
        conn = self._get_connection()
        c = conn.cursor()

        # 1. Main Memories Table
        c.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                memory_type TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                importance REAL DEFAULT 0.5,
                confidence REAL DEFAULT 0.9,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                access_count INTEGER DEFAULT 1,
                source TEXT DEFAULT 'conversation',
                status TEXT DEFAULT 'active',
                pinned INTEGER DEFAULT 0,
                tags_json TEXT DEFAULT '[]',
                project_id TEXT,
                metadata_json TEXT DEFAULT '{}',
                embedding BLOB
            )
        ''')

        # 2. Indices for fast filtering
        c.execute('CREATE INDEX IF NOT EXISTS idx_mem_type ON memories(memory_type)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mem_status ON memories(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mem_importance ON memories(importance)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mem_project ON memories(project_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mem_created ON memories(created_at)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_mem_accessed ON memories(last_accessed)')

        # 3. FTS5 Virtual Table for Instant Offline Full-Text Keyword Search
        try:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts USING fts5(
                    id UNINDEXED,
                    content,
                    category,
                    tags_json
                )
            ''')

            # Triggers to keep FTS table synchronized with memories table
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_memories_ai AFTER INSERT ON memories BEGIN
                    INSERT INTO memories_fts(id, content, category, tags_json)
                    VALUES (new.id, new.content, new.category, new.tags_json);
                END;
            ''')
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_memories_ad AFTER DELETE ON memories BEGIN
                    DELETE FROM memories_fts WHERE id = old.id;
                END;
            ''')
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_memories_au AFTER UPDATE ON memories BEGIN
                    DELETE FROM memories_fts WHERE id = old.id;
                    INSERT INTO memories_fts(id, content, category, tags_json)
                    VALUES (new.id, new.content, new.category, new.tags_json);
                END;
            ''')
        except Exception as e:
            print(f"ℹ️ FTS5 notice (using standard fallback if unavailable): {e}")

        # 4. Memory Relationships (Knowledge Graph Edges)
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_relationships (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_id TEXT NOT NULL,
                target_id TEXT NOT NULL,
                relationship TEXT NOT NULL,
                weight REAL DEFAULT 1.0,
                created_at REAL NOT NULL,
                UNIQUE(source_id, target_id, relationship)
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_rel_source ON memory_relationships(source_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_rel_target ON memory_relationships(target_id)')

        # 5. Conceptual Knowledge Nodes (Entities)
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_knowledge_nodes (
                id TEXT PRIMARY KEY,
                node_type TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                description TEXT DEFAULT '',
                properties_json TEXT DEFAULT '{}',
                created_at REAL NOT NULL
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_knode_type ON memory_knowledge_nodes(node_type)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_knode_name ON memory_knowledge_nodes(name)')

        # 6. Project Context Records
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_projects (
                project_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                path TEXT DEFAULT '',
                architecture TEXT DEFAULT '',
                technologies_json TEXT DEFAULT '[]',
                decisions_json TEXT DEFAULT '[]',
                problems_and_solutions_json TEXT DEFAULT '[]',
                todos_json TEXT DEFAULT '[]',
                updated_at REAL NOT NULL
            )
        ''')

        # 7. Audit & Consolidation Log
        c.execute('''
            CREATE TABLE IF NOT EXISTS memory_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id TEXT,
                action TEXT NOT NULL,
                timestamp REAL NOT NULL,
                details_json TEXT DEFAULT '{}'
            )
        ''')

        # 8. Check and migrate legacy memory_nodes if present
        self._migrate_legacy_schema(conn)

        conn.commit()
        conn.close()

    def _migrate_legacy_schema(self, conn: sqlite3.Connection):
        """Migrate rows from legacy memory_nodes table if it exists."""
        c = conn.cursor()
        try:
            c.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memory_nodes'")
            if c.fetchone():
                c.execute("SELECT timestamp, tier, category, text, embedding, importance, access_count, last_accessed FROM memory_nodes")
                rows = c.fetchall()
                for r in rows:
                    content = r["text"]
                    if content:
                        # Check if already in new table
                        c.execute("SELECT id FROM memories WHERE content = ?", (content,))
                        if not c.fetchone():
                            mid = str(uuid.uuid4())
                            ts = r["timestamp"] or time.time()
                            tier = r["tier"] or MemoryTier.SEMANTIC.value
                            cat = r["category"] or "general"
                            imp = r["importance"] if r["importance"] is not None else 0.5
                            acc_cnt = r["access_count"] or 1
                            last_acc = r["last_accessed"] or ts
                            blob = r["embedding"]

                            c.execute('''
                                INSERT INTO memories (id, content, memory_type, category, importance, confidence, created_at, last_accessed, access_count, source, status, pinned, tags_json, metadata_json, embedding)
                                VALUES (?, ?, ?, ?, ?, 0.9, ?, ?, ?, 'legacy_migration', 'active', 0, '[]', '{}', ?)
                            ''', (mid, content, tier, cat, imp, ts, last_acc, acc_cnt, blob))
        except Exception as e:
            print(f"ℹ️ Legacy migration note: {e}")

    # =========================================================================
    # MEMORY CRUD OPERATIONS
    # =========================================================================

    def save_memory(self, node: MemoryNode) -> MemoryNode:
        """Insert or update a memory node."""
        conn = self._get_connection()
        c = conn.cursor()
        tags_str = json.dumps(node.tags)
        meta_str = json.dumps(node.metadata)
        pinned_int = 1 if node.pinned else 0

        c.execute('''
            INSERT INTO memories (
                id, content, memory_type, category, importance, confidence,
                created_at, last_accessed, access_count, source, status,
                pinned, tags_json, project_id, metadata_json, embedding
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                content = excluded.content,
                memory_type = excluded.memory_type,
                category = excluded.category,
                importance = excluded.importance,
                confidence = excluded.confidence,
                last_accessed = excluded.last_accessed,
                access_count = excluded.access_count,
                status = excluded.status,
                pinned = excluded.pinned,
                tags_json = excluded.tags_json,
                project_id = excluded.project_id,
                metadata_json = excluded.metadata_json,
                embedding = coalesce(excluded.embedding, memories.embedding)
        ''', (
            node.id, node.content, node.memory_type, node.category,
            node.importance, node.confidence, node.created_at,
            node.last_accessed, node.access_count, node.source,
            node.status, pinned_int, tags_str, node.project_id,
            meta_str, node.embedding
        ))

        # Log creation/update
        c.execute('''
            INSERT INTO memory_audit_log (memory_id, action, timestamp, details_json)
            VALUES (?, 'saved', ?, ?)
        ''', (node.id, time.time(), json.dumps({"category": node.category, "type": node.memory_type})))

        conn.commit()
        conn.close()
        return node

    def get_memory_by_id(self, memory_id: str) -> Optional[MemoryNode]:
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM memories WHERE id = ?', (memory_id,))
        row = c.fetchone()
        conn.close()
        if row:
            return self._row_to_node(row)
        return None

    def get_memory_by_exact_content(self, content: str) -> Optional[MemoryNode]:
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM memories WHERE content = ? AND status != ? LIMIT 1', (content.strip(), MemoryStatus.DELETED.value))
        row = c.fetchone()
        conn.close()
        if row:
            return self._row_to_node(row)
        return None

    def list_memories(
        self,
        memory_type: Optional[str] = None,
        category: Optional[str] = None,
        status: Optional[str] = MemoryStatus.ACTIVE.value,
        project_id: Optional[str] = None,
        pinned_only: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> List[MemoryNode]:
        conn = self._get_connection()
        c = conn.cursor()

        query = "SELECT * FROM memories WHERE 1=1"
        params: List[Any] = []

        if memory_type:
            query += " AND memory_type = ?"
            params.append(memory_type)
        if category:
            query += " AND category = ?"
            params.append(category)
        if status:
            query += " AND status = ?"
            params.append(status)
        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)
        if pinned_only:
            query += " AND pinned = 1"

        query += " ORDER BY pinned DESC, importance DESC, last_accessed DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return [self._row_to_node(r) for r in rows]

    def update_access(self, memory_id: str):
        """Update last_accessed timestamp and increment access_count."""
        conn = self._get_connection()
        c = conn.cursor()
        now = time.time()
        c.execute('''
            UPDATE memories
            SET last_accessed = ?, access_count = access_count + 1
            WHERE id = ?
        ''', (now, memory_id))
        conn.commit()
        conn.close()

    def update_status(self, memory_id: str, new_status: str) -> bool:
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('UPDATE memories SET status = ? WHERE id = ?', (new_status, memory_id))
        updated = c.rowcount > 0
        if updated:
            c.execute('INSERT INTO memory_audit_log (memory_id, action, timestamp, details_json) VALUES (?, ?, ?, ?)',
                      (memory_id, f"status_{new_status}", time.time(), json.dumps({"status": new_status})))
        conn.commit()
        conn.close()
        return updated

    def delete_memory(self, memory_id: str, hard_delete: bool = False) -> bool:
        conn = self._get_connection()
        c = conn.cursor()
        if hard_delete:
            c.execute('DELETE FROM memory_relationships WHERE source_id = ? OR target_id = ?', (memory_id, memory_id))
            c.execute('DELETE FROM memories WHERE id = ?', (memory_id,))
            deleted = c.rowcount > 0
        else:
            c.execute('UPDATE memories SET status = ? WHERE id = ?', (MemoryStatus.DELETED.value, memory_id))
            deleted = c.rowcount > 0

        if deleted:
            c.execute('INSERT INTO memory_audit_log (memory_id, action, timestamp, details_json) VALUES (?, ?, ?, ?)',
                      (memory_id, "hard_deleted" if hard_delete else "soft_deleted", time.time(), "{}"))

        conn.commit()
        conn.close()
        return deleted

    def forget_matching(self, query: str) -> int:
        """Purges or soft-deletes memories containing the target query."""
        clean = query.strip().lower()
        if not clean:
            return 0
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('SELECT id FROM memories WHERE lower(content) LIKE ? AND status != ?',
                  (f"%{clean}%", MemoryStatus.DELETED.value))
        rows = c.fetchall()
        count = 0
        for r in rows:
            mid = r["id"]
            c.execute('UPDATE memories SET status = ? WHERE id = ?', (MemoryStatus.DELETED.value, mid))
            count += 1
            c.execute('INSERT INTO memory_audit_log (memory_id, action, timestamp, details_json) VALUES (?, "forgotten", ?, ?)',
                      (mid, time.time(), json.dumps({"match_query": clean})))
        conn.commit()
        conn.close()
        return count

    # =========================================================================
    # FTS5 & KEYWORD RETRIEVAL
    # =========================================================================

    def search_fts(self, query: str, limit: int = 10, status: str = MemoryStatus.ACTIVE.value) -> List[Tuple[MemoryNode, float]]:
        """Search memories using SQLite FTS5 full-text index with rank score."""
        clean_q = "".join(c for c in query if c.isalnum() or c.isspace()).strip()
        if not clean_q:
            return []

        conn = self._get_connection()
        c = conn.cursor()
        results: List[Tuple[MemoryNode, float]] = []

        try:
            # FTS5 match query
            tokens = [f'"{t}"' for t in clean_q.split() if len(t) > 1]
            if not tokens:
                tokens = [f'"{clean_q}"']
            fts_match_expr = " OR ".join(tokens)

            sql = '''
                SELECT m.*, rank
                FROM memories_fts f
                JOIN memories m ON m.id = f.id
                WHERE memories_fts MATCH ? AND m.status = ?
                ORDER BY rank
                LIMIT ?
            '''
            c.execute(sql, (fts_match_expr, status, limit))
            rows = c.fetchall()

            for r in rows:
                node = self._row_to_node(r)
                # FTS5 rank is negative (lower = better), normalize to 0..1
                raw_rank = r["rank"] if "rank" in r.keys() else -1.0
                score = max(0.1, min(1.0, 1.0 / (1.0 + abs(float(raw_rank)))))
                results.append((node, score))

        except Exception as e:
            # Fallback LIKE search if FTS syntax fails
            try:
                like_expr = f"%{clean_q}%"
                c.execute('SELECT * FROM memories WHERE content LIKE ? AND status = ? LIMIT ?', (like_expr, status, limit))
                for r in c.fetchall():
                    results.append((self._row_to_node(r), 0.75))
            except Exception:
                pass
        finally:
            conn.close()

        return results

    # =========================================================================
    # RELATIONSHIP & KNOWLEDGE GRAPH OPERATIONS
    # =========================================================================

    def add_relationship(self, rel: MemoryRelationship) -> bool:
        conn = self._get_connection()
        c = conn.cursor()
        try:
            c.execute('''
                INSERT INTO memory_relationships (source_id, target_id, relationship, weight, created_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(source_id, target_id, relationship) DO UPDATE SET
                    weight = excluded.weight
            ''', (rel.source_id, rel.target_id, rel.relationship, rel.weight, rel.created_at))
            conn.commit()
            return True
        except Exception as e:
            print(f"⚠️ Failed to add memory relationship: {e}")
            return False
        finally:
            conn.close()

    def get_related_memories(self, memory_id: str, relationship: Optional[str] = None) -> List[Tuple[MemoryNode, str, float]]:
        """Finds connected memories and knowledge entities (outgoing and incoming edges)."""
        conn = self._get_connection()
        c = conn.cursor()

        sql = '''
            SELECT 
                r.source_id, r.target_id, r.relationship, r.weight,
                m.id, m.content, m.memory_type, m.category, m.importance, m.confidence,
                m.created_at, m.last_accessed, m.access_count, m.source, m.status, m.pinned,
                m.tags_json, m.project_id, m.metadata_json, m.embedding,
                k.name as kname, k.description as kdesc, k.node_type as ktype
            FROM memory_relationships r
            LEFT JOIN memories m ON m.id = r.target_id
            LEFT JOIN memory_knowledge_nodes k ON (k.name = r.target_id OR k.id = r.target_id)
            WHERE r.source_id = ? AND (m.status IS NULL OR m.status != ?)
        '''
        params: List[Any] = [memory_id, MemoryStatus.DELETED.value]
        if relationship:
            sql += " AND r.relationship = ?"
            params.append(relationship)

        c.execute(sql, params)
        results = []
        for r in c.fetchall():
            if r["id"]:
                node = self._row_to_node(r)
            else:
                # Entity node from knowledge graph
                node = MemoryNode(
                    id=r["target_id"],
                    content=r["kdesc"] or f"Entity: {r['target_id']}",
                    memory_type=r["ktype"] or "concept",
                    category="knowledge_graph",
                    importance=0.7
                )
            results.append((node, r["relationship"], float(r["weight"])))

        # Also get incoming edges
        sql_in = '''
            SELECT 
                r.source_id, r.target_id, r.relationship, r.weight,
                m.id, m.content, m.memory_type, m.category, m.importance, m.confidence,
                m.created_at, m.last_accessed, m.access_count, m.source, m.status, m.pinned,
                m.tags_json, m.project_id, m.metadata_json, m.embedding,
                k.name as kname, k.description as kdesc, k.node_type as ktype
            FROM memory_relationships r
            LEFT JOIN memories m ON m.id = r.source_id
            LEFT JOIN memory_knowledge_nodes k ON (k.name = r.source_id OR k.id = r.source_id)
            WHERE r.target_id = ? AND (m.status IS NULL OR m.status != ?)
        '''
        params_in: List[Any] = [memory_id, MemoryStatus.DELETED.value]
        if relationship:
            sql_in += " AND r.relationship = ?"
            params_in.append(relationship)

        c.execute(sql_in, params_in)
        for r in c.fetchall():
            if r["id"]:
                node = self._row_to_node(r)
            else:
                node = MemoryNode(
                    id=r["source_id"],
                    content=r["kdesc"] or f"Entity: {r['source_id']}",
                    memory_type=r["ktype"] or "concept",
                    category="knowledge_graph",
                    importance=0.7
                )
            results.append((node, f"incoming_{r['relationship']}", float(r["weight"])))

        conn.close()
        return results

    def save_knowledge_node(self, node: KnowledgeNode) -> KnowledgeNode:
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO memory_knowledge_nodes (id, node_type, name, description, properties_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                node_type = excluded.node_type,
                description = excluded.description,
                properties_json = excluded.properties_json
        ''', (node.id, node.node_type, node.name, node.description, json.dumps(node.properties), node.created_at))
        conn.commit()
        conn.close()
        return node

    def list_knowledge_nodes(self, node_type: Optional[str] = None) -> List[KnowledgeNode]:
        conn = self._get_connection()
        c = conn.cursor()
        if node_type:
            c.execute('SELECT * FROM memory_knowledge_nodes WHERE node_type = ? ORDER BY name ASC', (node_type,))
        else:
            c.execute('SELECT * FROM memory_knowledge_nodes ORDER BY node_type, name ASC')
        rows = c.fetchall()
        conn.close()

        nodes = []
        for r in rows:
            try:
                props = json.loads(r["properties_json"])
            except Exception:
                props = {}
            nodes.append(KnowledgeNode(
                id=r["id"],
                node_type=r["node_type"],
                name=r["name"],
                description=r["description"],
                properties=props,
                created_at=r["created_at"]
            ))
        return nodes

    # =========================================================================
    # PROJECT MEMORY PERSISTENCE
    # =========================================================================

    def save_project_record(self, record: ProjectMemoryRecord) -> ProjectMemoryRecord:
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            INSERT INTO memory_projects (
                project_id, name, path, architecture, technologies_json,
                decisions_json, problems_and_solutions_json, todos_json, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id) DO UPDATE SET
                name = excluded.name,
                path = excluded.path,
                architecture = excluded.architecture,
                technologies_json = excluded.technologies_json,
                decisions_json = excluded.decisions_json,
                problems_and_solutions_json = excluded.problems_and_solutions_json,
                todos_json = excluded.todos_json,
                updated_at = excluded.updated_at
        ''', (
            record.project_id, record.name, record.path, record.architecture,
            json.dumps(record.technologies), json.dumps(record.decisions),
            json.dumps(record.problems_and_solutions), json.dumps(record.todos),
            record.updated_at
        ))
        conn.commit()
        conn.close()
        return record

    def get_project_record(self, project_id: str = "default") -> Optional[ProjectMemoryRecord]:
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('SELECT * FROM memory_projects WHERE project_id = ?', (project_id,))
        r = c.fetchone()
        conn.close()
        if not r:
            return None

        try:
            techs = json.loads(r["technologies_json"])
        except Exception:
            techs = []
        try:
            decs = json.loads(r["decisions_json"])
        except Exception:
            decs = []
        try:
            probs = json.loads(r["problems_and_solutions_json"])
        except Exception:
            probs = []
        try:
            todos = json.loads(r["todos_json"])
        except Exception:
            todos = []

        return ProjectMemoryRecord(
            project_id=r["project_id"],
            name=r["name"],
            path=r["path"],
            architecture=r["architecture"],
            technologies=techs,
            decisions=decs,
            problems_and_solutions=probs,
            todos=todos,
            updated_at=r["updated_at"]
        )

    # =========================================================================
    # STATS & TELEMETRY
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        conn = self._get_connection()
        c = conn.cursor()

        c.execute("SELECT count(*) as total FROM memories WHERE status != 'deleted'")
        total = c.fetchone()["total"]

        c.execute("SELECT memory_type, count(*) as count FROM memories WHERE status != 'deleted' GROUP BY memory_type")
        tier_counts = {r["memory_type"]: r["count"] for r in c.fetchall()}

        c.execute("SELECT status, count(*) as count FROM memories GROUP BY status")
        status_counts = {r["status"]: r["count"] for r in c.fetchall()}

        c.execute("SELECT count(*) as count FROM memory_relationships")
        rel_count = c.fetchone()["count"]

        c.execute("SELECT count(*) as count FROM memory_knowledge_nodes")
        knode_count = c.fetchone()["count"]

        db_size_kb = 0
        if os.path.exists(self.db_path):
            db_size_kb = round(os.path.getsize(self.db_path) / 1024, 2)

        conn.close()

        return {
            "total_memories": total,
            "tier_distribution": tier_counts,
            "status_distribution": status_counts,
            "relationships_count": rel_count,
            "knowledge_nodes_count": knode_count,
            "db_size_kb": db_size_kb,
            "db_path": self.db_path
        }

    # =========================================================================
    # HELPER MAPPINGS
    # =========================================================================

    def _row_to_node(self, r: sqlite3.Row) -> MemoryNode:
        try:
            tags = json.loads(r["tags_json"]) if r["tags_json"] else []
        except Exception:
            tags = []

        try:
            meta = json.loads(r["metadata_json"]) if r["metadata_json"] else {}
        except Exception:
            meta = {}

        return MemoryNode(
            id=r["id"],
            content=r["content"],
            memory_type=r["memory_type"],
            category=r["category"],
            importance=float(r["importance"]),
            confidence=float(r["confidence"]),
            created_at=float(r["created_at"]),
            last_accessed=float(r["last_accessed"]),
            access_count=int(r["access_count"]),
            source=r["source"],
            status=r["status"],
            pinned=bool(r["pinned"]),
            tags=tags,
            project_id=r["project_id"],
            metadata=meta,
            embedding=r["embedding"]
        )
