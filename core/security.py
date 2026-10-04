# core/security.py
import ast
import contextlib
import io
import math
import random
import re
import sys
import time
from enum import IntEnum
from typing import Dict, Any, Tuple, Optional, Set

class PermissionLevel(IntEnum):
    LEVEL_0_CONVERSATION = 0
    LEVEL_1_READ_INFO = 1
    LEVEL_2_READ_FILES = 2
    LEVEL_3_MODIFY_FILES = 3
    LEVEL_4_APP_CONTROL = 4
    LEVEL_5_SYSTEM_MODS = 5
    LEVEL_6_NETWORK = 6

class SecurityViolationError(Exception):
    """Raised when an operation violates security permissions or safety policies."""
    pass

class SecurityManager:
    """
    V.O.I.D. Core Security & Safety Controller.
    Enforces permission levels, AST safety verification, sandbox isolation, and emergency stops.
    """
    _instance: Optional['SecurityManager'] = None

    FORBIDDEN_CALLS: Set[str] = {
        "os.system", "os.popen", "os.remove", "os.unlink", "os.rmdir",
        "subprocess.Popen", "subprocess.run", "subprocess.call", "subprocess.check_output",
        "shutil.rmtree", "shutil.move", "__import__", "importlib.import_module",
        "eval", "exec", "compile", "globals", "locals", "getattr", "setattr", "delattr"
    }

    FORBIDDEN_MODULES: Set[str] = {
        "socket", "http", "urllib", "requests", "paramiko", "ftplib",
        "ctypes", "winreg", "_winapi", "pty"
    }

    def __init__(self, default_max_permission: PermissionLevel = PermissionLevel.LEVEL_6_NETWORK):
        self.max_permission = default_max_permission
        self.emergency_stop_triggered = False

    @classmethod
    def get_instance(cls) -> 'SecurityManager':
        if cls._instance is None:
            cls._instance = SecurityManager()
        return cls._instance

    def trigger_emergency_stop(self, reason: str = "Manual emergency override"):
        self.emergency_stop_triggered = True

    def reset_emergency_stop(self):
        self.emergency_stop_triggered = False

    def verify_permission(self, required_level: PermissionLevel, tool_name: str) -> bool:
        if self.emergency_stop_triggered:
            raise SecurityViolationError(f"Emergency stop is active. Tool '{tool_name}' execution blocked.")
        if required_level > self.max_permission:
            raise SecurityViolationError(
                f"Permission denied for '{tool_name}'. Required: {required_level.name}, Max Allowed: {self.max_permission.name}"
            )
        return True

    def scan_python_ast(self, code_str: str) -> Tuple[bool, Optional[str]]:
        """
        Performs static AST inspection to detect unsafe constructs or forbidden functions.
        """
        try:
            tree = ast.parse(code_str)
        except SyntaxError as e:
            return False, f"Syntax Error: {str(e)}"

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split('.')[0] in self.FORBIDDEN_MODULES:
                        return False, f"Security Violation: Import of '{alias.name}' is prohibited."
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split('.')[0] in self.FORBIDDEN_MODULES:
                    return False, f"Security Violation: Import from '{node.module}' is prohibited."

            # Check function calls
            elif isinstance(node, ast.Call):
                call_name = ""
                if isinstance(node.func, ast.Name):
                    call_name = node.func.id
                elif isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        call_name = f"{node.func.value.id}.{node.func.attr}"
                    else:
                        call_name = node.func.attr

                if call_name in self.FORBIDDEN_CALLS or call_name in ["exec", "eval", "__import__"]:
                    return False, f"Security Violation: Invocation of dangerous function '{call_name}' is blocked."

        return True, None

    def execute_sandboxed_python(self, code_str: str, timeout_seconds: float = 3.0) -> Dict[str, Any]:
        """
        Safely executes a Python snippet with AST verification, isolated built-ins, and output capture.
        """
        if self.emergency_stop_triggered:
            return {"success": False, "output": "[Emergency Stop Active: Execution Blocked]", "error": "Emergency Stop"}

        clean_code = code_str.replace("```python", "").replace("```", "").strip()
        is_safe, error_msg = self.scan_python_ast(clean_code)
        if not is_safe:
            return {"success": False, "output": f"❌ {error_msg}", "error": error_msg}

        # Safe import controller
        allowed_modules = {
            "math", "random", "re", "time", "datetime", "json", "collections",
            "itertools", "functools", "string", "statistics", "decimal", "fractions",
            "typing", "numpy", "np", "sympy"
        }

        def safe_import(name, *args, **kwargs):
            base_mod = name.split('.')[0]
            if base_mod in allowed_modules:
                return __import__(name, *args, **kwargs)
            raise ImportError(f"Security: Import of module '{name}' is not permitted in sandbox.")

        # Safe execution environment
        safe_builtins = {
            "__import__": safe_import,
            "abs": abs, "all": all, "any": any, "bin": bin, "bool": bool,
            "chr": chr, "dict": dict, "dir": dir, "divmod": divmod, "enumerate": enumerate,
            "filter": filter, "float": float, "format": format, "frozenset": frozenset,
            "hasattr": hasattr, "hash": hash, "hex": hex, "int": int, "isinstance": isinstance,
            "issubclass": issubclass, "iter": iter, "len": len, "list": list, "map": map,
            "max": max, "min": min, "next": next, "oct": oct, "ord": ord, "pow": pow,
            "print": print, "range": range, "repr": repr, "reversed": reversed, "round": round,
            "set": set, "slice": slice, "sorted": sorted, "str": str, "sum": sum,
            "tuple": tuple, "type": type, "zip": zip,
            "None": None, "True": True, "False": False
        }

        exec_globals = {
            "__builtins__": safe_builtins,
            "math": math,
            "random": random,
            "re": re,
            "time": time
        }

        # Try importing numpy/sympy if installed
        try:
            import numpy as np
            exec_globals["np"] = np
            exec_globals["numpy"] = np
        except ImportError:
            pass

        try:
            import sympy
            exec_globals["sympy"] = sympy
        except ImportError:
            pass

        buffer = io.StringIO()
        start_time = time.time()

        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
                exec(clean_code, exec_globals)

            elapsed = round(time.time() - start_time, 4)
            output = buffer.getvalue().strip()
            if not output:
                output = "Code executed successfully with no stdout output."
            elif len(output) > 8000:
                output = output[:8000] + "\n... [Output truncated at 8000 chars]"

            return {"success": True, "output": output, "execution_time": elapsed}
        except Exception as e:
            return {"success": False, "output": f"Runtime Error: {type(e).__name__}: {str(e)}", "error": str(e)}

security_manager = SecurityManager.get_instance()
