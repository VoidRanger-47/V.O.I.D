"""
core/agents/coding_agent.py
Dedicated 100% Offline Coding & Software Engineering Agent for V.O.I.D.
Integrates AST validation, algorithmic pattern retrieval, workspace symbol indexing,
and self-healing sandboxed execution.
"""

import glob
import os
from typing import Any, Dict, Optional

from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel, security_manager
from providers.manager import model_manager
from skills.coding import handle_coding_query, execute_and_verify_code, get_coding_persona, format_code_response
from skills.coding_engine import coding_engine, ASTCodeValidator, WorkspaceSymbolIndexer


class CodingAgent(BaseAgent):
    """
    Dedicated Coding & Engineering Agent.
    Specialized in workspace inspection, AST-sandboxed Python execution,
    verified algorithmic patterns, and self-healing debugging.
    """
    def __init__(self):
        super().__init__(
            name="coding_agent",
            role="Performs offline code analysis, sandboxed execution, repository AST indexing, and self-healing debugging",
            permission_level=PermissionLevel.LEVEL_2_READ_FILES,
            is_llm_assisted=True
        )
        self.security = security_manager
        self.model_mgr = model_manager
        self.engine = coding_engine

    def process(self, message: AgentMessage) -> AgentMessage:
        action = message.payload.get("action", "auto")
        code = message.payload.get("code")
        query = message.payload.get("query", message.goal)

        # 1. Direct Math Request
        if action == "math" or ("solve" in (query or "").lower() and any(c.isdigit() for c in query or "")):
            from skills.math import handle_math
            math_res = handle_math(query)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=str(math_res),
                payload={"math_result": math_res}
            )

        # 2. Sandboxed Python Execution with Self-Healing
        elif action in ["run_python", "execute_and_heal"] and code:
            heal_res = execute_and_verify_code(code)
            status = "SUCCESS" if heal_res.get("success") else "FAILED"
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status=status,
                result=heal_res.get("output"),
                payload=heal_res
            )

        # 3. Workspace AST Symbol Search
        elif action in ["find_symbol", "search_symbols"]:
            sym_query = message.payload.get("symbol", query)
            symbols = self.engine.indexer.find_symbol(sym_query)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=f"Found {len(symbols)} symbol(s) in workspace matching '{sym_query}'.",
                payload={"symbols": symbols, "count": len(symbols)}
            )

        # 4. Workspace Repository Inspection & File Outline
        elif action in ["inspect_repo", "outline"]:
            target_file = message.payload.get("file")
            if target_file:
                outline = self.engine.indexer.get_module_outline(target_file)
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="SUCCESS" if "error" not in outline else "FAILED",
                    result=str(outline),
                    payload=outline
                )
            else:
                symbols = self.engine.indexer.scan_workspace(force_rescan=True)
                py_files = glob.glob("**/*.py", recursive=True)
                summary = (
                    f"Repository AST Analysis:\n"
                    f"• {len(py_files)} Python source modules found.\n"
                    f"• {len(symbols)} total functions and classes indexed offline."
                )
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="SUCCESS",
                    result=summary,
                    payload={"files_count": len(py_files), "symbol_count": len(symbols)}
                )

        # 5. General Coding Query (Pattern check -> Neural generation with AST validation)
        else:
            # First check verified algorithmic pattern library
            pattern_res = handle_coding_query(query)
            if pattern_res.get("handled"):
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="SUCCESS",
                    result=pattern_res.get("response"),
                    payload=pattern_res
                )

            # Otherwise, neural synthesis via active model provider with coding persona
            provider = self.model_mgr.get_active_provider()
            persona = get_coding_persona(query)
            prompt = (
                f"{persona}\n"
                f"### User:\n{query}\n"
                f"### V.O.I.D. (Verified Offline Code):\n"
            )
            response = provider.generate(prompt, max_new_tokens=500, temperature=0.3)
            formatted = format_code_response(response)

            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=formatted,
                payload={"response": formatted}
            )
