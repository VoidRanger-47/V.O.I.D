"""
core/project_awareness.py
Codebase Structure & Architectural Awareness Engine for V.O.I.D.
Provides real-time directory tree mapping, file analytics, symbol indexing,
and architecture descriptions to give V.O.I.D. deep workspace intelligence.
"""

import ast
import os
import time
from typing import Dict, Any, List, Optional


class ProjectAwarenessEngine:
    """
    Scans and indexes the local project codebase.
    Enables V.O.I.D. to understand file hierarchies, module relationships,
    exported symbols, and technology stacks.
    """
    _instance: Optional['ProjectAwarenessEngine'] = None

    IGNORE_DIRS = {
        ".git", "__pycache__", "node_modules", "venv", ".venv",
        ".void_desktop_profile", ".vscode", "artifacts", "dist", "build"
    }

    MODULE_ROLES = {
        "core": "Multi-Agent Coordinator, Security Sandbox, State Manager, Missions & Event Bus",
        "core/agents": "Specialized Agents: Planner, Researcher, Coder, Executive, Verifier, Reflection",
        "skills": "Neuro-Symbolic Tool Handlers (Math, Coding AST, Computer Control, NLP, Web, Phone ADB)",
        "void_memory": "6-Tier Persistent SQLite & Vector Long-Term Memory System",
        "void_phone": "Android ADB Intent Parser, Phone Automation & Bridge",
        "templates": "Jinja2 HTML Frontend Views (chat.html)",
        "static": "Client UI Styling (chat.css), JS Runtime (chat.js), PWA Manifest",
        "training": "Custom Dataset Corpus (JSONL & Raw Text) for Neural Model Training",
        "app.py": "Flask REST API Gateway & Server-Sent Events (SSE) Token Streaming Server",
        "chat.py": "CLI Entrypoint, Intent Skill Router & Generation Pipeline",
        "from_scratch_transformer.py": "103M Parameter PyTorch Decoder Transformer Neural Network"
    }

    def __init__(self, workspace_root: Optional[str] = None):
        self.root = workspace_root or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._cached_summary: Optional[Dict[str, Any]] = None
        self._cached_tree: Optional[Dict[str, Any]] = None
        self._last_scan_time: float = 0.0

    @classmethod
    def get_instance(cls) -> 'ProjectAwarenessEngine':
        if cls._instance is None:
            cls._instance = ProjectAwarenessEngine()
        return cls._instance

    def scan_structure(self, force: bool = False) -> Dict[str, Any]:
        """
        Scans workspace and returns a comprehensive structure analysis.
        """
        if self._cached_summary and not force and (time.time() - self._last_scan_time < 30):
            return self._cached_summary

        file_counts: Dict[str, int] = {}
        file_sizes: Dict[str, int] = {}
        total_files = 0
        total_bytes = 0
        python_files = []
        modules = []

        for root, dirs, files in os.walk(self.root):
            dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS]
            rel_dir = os.path.relpath(root, self.root)
            if rel_dir != ".":
                modules.append(rel_dir.replace("\\", "/"))

            for f in files:
                ext = os.path.splitext(f)[1].lower() or "other"
                file_counts[ext] = file_counts.get(ext, 0) + 1
                full_path = os.path.join(root, f)
                try:
                    size = os.path.getsize(full_path)
                except Exception:
                    size = 0
                file_sizes[ext] = file_sizes.get(ext, 0) + size
                total_files += 1
                total_bytes += size

                if ext == ".py":
                    python_files.append(os.path.relpath(full_path, self.root).replace("\\", "/"))

        # Scan python symbols
        symbols_count = {"classes": 0, "functions": 0}
        for py_rel in python_files:
            abs_py = os.path.join(self.root, py_rel)
            try:
                with open(abs_py, "r", encoding="utf-8", errors="replace") as pf:
                    tree = ast.parse(pf.read(), filename=py_rel)
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        symbols_count["classes"] += 1
                    elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols_count["functions"] += 1
            except Exception:
                continue

        summary = {
            "project_name": "V.O.I.D.",
            "workspace_path": self.root,
            "total_files": total_files,
            "total_size_mb": round(total_bytes / (1024 * 1024), 2),
            "file_counts": file_counts,
            "file_sizes_kb": {k: round(v / 1024, 1) for k, v in file_sizes.items()},
            "python_files_count": len(python_files),
            "symbols_count": symbols_count,
            "modules": sorted(list(set(modules))),
            "module_roles": self.MODULE_ROLES,
            "scanned_at": time.time()
        }

        self._cached_summary = summary
        self._last_scan_time = time.time()
        return summary

    def get_file_tree(self, max_depth: int = 3) -> Dict[str, Any]:
        """
        Builds a nested JSON tree of files and directories.
        """
        def build_node(current_path: str, depth: int) -> Dict[str, Any]:
            name = os.path.basename(current_path) or "VOID_ROOT"
            is_dir = os.path.isdir(current_path)

            node: Dict[str, Any] = {
                "name": name,
                "path": os.path.relpath(current_path, self.root).replace("\\", "/"),
                "is_dir": is_dir
            }

            if not is_dir:
                ext = os.path.splitext(name)[1].lower()
                node["ext"] = ext
                try:
                    node["size_kb"] = round(os.path.getsize(current_path) / 1024, 1)
                except Exception:
                    node["size_kb"] = 0
                return node

            if depth >= max_depth:
                node["children"] = []
                return node

            children = []
            try:
                entries = sorted(os.listdir(current_path))
                for entry in entries:
                    if entry in self.IGNORE_DIRS:
                        continue
                    child_path = os.path.join(current_path, entry)
                    children.append(build_node(child_path, depth + 1))
            except Exception:
                pass

            node["children"] = children
            return node

        return build_node(self.root, 0)

    def generate_context_prompt(self, query: str = "") -> str:
        """
        Generates a concise markdown architectural overview for LLM context injection.
        """
        summary = self.scan_structure()
        text = [
            "### [Codebase Architecture & Project Awareness Context]",
            f"**Project**: {summary['project_name']} (Total files: {summary['total_files']}, Size: {summary['total_size_mb']} MB)",
            f"**Python Symbols**: {summary['symbols_count']['classes']} Classes, {summary['symbols_count']['functions']} Functions across {summary['python_files_count']} Python modules.",
            "**Core Modules & Roles**:"
        ]
        for mod, role in self.MODULE_ROLES.items():
            text.append(f"- `{mod}`: {role}")
        return "\n".join(text)


project_awareness = ProjectAwarenessEngine.get_instance()
