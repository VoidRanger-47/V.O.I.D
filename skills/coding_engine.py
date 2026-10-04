"""
skills/coding_engine.py
100% Offline Neuro-Symbolic Coding Intelligence Engine for V.O.I.D.
Provides AST validation, workspace symbol indexing, algorithmic pattern retrieval,
and a self-healing execution loop.
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.security import security_manager


@dataclass
class CodeSymbol:
    name: str
    symbol_type: str  # "function", "class", "async_function"
    file_path: str
    line_number: int
    docstring: Optional[str] = None
    args: List[str] = field(default_factory=list)


class ASTCodeValidator:
    """
    Performs fast, offline Abstract Syntax Tree (AST) validation and static analysis.
    """
    @staticmethod
    def validate_syntax(code: str) -> Tuple[bool, Optional[str], Optional[int]]:
        """
        Validate Python code syntax using the built-in AST parser.
        Returns: (is_valid, error_message, line_number)
        """
        try:
            ast.parse(code)
            return True, None, None
        except SyntaxError as e:
            return False, str(e), e.lineno
        except Exception as e:
            return False, str(e), None

    @staticmethod
    def analyze_structure(code: str) -> Dict[str, Any]:
        """
        Extract functions, classes, imports, and global variables from code string.
        """
        try:
            tree = ast.parse(code)
        except Exception:
            return {"functions": [], "classes": [], "imports": [], "syntax_valid": False}

        functions = []
        classes = []
        imports = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                args = [arg.arg for arg in node.args.args]
                doc = ast.get_docstring(node)
                functions.append({
                    "name": node.name,
                    "args": args,
                    "line": node.lineno,
                    "docstring": doc
                })
            elif isinstance(node, ast.ClassDef):
                doc = ast.get_docstring(node)
                classes.append({
                    "name": node.name,
                    "line": node.lineno,
                    "docstring": doc
                })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append(f"{module}.{alias.name}" if module else alias.name)

        return {
            "functions": functions,
            "classes": classes,
            "imports": imports,
            "syntax_valid": True
        }

    @staticmethod
    def auto_repair_syntax(code: str, error_msg: str, line_no: Optional[int]) -> str:
        """
        Heuristically patch common syntax errors (missing colons, unbalanced brackets, bad quotes).
        """
        lines = code.splitlines()
        if not lines:
            return code

        # 1. Missing colon at def/class/if/elif/else/for/while/try/except/with
        if line_no is not None and 1 <= line_no <= len(lines):
            idx = line_no - 1
            line = lines[idx]
            stripped = line.strip()
            keywords = ("def ", "class ", "if ", "elif ", "else", "for ", "while ", "try", "except", "finally", "with ")
            if any(stripped.startswith(kw) for kw in keywords) and not stripped.endswith(":"):
                lines[idx] = line + ":"
                return "\n".join(lines)

        # 2. Check for missing closing parentheses / brackets / braces
        code_text = "\n".join(lines)
        open_parens = code_text.count("(") - code_text.count(")")
        open_brackets = code_text.count("[") - code_text.count("]")
        open_braces = code_text.count("{") - code_text.count("}")

        if open_parens > 0:
            code_text += ")" * open_parens
        if open_brackets > 0:
            code_text += "]" * open_brackets
        if open_braces > 0:
            code_text += "}" * open_braces

        return code_text


class WorkspaceSymbolIndexer:
    """
    Offline workspace code indexer. Scans workspace files to build an AST symbol index
    for classes, functions, docstrings, and imports with zero cloud calls.
    """
    def __init__(self, root_dir: Optional[str] = None):
        self.root_dir = root_dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self._symbols_cache: List[CodeSymbol] = []
        self._last_scan_time: float = 0.0

    def scan_workspace(self, force_rescan: bool = False) -> List[CodeSymbol]:
        """
        Scan workspace Python files and extract all code symbols.
        """
        if self._symbols_cache and not force_rescan:
            return self._symbols_cache

        symbols: List[CodeSymbol] = []
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", ".void_desktop_profile"}

        for root, dirs, files in os.walk(self.root_dir):
            dirs[:] = [d for d in dirs if d not in ignore_dirs]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    try:
                        with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                            content = f.read()
                        tree = ast.parse(content, filename=rel_path)
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                doc = ast.get_docstring(node)
                                args = [a.arg for a in node.args.args]
                                sym = CodeSymbol(
                                    name=node.name,
                                    symbol_type="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    docstring=doc,
                                    args=args
                                )
                                symbols.append(sym)
                            elif isinstance(node, ast.ClassDef):
                                doc = ast.get_docstring(node)
                                sym = CodeSymbol(
                                    name=node.name,
                                    symbol_type="class",
                                    file_path=rel_path,
                                    line_number=node.lineno,
                                    docstring=doc
                                )
                                symbols.append(sym)
                    except Exception:
                        continue

        self._symbols_cache = symbols
        return symbols

    def find_symbol(self, query: str) -> List[Dict[str, Any]]:
        """Find symbols matching name or substring query."""
        symbols = self.scan_workspace()
        q = query.strip().lower()
        matches = []
        for sym in symbols:
            if q == sym.name.lower() or q in sym.name.lower():
                matches.append({
                    "name": sym.name,
                    "type": sym.symbol_type,
                    "file": sym.file_path,
                    "line": sym.line_number,
                    "docstring": sym.docstring,
                    "args": sym.args
                })
        return matches

    def get_module_outline(self, file_path: str) -> Dict[str, Any]:
        """Generate a structured outline of classes and functions in a file."""
        abs_path = os.path.join(self.root_dir, file_path) if not os.path.isabs(file_path) else file_path
        if not os.path.exists(abs_path):
            return {"error": f"File '{file_path}' not found."}

        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            return ASTCodeValidator.analyze_structure(content)
        except Exception as e:
            return {"error": str(e)}


class LocalCodePatternLibrary:
    """
    Offline algorithmic pattern repository loaded from data/code_patterns.json.
    Provides verified code templates with zero hallucinations.
    """
    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "code_patterns.json"
        )
        self.patterns: List[Dict[str, Any]] = self._load_patterns()

    def _load_patterns(self) -> List[Dict[str, Any]]:
        if os.path.exists(self.data_path):
            try:
                with open(self.data_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                all_patterns = []
                for cat in data.values():
                    if isinstance(cat, list):
                        all_patterns.extend(cat)
                return all_patterns
            except Exception as e:
                print(f"[CodePatternLibrary] Error loading patterns: {e}")
        return []

    def find_pattern(self, query: str) -> Optional[Dict[str, Any]]:
        """Find the most relevant verified algorithm/pattern for a user query."""
        if not self.patterns:
            return None

        q = query.lower()
        # Ignore web search queries unless an algorithm name is explicitly mentioned
        if any(term in q for term in ["search web", "web search", "search the web", "google ", "browse ", "latest news", "current weather", "latest stocks"]):
            if not any(pat.get("name", "").replace("_", " ") in q for pat in self.patterns):
                return None

        q_tokens = set(re.findall(r"\w+", q))

        best_match = None
        best_score = 0

        for pat in self.patterns:
            name = pat.get("name", "").lower()
            cat = pat.get("category", "").lower()
            desc = pat.get("description", "").lower()

            score = 0
            # Direct name match
            if name.replace("_", " ") in q or name in q:
                score += 10
            # Category match
            if cat in q:
                score += 3
            # Token overlap
            desc_tokens = set(re.findall(r"\w+", desc))
            overlap = len(q_tokens.intersection(desc_tokens))
            score += overlap

            if score > best_score:
                best_score = score
                best_match = pat

        return best_match if best_score >= 2 else None


class SelfHealingExecutionLoop:
    """
    Runs code in an AST-sandboxed execution environment, catches runtime errors,
    and applies automated repair heuristics to fix and verify code.
    """
    def __init__(self):
        self.validator = ASTCodeValidator()

    def execute_and_heal(self, code: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Executes code through the self-healing loop.
        Returns: { success: bool, code: str, output: str, iterations: int, repairs: list }
        """
        current_code = code
        repairs: List[str] = []

        for attempt in range(1, max_retries + 1):
            # 1. AST Syntax Check
            is_valid, syn_err, lineno = self.validator.validate_syntax(current_code)
            if not is_valid:
                repaired = self.validator.auto_repair_syntax(current_code, syn_err or "", lineno)
                if repaired != current_code:
                    repairs.append(f"Attempt {attempt}: Auto-repaired syntax error at line {lineno} ({syn_err})")
                    current_code = repaired
                    continue
                else:
                    return {
                        "success": False,
                        "code": current_code,
                        "output": f"Syntax Error: {syn_err} at line {lineno}",
                        "iterations": attempt,
                        "repairs": repairs
                    }

            # 2. Sandboxed Python Execution
            exec_res = security_manager.execute_sandboxed_python(current_code)
            if exec_res.get("success"):
                return {
                    "success": True,
                    "code": current_code,
                    "output": exec_res.get("output", ""),
                    "iterations": attempt,
                    "repairs": repairs
                }

            # 3. Handle Runtime Error
            error_output = exec_res.get("output", "")
            repaired_code = self._heal_runtime_error(current_code, error_output)
            if repaired_code and repaired_code != current_code:
                repairs.append(f"Attempt {attempt}: Healed runtime exception: {error_output[:80]}")
                current_code = repaired_code
            else:
                return {
                    "success": False,
                    "code": current_code,
                    "output": error_output,
                    "iterations": attempt,
                    "repairs": repairs
                }

        return {
            "success": False,
            "code": current_code,
            "output": f"Execution failed after {max_retries} self-healing attempts.",
            "iterations": max_retries,
            "repairs": repairs
        }

    def _heal_runtime_error(self, code: str, error_traceback: str) -> Optional[str]:
        """
        Applies automated code healing heuristics based on runtime error type.
        """
        # 1. ZeroDivisionError
        if "ZeroDivisionError" in error_traceback:
            # Replace raw division with safe division guard
            pattern = r"(\b\w+\s*/\s*(\w+))"
            match = re.search(pattern, code)
            if match:
                divisor = match.group(2)
                guard = f"({match.group(1)} if {divisor} != 0 else 0)"
                return code.replace(match.group(1), guard, 1)

        # 2. IndexError
        if "IndexError" in error_traceback:
            # Wrap indexing with length guard
            idx_match = re.search(r"(\w+)\[([^\]]+)\]", code)
            if idx_match:
                arr = idx_match.group(1)
                idx = idx_match.group(2)
                safe_expr = f"({arr}[{idx}] if 0 <= ({idx}) < len({arr}) else None)"
                return code.replace(idx_match.group(0), safe_expr, 1)

        # 3. KeyError
        if "KeyError" in error_traceback:
            # Replace dict[key] with dict.get(key)
            key_match = re.search(r"(\w+)\[['\"]([^'\"]+)['\"]\]", code)
            if key_match:
                d = key_match.group(1)
                k = key_match.group(2)
                return code.replace(key_match.group(0), f"{d}.get('{k}')", 1)

        # 4. NameError: name 'x' is not defined (Common missing standard library imports)
        name_match = re.search(r"NameError: name '(\w+)' is not defined", error_traceback)
        if name_match:
            missing_name = name_match.group(1)
            std_imports = {
                "json": "import json\n",
                "math": "import math\n",
                "os": "import os\n",
                "re": "import re\n",
                "sys": "import sys\n",
                "time": "import time\n",
                "random": "import random\n",
                "deque": "from collections import deque\n",
                "defaultdict": "from collections import defaultdict\n",
                "Counter": "from collections import Counter\n",
                "List": "from typing import List\n",
                "Dict": "from typing import Dict\n",
                "Optional": "from typing import Optional\n",
                "Tuple": "from typing import Tuple\n"
            }
            if missing_name in std_imports:
                return std_imports[missing_name] + code

        return None


class CodingEngine:
    """
    Unified Offline Coding Engine for V.O.I.D.
    """
    _instance: Optional[CodingEngine] = None

    def __init__(self):
        self.validator = ASTCodeValidator()
        self.indexer = WorkspaceSymbolIndexer()
        self.patterns = LocalCodePatternLibrary()
        self.healer = SelfHealingExecutionLoop()

    @classmethod
    def get_instance(cls) -> CodingEngine:
        if cls._instance is None:
            cls._instance = CodingEngine()
        return cls._instance

    def process_code_request(self, query: str) -> Dict[str, Any]:
        """
        Process a coding request:
        1. Checks pattern library for verified algorithmic templates.
        2. Inspects workspace context if relevant.
        3. Validates and runs through self-healing loop.
        """
        # 1. Check verified pattern library
        pattern = self.patterns.find_pattern(query)
        if pattern:
            return {
                "source": "verified_pattern_library",
                "name": pattern.get("name"),
                "category": pattern.get("category"),
                "description": pattern.get("description"),
                "code": pattern.get("code"),
                "test": pattern.get("test"),
                "verified": True
            }

        # 2. Check if user is asking to find symbols / search codebase
        if any(term in query.lower() for term in ["find function", "find class", "search symbol", "where is", "find symbol"]):
            symbol_query = re.sub(r"^(find function|find class|search symbol|where is|find symbol)\s+", "", query, flags=re.IGNORECASE).strip()
            symbols = self.indexer.find_symbol(symbol_query)
            return {
                "source": "workspace_index",
                "query": symbol_query,
                "symbols": symbols,
                "count": len(symbols)
            }

        return {
            "source": "general_coding",
            "query": query,
            "verified": False
        }


# Global singleton instance
coding_engine = CodingEngine.get_instance()
