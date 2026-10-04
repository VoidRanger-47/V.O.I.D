# void_memory/project_memory.py
"""
Project Memory Manager for V.O.I.D.
Maintains persistent architecture documentation, technology inventories,
decision logs, problem-solution histories, and TODO lists for local projects.
"""

import time
from typing import List, Dict, Any, Optional

from void_memory.database.models import ProjectMemoryRecord, MemoryNode, MemoryTier
from void_memory.database.repository import MemoryRepository


class ProjectMemoryManager:
    """
    Manages long-term project context and engineering knowledge.
    """

    def __init__(self, repo: MemoryRepository, project_id: str = "VOID"):
        self.repo = repo
        self.project_id = project_id
        self._ensure_project_initialized()

    def _ensure_project_initialized(self):
        rec = self.repo.get_project_record(self.project_id)
        if not rec:
            initial = ProjectMemoryRecord(
                project_id=self.project_id,
                name="V.O.I.D.",
                path=r"c:\Users\kbven\OneDrive\Documents\VOID",
                architecture="Offline-first multi-tier neural assistant operating layer with local LLM, TTS, STT, and Multi-Agent Network.",
                technologies=["Python", "PyTorch", "SQLite", "Flask", "Electron", "Faster-Whisper", "Piper", "SentenceTransformers"],
                decisions=[
                    {"title": "Offline Guarantee", "rationale": "Zero external internet dependencies for core model inference and memory.", "timestamp": time.time()},
                    {"title": "Multi-Tier Memory", "rationale": "Organize memories into Working, Episodic, Semantic, Preference, Project, and Procedural tiers.", "timestamp": time.time()}
                ],
                problems_and_solutions=[
                    {
                        "problem": "Token streaming aborted unexpectedly",
                        "cause": "Missing frontend artifact method and CRLF SSE parsing on Windows",
                        "solution": "Implemented missing artifact handlers in chat.js and robust SSE reader with internal generator error boundaries.",
                        "timestamp": time.time()
                    },
                    {
                        "problem": "Application launcher failing on social/Store apps",
                        "cause": "Hardcoded catalog and lack of UWP shell:AppsFolder/URI/Web fallbacks",
                        "solution": "Built UniversalAppRegistry scanning Start Menu, Registry, Get-StartApps, protocol URIs, and ADB package manager.",
                        "timestamp": time.time()
                    }
                ],
                todos=[],
                updated_at=time.time()
            )
            self.repo.save_project_record(initial)

    def get_project_record(self) -> ProjectMemoryRecord:
        rec = self.repo.get_project_record(self.project_id)
        if not rec:
            self._ensure_project_initialized()
            rec = self.repo.get_project_record(self.project_id)
        return rec  # type: ignore

    def record_decision(self, title: str, rationale: str) -> Dict[str, Any]:
        rec = self.get_project_record()
        decision_entry = {
            "id": len(rec.decisions) + 1,
            "title": title.strip(),
            "rationale": rationale.strip(),
            "timestamp": time.time()
        }
        rec.decisions.append(decision_entry)
        rec.updated_at = time.time()
        self.repo.save_project_record(rec)

        # Also mirror to semantic project memory
        self.repo.save_memory(MemoryNode(
            content=f"Project Decision: {title} — Rationale: {rationale}",
            memory_type=MemoryTier.PROJECT.value,
            category="technical_decision",
            importance=0.90,
            source="project_manager",
            project_id=self.project_id,
            tags=["decision", "architecture"]
        ))

        return decision_entry

    def record_problem_and_solution(self, problem: str, cause: str, solution: str) -> Dict[str, Any]:
        rec = self.get_project_record()
        entry = {
            "id": len(rec.problems_and_solutions) + 1,
            "problem": problem.strip(),
            "cause": cause.strip(),
            "solution": solution.strip(),
            "timestamp": time.time()
        }
        rec.problems_and_solutions.append(entry)
        rec.updated_at = time.time()
        self.repo.save_project_record(rec)

        # Also mirror to procedural memory
        self.repo.save_memory(MemoryNode(
            content=f"Troubleshooting Record: Problem: '{problem}' | Cause: '{cause}' | Solution: '{solution}'",
            memory_type=MemoryTier.PROCEDURAL.value,
            category="problem_solution",
            importance=0.85,
            source="project_manager",
            project_id=self.project_id,
            tags=["problem", "solution", "bug_fix"]
        ))

        return entry

    def add_todo(self, title: str, priority: str = "medium") -> Dict[str, Any]:
        rec = self.get_project_record()
        todo = {
            "id": len(rec.todos) + 1,
            "title": title.strip(),
            "priority": priority,
            "completed": False,
            "created_at": time.time()
        }
        rec.todos.append(todo)
        rec.updated_at = time.time()
        self.repo.save_project_record(rec)
        return todo

    def complete_todo(self, todo_id: int) -> bool:
        rec = self.get_project_record()
        for t in rec.todos:
            if t.get("id") == todo_id:
                t["completed"] = True
                t["completed_at"] = time.time()
                rec.updated_at = time.time()
                self.repo.save_project_record(rec)
                return True
        return False

    def get_project_summary(self) -> str:
        rec = self.get_project_record()
        lines = [
            f"Project: {rec.name}",
            f"Architecture: {rec.architecture}",
            f"Technologies: {', '.join(rec.technologies)}",
        ]
        if rec.decisions:
            lines.append("Key Decisions:")
            for d in rec.decisions[-3:]:
                lines.append(f"  • {d.get('title')}: {d.get('rationale')}")
        if rec.problems_and_solutions:
            lines.append("Recent Solutions:")
            for s in rec.problems_and_solutions[-2:]:
                lines.append(f"  • Problem: {s.get('problem')} -> Fixed: {s.get('solution')}")
        return "\n".join(lines)
