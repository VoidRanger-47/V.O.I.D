# void_memory/skill_persistence.py
"""
V.O.I.D. Autonomous Evolution & Adaptive Skill Persistence Engine
Parses, indexes, and retrieves structured procedural skills from model outputs.
Enables continuous self-improvement and deterministic workflow retention.
"""

import os
import re
import json
import sqlite3
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

PROCEDURAL_TIER = "procedural"


@dataclass
class SkillMemoryEntry:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    domain: str = ""
    trigger_keywords: List[str] = field(default_factory=list)
    core_tooling: List[str] = field(default_factory=list)
    validated_workflow: str = ""
    failure_modes: List[str] = field(default_factory=list)
    verification_status: str = "Verified (>90% confidence)"
    raw_block: str = ""
    created_at: float = field(default_factory=time.time)


class SkillPersistenceManager:
    """
    Manages parsing and SQLite persistence for V.O.I.D. autonomous memory entries.
    Provides fast keyword-indexed and full-text retrieval for dynamic context injection.
    """

    MEMORY_ENTRY_REGEX = re.compile(
        r"```memory_entry\s*?\n(.*?)```",
        re.DOTALL | re.IGNORECASE
    )

    def __init__(self, db_path: str = "void_memory/void_memory.db"):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def _init_db(self):
        """Creates the autonomous_skills table and FTS index if not present."""
        conn = self._get_connection()
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS autonomous_skills (
                id TEXT PRIMARY KEY,
                domain TEXT NOT NULL,
                trigger_keywords_json TEXT NOT NULL,
                core_tooling_json TEXT NOT NULL,
                validated_workflow TEXT NOT NULL,
                failure_modes_json TEXT NOT NULL,
                verification_status TEXT NOT NULL,
                raw_block TEXT NOT NULL,
                created_at REAL NOT NULL,
                usage_count INTEGER DEFAULT 0
            )
        ''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_skills_domain ON autonomous_skills(domain)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_skills_created ON autonomous_skills(created_at)')

        # Virtual Full-Text Search Table for instantaneous semantic/keyword retrieval
        try:
            c.execute('''
                CREATE VIRTUAL TABLE IF NOT EXISTS autonomous_skills_fts USING fts5(
                    id UNINDEXED,
                    domain,
                    trigger_keywords_json,
                    core_tooling_json,
                    validated_workflow
                )
            ''')
            # Triggers to keep FTS table synchronized
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_auto_skills_ai AFTER INSERT ON autonomous_skills BEGIN
                    INSERT INTO autonomous_skills_fts(id, domain, trigger_keywords_json, core_tooling_json, validated_workflow)
                    VALUES (new.id, new.domain, new.trigger_keywords_json, new.core_tooling_json, new.validated_workflow);
                END;
            ''')
            c.execute('''
                CREATE TRIGGER IF NOT EXISTS trg_auto_skills_ad AFTER DELETE ON autonomous_skills BEGIN
                    DELETE FROM autonomous_skills_fts WHERE id = old.id;
                END;
            ''')
        except sqlite3.OperationalError:
            pass  # FTS5 already exists or module handled

        conn.commit()
        conn.close()

    def parse_memory_entry(self, text: str) -> Optional[SkillMemoryEntry]:
        """
        Extracts and parses a ```memory_entry block from text.
        """
        match = self.MEMORY_ENTRY_REGEX.search(text)
        if not match:
            return None

        content = match.group(1).strip()
        lines = content.splitlines()

        domain = "General"
        keywords: List[str] = []
        tooling: List[str] = []
        workflow_lines: List[str] = []
        failure_modes: List[str] = []
        verification = "Verified (>90% confidence)"

        current_section = None

        for line in lines:
            line_str = line.strip()
            if not line_str or line_str.startswith("[NEW_SKILL_PERSISTENCE]"):
                continue

            if line_str.lower().startswith("domain:"):
                domain = line_str.split(":", 1)[1].strip()
                current_section = None
            elif line_str.lower().startswith("trigger keywords:"):
                kw_str = line_str.split(":", 1)[1].strip()
                keywords = [k.strip() for k in kw_str.split(",") if k.strip()]
                current_section = "keywords"
            elif line_str.lower().startswith("core tooling:"):
                t_str = line_str.split(":", 1)[1].strip()
                tooling = [t.strip() for t in t_str.split(",") if t.strip()]
                current_section = "tooling"
            elif line_str.lower().startswith("validated workflow:"):
                current_section = "workflow"
            elif line_str.lower().startswith("failure modes & caveats:"):
                current_section = "failure_modes"
            elif line_str.lower().startswith("verification status:"):
                verification = line_str.split(":", 1)[1].strip()
                current_section = None
            else:
                if current_section == "workflow":
                    workflow_lines.append(line)
                elif current_section == "failure_modes":
                    failure_modes.append(line_str.lstrip("- *").strip())
                elif current_section == "keywords":
                    keywords.extend([k.strip() for k in line_str.split(",") if k.strip()])
                elif current_section == "tooling":
                    tooling.extend([t.strip() for t in line_str.split(",") if t.strip()])

        return SkillMemoryEntry(
            domain=domain,
            trigger_keywords=keywords,
            core_tooling=tooling,
            validated_workflow="\n".join(workflow_lines).strip(),
            failure_modes=failure_modes,
            verification_status=verification,
            raw_block=content
        )

    def save_skill(self, entry: SkillMemoryEntry) -> str:
        """
        Saves a skill into the autonomous_skills table and syncs to the 8-tier memory system.
        """
        conn = self._get_connection()
        c = conn.cursor()

        # Check for duplicate domain/workflow to prevent redundant bloat
        c.execute("SELECT id FROM autonomous_skills WHERE domain = ? AND validated_workflow = ?",
                  (entry.domain, entry.validated_workflow))
        existing = c.fetchone()
        if existing:
            c.execute("UPDATE autonomous_skills SET usage_count = usage_count + 1 WHERE id = ?", (existing[0],))
            conn.commit()
            conn.close()
            return existing[0]

        skill_id = entry.id or str(uuid.uuid4())
        c.execute('''
            INSERT INTO autonomous_skills (
                id, domain, trigger_keywords_json, core_tooling_json,
                validated_workflow, failure_modes_json, verification_status,
                raw_block, created_at, usage_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        ''', (
            skill_id,
            entry.domain,
            json.dumps(entry.trigger_keywords),
            json.dumps(entry.core_tooling),
            entry.validated_workflow,
            json.dumps(entry.failure_modes),
            entry.verification_status,
            entry.raw_block,
            entry.created_at
        ))

        # Also register in primary 8-tier memories table under PROCEDURAL tier
        try:
            procedural_content = f"SKILL [{entry.domain}]: {entry.validated_workflow}"
            c.execute('''
                INSERT OR IGNORE INTO memories (
                    id, content, memory_type, category, importance, confidence,
                    created_at, last_accessed, access_count, source, status, tags_json, metadata_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 'autonomous_learner', 'active', ?, ?)
            ''', (
                skill_id,
                procedural_content,
                PROCEDURAL_TIER,
                entry.domain.lower(),
                0.95,
                0.98,
                entry.created_at,
                entry.created_at,
                json.dumps(entry.trigger_keywords),
                json.dumps({
                    "core_tooling": entry.core_tooling,
                    "failure_modes": entry.failure_modes,
                    "verification": entry.verification_status
                })
            ))
        except Exception:
            pass  # Fallback if primary table not loaded

        conn.commit()
        conn.close()
        return skill_id

    def process_model_output(self, response_text: str) -> Optional[SkillMemoryEntry]:
        """
        Inspects model response, extracts any memory_entry block, and persists it.
        """
        entry = self.parse_memory_entry(response_text)
        if entry:
            self.save_skill(entry)
            return entry
        return None

    def find_relevant_skills(self, query: str, limit: int = 3) -> List[SkillMemoryEntry]:
        """
        Finds validated skills matching the incoming user query keywords or semantics.
        """
        conn = self._get_connection()
        c = conn.cursor()
        results: List[SkillMemoryEntry] = []

        query_tokens = [t.lower().strip() for t in re.findall(r"\w+", query) if len(t) > 2]
        if not query_tokens:
            conn.close()
            return []

        # 1. Direct FTS Match
        fts_query = " OR ".join(f'"{t}"*' for t in query_tokens[:6])
        try:
            c.execute('''
                SELECT s.* FROM autonomous_skills s
                JOIN autonomous_skills_fts f ON s.id = f.id
                WHERE autonomous_skills_fts MATCH ?
                ORDER BY rank
                LIMIT ?
            ''', (fts_query, limit))
            rows = c.fetchall()
            for r in rows:
                results.append(self._row_to_entry(r))
        except Exception:
            pass

        # 2. Keyword fallback if FTS yields nothing
        if not results:
            c.execute('SELECT * FROM autonomous_skills ORDER BY usage_count DESC, created_at DESC LIMIT 50')
            rows = c.fetchall()
            for r in rows:
                kw_list = json.loads(r["trigger_keywords_json"])
                domain = r["domain"].lower()
                matches = sum(1 for q in query_tokens if any(q in kw.lower() for kw in kw_list) or q in domain)
                if matches > 0:
                    results.append(self._row_to_entry(r))
                    if len(results) >= limit:
                        break

        conn.close()
        return results

    def _row_to_entry(self, r: sqlite3.Row) -> SkillMemoryEntry:
        return SkillMemoryEntry(
            id=r["id"],
            domain=r["domain"],
            trigger_keywords=json.loads(r["trigger_keywords_json"]),
            core_tooling=json.loads(r["core_tooling_json"]),
            validated_workflow=r["validated_workflow"],
            failure_modes=json.loads(r["failure_modes_json"]),
            verification_status=r["verification_status"],
            raw_block=r["raw_block"],
            created_at=r["created_at"]
        )

    def build_skill_injection_context(self, query: str) -> str:
        """
        Generates context injection block to place in system prompt if relevant skill is detected.
        """
        matched = self.find_relevant_skills(query)
        if not matched:
            return ""

        sections = []
        for s in matched:
            sections.append(
                f"[PREVIOUSLY VERIFIED SKILL - {s.domain.upper()}]\n"
                f"Core Tooling: {', '.join(s.core_tooling)}\n"
                f"Validated Workflow:\n{s.validated_workflow}\n"
                f"Known Failure Modes:\n" + "\n".join(f"- {f}" for f in s.failure_modes)
            )

        return (
            "=== V.O.I.D. VERIFIED PROCEDURAL SKILLS (AUTONOMOUS MEMORY) ===\n"
            + "\n\n".join(sections)
            + "\n============================================================\n"
        )


# Global Singleton Instance (Lazy)
_skill_persistence_instance: Optional[SkillPersistenceManager] = None


def get_skill_persistence() -> SkillPersistenceManager:
    global _skill_persistence_instance
    if _skill_persistence_instance is None:
        _skill_persistence_instance = SkillPersistenceManager()
    return _skill_persistence_instance


class _SkillPersistenceProxy:
    def __getattr__(self, name: str):
        return getattr(get_skill_persistence(), name)


skill_persistence = _SkillPersistenceProxy()
