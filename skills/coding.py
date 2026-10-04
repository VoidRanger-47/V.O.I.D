"""
skills/coding.py
V.O.I.D. 100% Offline Coding Skill.
Provides offline code generation, AST verification, workspace symbol search,
and self-healing execution.
"""

import re
from typing import Any, Dict, Optional
from skills.coding_engine import coding_engine, ASTCodeValidator, WorkspaceSymbolIndexer


def is_coding_request(user_input: str) -> bool:
    """Check if query is about coding."""
    keywords = [
        "code", "debug", "function", "python", "javascript", "java", "c++",
        "algorithm", "error", "fix", "syntax", "generate", "write", "implement",
        "class", "method", "variable", "loop", "conditional", "binary search",
        "quick sort", "merge sort", "bfs", "dfs", "lru cache", "trie",
        "find function", "find class", "symbol"
    ]
    return any(word in user_input.lower() for word in keywords)


def get_coding_persona(user_input: str) -> str:
    """Inject coding-specific system instruction."""
    text = user_input.lower()

    if any(word in text for word in ["debug", "error", "fix", "bug"]):
        return "\n[SYSTEM: You are an expert code debugger. Analyze the code for errors, explain the root cause, and provide verified fixes with tests.]"
    elif any(word in text for word in ["generate", "write", "create", "implement"]):
        return "\n[SYSTEM: You are a high-performance code architect. Write clean, idiomatic, type-hinted, and well-documented Python code.]"
    elif any(word in text for word in ["explain", "what is", "how does"]):
        return "\n[SYSTEM: You are a technical programming mentor. Explain algorithmic principles and complexity with precise code examples.]"
    else:
        return "\n[SYSTEM: You are V.O.I.D.'s offline coding intelligence. Provide optimal, bug-free, and sandboxed-tested code solutions.]"


def format_code_response(response: str) -> str:
    """Format code blocks with syntax highlighting."""
    if "```" not in response:
        lines = response.split('\n')
        has_code = any(any(keyword in line for keyword in ["def ", "class ", "import ", "return ", "if ", "for ", "while "]) 
                      for line in lines)
        if has_code:
            return f"```python\n{response.strip()}\n```"
    return response


def handle_coding_query(query: str) -> Dict[str, Any]:
    """
    High-level offline coding handler.
    Checks verified pattern library, workspace AST index, or routes to execution.
    """
    res = coding_engine.process_code_request(query)

    if res.get("source") == "verified_pattern_library":
        formatted_code = (
            f"### ⚡ Verified Algorithmic Pattern: {res.get('name').replace('_', ' ').title()}\n"
            f"**Category**: {res.get('category')} | **Status**: Verified 100% Offline\n\n"
            f"_{res.get('description')}_\n\n"
            f"```python\n{res.get('code')}\n```\n\n"
            f"**Unit Verification Test:**\n"
            f"```python\n{res.get('test')}\n```"
        )
        return {
            "handled": True,
            "response": formatted_code,
            "code": res.get("code"),
            "pattern": res
        }

    elif res.get("source") == "workspace_index":
        symbols = res.get("symbols", [])
        if not symbols:
            resp = f"🔍 No symbol found matching '{res.get('query')}' in the local workspace."
        else:
            resp = f"🔍 Found {len(symbols)} symbol(s) in workspace:\n"
            for s in symbols[:10]:
                args_str = f"({', '.join(s.get('args', []))})" if s.get('type') in ['function', 'async_function'] else ""
                resp += f"- **`{s.get('name')}{args_str}`** ({s.get('type')}) in `[{s.get('file')}:{s.get('line')}]`\n"
                if s.get("docstring"):
                    resp += f"  _{s.get('docstring').strip().splitlines()[0]}_\n"
        return {
            "handled": True,
            "response": resp,
            "symbols": symbols
        }

    return {
        "handled": False,
        "query": query
    }


def execute_and_verify_code(code: str, max_retries: int = 3) -> Dict[str, Any]:
    """
    Execute code in the AST-sandboxed self-healing execution loop.
    """
    return coding_engine.healer.execute_and_heal(code, max_retries=max_retries)
