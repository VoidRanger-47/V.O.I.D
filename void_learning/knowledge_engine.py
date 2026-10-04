# void_learning/knowledge_engine.py
"""
Central Knowledge Engine for V.O.I.D.
Manages:
- Knowledge Sandbox States: RAW -> ANALYZED -> UNVERIFIED -> VERIFIED -> OUTDATED -> CONFLICTED -> REJECTED
- Persistent SQLite table `void_learned_knowledge` in `void_memory/void_memory.db`
- Knowledge Graph synchronization (Entities & Relationships)
- Temporal Freshness Checking (FRESHNESS_POLICY)
- Source Traceability ("Where did you learn this?")
- Continuous & Autonomous Learning Modes (AUTO_LEARNING = False by default)
"""

import os
import json
import time
import uuid
import sqlite3
from typing import Dict, Any, List, Optional
from datetime import datetime

from void_learning.research_agent import WebResearchAgent
from void_learning.source_quality import evaluate_source_quality
from void_memory.memory_manager import MemoryManager


# Temporal Freshness Policies (in days)
FRESHNESS_POLICY: Dict[str, Optional[int]] = {
    "current_events": 1,       # 1 day
    "cybersecurity": 7,        # 7 days
    "software": 30,            # 30 days
    "hardware": 90,            # 90 days
    "scientific_research": 180,# 180 days
    "general_knowledge": None  # No expiration for timeless facts (math, basic physics)
}


class KnowledgeStatus:
    RAW = "RAW"
    ANALYZED = "ANALYZED"
    UNVERIFIED = "UNVERIFIED"
    VERIFIED = "VERIFIED"
    OUTDATED = "OUTDATED"
    CONFLICTED = "CONFLICTED"
    REJECTED = "REJECTED"


class KnowledgeEngine:
    """
    Coordinates V.O.I.D.'s structured knowledge core, storage, and retrieval.
    """

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        self.researcher = WebResearchAgent()
        self.auto_learning_enabled = False  # Strictly False by default
        self._init_db()

    def _get_conn(self) -> sqlite3.Connection:
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Creates the learned knowledge table and indices."""
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('''
            CREATE TABLE IF NOT EXISTS void_learned_knowledge (
                knowledge_id TEXT PRIMARY KEY,
                topic TEXT NOT NULL,
                subject TEXT NOT NULL,
                concept TEXT NOT NULL,
                fact TEXT NOT NULL,
                source TEXT NOT NULL,
                source_url TEXT,
                source_type TEXT DEFAULT 'general_webpage',
                confidence REAL DEFAULT 0.85,
                status TEXT DEFAULT 'VERIFIED',
                category TEXT DEFAULT 'software',
                learned_at REAL NOT NULL,
                last_verified REAL NOT NULL,
                verification_count INTEGER DEFAULT 1,
                version INTEGER DEFAULT 1,
                metadata_json TEXT DEFAULT '{}'
            )
        ''')

        c.execute('CREATE INDEX IF NOT EXISTS idx_vlk_topic ON void_learned_knowledge(topic)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_vlk_status ON void_learned_knowledge(status)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_vlk_learned ON void_learned_knowledge(learned_at)')

        # Virtual table for instant text search
        try:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS void_knowledge_fts USING fts5(
                    knowledge_id UNINDEXED,
                    topic,
                    concept,
                    fact
                )
            ''')
        except Exception:
            pass

        conn.commit()
        conn.close()

    # ==========================================
    # 📚 LEARNING PIPELINE API
    # ==========================================

    def learn(self, topic: str) -> Dict[str, Any]:
        """
        Full continuous learning pipeline:
        Research -> Collect sources -> Clean & Extract -> Verify -> Graph Link -> Store -> Report
        """
        clean_topic = topic.strip()
        if not clean_topic:
            return {"status": "error", "message": "Topic cannot be empty"}

        # 1. Execute Web Research
        research_result = self.researcher.research(clean_topic, max_sources=5, scrape_full_content=True)

        if research_result.get("offline"):
            return {
                "status": "offline",
                "topic": clean_topic,
                "message": research_result.get("research_summary")
            }

        facts = research_result.get("facts", [])
        triples = research_result.get("triples", [])
        sources = research_result.get("sources", [])
        conflicts = research_result.get("conflicts", [])
        overall_confidence = research_result.get("confidence", 0.85)

        if not facts and not sources:
            return {
                "status": "not_found",
                "topic": clean_topic,
                "message": f"Could not find sufficient credible information online for '{clean_topic}'."
            }

        now = time.time()
        stored_records_count = 0
        verified_count = 0
        conflicted_count = len(conflicts)

        conn = self._get_conn()
        c = conn.cursor()

        # Determine knowledge category for freshness policy
        category = self._categorize_topic(clean_topic)

        # 2. Store extracted facts in SQLite Knowledge Core
        for f in facts:
            fact_text = f.get("fact", "").strip()
            if not fact_text:
                continue

            # Check if this exact fact or concept already exists
            c.execute('SELECT knowledge_id, confidence, verification_count FROM void_learned_knowledge WHERE fact = ?', (fact_text,))
            existing = c.fetchone()

            if existing:
                # Update existing record with higher verification count
                new_vcount = existing["verification_count"] + 1
                new_conf = min(0.99, existing["confidence"] + 0.02)
                c.execute('''
                    UPDATE void_learned_knowledge
                    SET last_verified = ?, verification_count = ?, confidence = ?
                    WHERE knowledge_id = ?
                ''', (now, new_vcount, new_conf, existing["knowledge_id"]))
                verified_count += 1
            else:
                k_id = f"k_{uuid.uuid4().hex[:10]}"
                status = KnowledgeStatus.CONFLICTED if any(f.get("concept", "").lower() in str(conf).lower() for conf in conflicts) else KnowledgeStatus.VERIFIED

                c.execute('''
                    INSERT INTO void_learned_knowledge (
                        knowledge_id, topic, subject, concept, fact, source, source_url,
                        source_type, confidence, status, category, learned_at, last_verified,
                        verification_count, version, metadata_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    k_id,
                    clean_topic,
                    f.get("subject", clean_topic),
                    f.get("concept", clean_topic),
                    fact_text,
                    f.get("source", "web"),
                    f.get("source_url", ""),
                    f.get("source_type", "web"),
                    f.get("confidence", overall_confidence),
                    status,
                    category,
                    now,
                    now,
                    1,
                    1,
                    json.dumps({"tier": f.get("tier", "Tier 3")})
                ))

                try:
                    c.execute('''
                        INSERT INTO void_knowledge_fts(knowledge_id, topic, concept, fact)
                        VALUES (?, ?, ?, ?)
                    ''', (k_id, clean_topic, f.get("concept", clean_topic), fact_text))
                except Exception:
                    pass

                stored_records_count += 1
                if status == KnowledgeStatus.VERIFIED:
                    verified_count += 1

        conn.commit()
        conn.close()

        # 3. Connect with Local Knowledge Graph
        graph_links_created = 0
        try:
            from void_memory.memory_manager import MemoryManager
            mem_mgr = MemoryManager(db_path=self.db_path)
            kg = mem_mgr.knowledge_graph

            # Ensure central topic node exists
            kg.add_concept(name=clean_topic, node_type="technology" if category == "software" else "concept", description=f"Learned domain: {clean_topic}")

            for t in triples[:15]:
                sub = t.get("source", clean_topic)
                rel = t.get("relationship", "related_to")
                obj = t.get("target", "")
                if sub and obj:
                    kg.add_concept(name=obj, node_type="concept")
                    if kg.link_entities(sub, obj, relationship=rel, weight=t.get("weight", 1.0)):
                        graph_links_created += 1
        except Exception as e:
            print(f"[KnowledgeEngine] Graph link notice: {e}")

        # 4. Return structured learning report matching Requirement 8
        return {
            "status": "success",
            "topic": clean_topic,
            "sources_analyzed": len(sources),
            "useful_facts": len(facts),
            "verified_facts": verified_count,
            "conflicting_claims": conflicted_count,
            "new_knowledge_records": stored_records_count,
            "knowledge_graph_relationships": graph_links_created,
            "confidence_percent": int(overall_confidence * 100),
            "sources": sources,
            "conflicts": conflicts,
            "summary_text": (
                f"VOID Research completed.\n\n"
                f"Topic: {clean_topic}\n"
                f"Sources analyzed: {len(sources)}\n"
                f"Useful facts: {len(facts)}\n"
                f"Verified facts: {verified_count}\n"
                f"Conflicting claims: {conflicted_count}\n"
                f"New knowledge records: {stored_records_count}\n"
                f"Knowledge graph relationships: {graph_links_created}\n"
                f"Confidence: {int(overall_confidence * 100)}%\n\n"
                f"Knowledge stored locally in SQLite & Knowledge Graph."
            )
        }

    # ==========================================
    # 🔍 SEMANTIC RETRIEVAL & SOURCE TRACEABILITY
    # ==========================================

    def retrieve(self, query: str, limit: int = 4) -> List[Dict[str, Any]]:
        """
        Retrieves matching local knowledge records and checks their freshness.
        """
        clean_q = (query or "").strip()
        if not clean_q:
            return []

        conn = self._get_conn()
        c = conn.cursor()

        records = []
        now = time.time()

        # Try FTS first
        try:
            c.execute('''
                SELECT k.* FROM void_learned_knowledge k
                JOIN void_knowledge_fts fts ON k.knowledge_id = fts.knowledge_id
                WHERE void_knowledge_fts MATCH ?
                LIMIT ?
            ''', (clean_q, limit))
            records = [dict(r) for r in c.fetchall()]
        except Exception:
            records = []

        # Fallback to LIKE query
        if not records:
            c.execute('''
                SELECT * FROM void_learned_knowledge
                WHERE topic LIKE ? OR concept LIKE ? OR fact LIKE ?
                ORDER BY confidence DESC, verification_count DESC
                LIMIT ?
            ''', (f"%{clean_q}%", f"%{clean_q}%", f"%{clean_q}%", limit))
            records = [dict(r) for r in c.fetchall()]

        conn.close()

        # Apply Freshness Evaluation
        for r in records:
            category = r.get("category", "general_knowledge")
            max_days = FRESHNESS_POLICY.get(category)
            if max_days is not None:
                age_days = (now - r["learned_at"]) / (24 * 3600)
                if age_days > max_days:
                    r["is_outdated"] = True
                    r["status"] = KnowledgeStatus.OUTDATED
                else:
                    r["is_outdated"] = False
            else:
                r["is_outdated"] = False

        return records

    def get_sources(self, topic_or_id: str) -> Dict[str, Any]:
        """
        Requirement 11 Source Traceability: Answers "Where did you learn this?"
        """
        clean_target = topic_or_id.strip()
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('''
            SELECT * FROM void_learned_knowledge
            WHERE knowledge_id = ? OR topic LIKE ? OR concept LIKE ?
            ORDER BY confidence DESC
            LIMIT 6
        ''', (clean_target, f"%{clean_target}%", f"%{clean_target}%"))
        rows = [dict(r) for r in c.fetchall()]
        conn.close()

        if not rows:
            return {
                "found": False,
                "message": f"No learned source records found for '{clean_target}'."
            }

        first = rows[0]
        unique_sources = list(set(r["source"] for r in rows if r.get("source")))
        urls = [r["source_url"] for r in rows if r.get("source_url")]
        learned_dt = datetime.fromtimestamp(first["learned_at"]).strftime("%Y-%m-%d %H:%M:%S")

        formatted_report = (
            f"Source Traceability for '{first['topic']}':\n"
            f"• Source(s): {', '.join(unique_sources)}\n"
            f"• URLs: {', '.join(urls[:3]) if urls else 'Locally recorded'}\n"
            f"• Retrieved: {learned_dt}\n"
            f"• Verification: {len(unique_sources)} independent sources ({first['verification_count']} confirmations)\n"
            f"• Confidence: {int(first['confidence'] * 100)}%\n"
            f"• Status: {first['status']}"
        )

        return {
            "found": True,
            "topic": first["topic"],
            "sources": unique_sources,
            "urls": urls,
            "retrieved_at": learned_dt,
            "verification_count": first["verification_count"],
            "confidence": first["confidence"],
            "report_text": formatted_report,
            "records": rows
        }

    def forget_knowledge(self, topic: str) -> Dict[str, Any]:
        """
        Requirement 19: Removes learned knowledge about a topic.
        """
        clean_t = topic.strip()
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('DELETE FROM void_learned_knowledge WHERE topic LIKE ? OR concept LIKE ?', (f"%{clean_t}%", f"%{clean_t}%"))
        deleted_count = c.rowcount

        try:
            c.execute('DELETE FROM void_knowledge_fts WHERE topic LIKE ? OR concept LIKE ?', (f"%{clean_t}%", f"%{clean_t}%"))
        except Exception:
            pass

        conn.commit()
        conn.close()

        return {
            "status": "success",
            "topic": clean_t,
            "deleted_records": deleted_count,
            "message": f"Deleted {deleted_count} knowledge records related to '{clean_t}'."
        }

    # ==========================================
    # 📊 TELEMETRY & DASHBOARD METRICS
    # ==========================================

    def get_dashboard_stats(self) -> Dict[str, Any]:
        """
        Provides metrics for the Learning Dashboard in Requirement 20.
        """
        conn = self._get_conn()
        c = conn.cursor()

        c.execute('SELECT COUNT(*) FROM void_learned_knowledge')
        total_records = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM void_learned_knowledge WHERE status = "VERIFIED"')
        verified_records = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM void_learned_knowledge WHERE status = "UNVERIFIED" OR status = "RAW"')
        pending_records = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM void_learned_knowledge WHERE status = "OUTDATED"')
        outdated_records = c.fetchone()[0]

        c.execute('SELECT COUNT(*) FROM void_learned_knowledge WHERE status = "CONFLICTED"')
        conflicted_records = c.fetchone()[0]

        # Recent topics learned
        c.execute('''
            SELECT topic, COUNT(*) as fact_count, MAX(learned_at) as recent_time, AVG(confidence) as avg_conf
            FROM void_learned_knowledge
            GROUP BY topic
            ORDER BY recent_time DESC
            LIMIT 6
        ''')
        recent_topics = [
            {
                "topic": r["topic"],
                "facts": r["fact_count"],
                "time": datetime.fromtimestamp(r["recent_time"]).strftime("%Y-%m-%d %H:%M"),
                "confidence": int(r["avg_conf"] * 100)
            }
            for r in c.fetchall()
        ]

        # Sources summary
        c.execute('SELECT COUNT(DISTINCT source) FROM void_learned_knowledge')
        unique_sources = c.fetchone()[0]

        conn.close()

        return {
            "total_records": total_records,
            "verified_records": verified_records,
            "pending_records": pending_records,
            "outdated_records": outdated_records,
            "conflicted_records": conflicted_records,
            "unique_sources": unique_sources,
            "recent_topics": recent_topics,
            "auto_learning": self.auto_learning_enabled
        }

    def toggle_auto_learning(self, enabled: Optional[bool] = None) -> bool:
        """Toggles autonomous learning mode (Requirement 9)."""
        if enabled is not None:
            self.auto_learning_enabled = bool(enabled)
        else:
            self.auto_learning_enabled = not self.auto_learning_enabled
        return self.auto_learning_enabled

    def _categorize_topic(self, topic: str) -> str:
        low = topic.lower()
        if any(k in low for k in ["vulnerability", "cve", "exploit", "security", "firewall", "malware"]):
            return "cybersecurity"
        if any(k in low for k in ["news", "today", "yesterday", "current", "president", "war", "election"]):
            return "current_events"
        if any(k in low for k in ["gpu", "cpu", "ram", "rtx", "intel", "amd", "display", "monitor", "motherboard"]):
            return "hardware"
        if any(k in low for k in ["python", "c++", "vulkan", "api", "framework", "library", "git", "linux", "compiler"]):
            return "software"
        if any(k in low for k in ["physics", "math", "calculus", "geometry", "biology"]):
            return "general_knowledge"
        return "software"


# Singleton instance
knowledge_engine = KnowledgeEngine()
