# core/agents/mathematics_agent.py
"""
Dedicated Mathematics Agent for V.O.I.D.
Provides exact symbolic mathematics, calculus, linear algebra, equation solving,
and verified numerical computation using SymPy and NumPy.
Never relies on LLM mental calculation for mathematical proofs or arithmetic.
"""

import re
import time
from typing import Dict, Any, Optional
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.security import PermissionLevel
from skills.math import handle_math


class MathematicsAgent(BaseAgent):
    """
    Deterministic Mathematical & Computational Intelligence Agent.
    Executes algebraic transformations, integrals, derivatives, limits, matrix calculations,
    and equation solving locally with SymPy and NumPy.
    """
    def __init__(self):
        super().__init__(
            name="math_agent",
            role="Performs exact symbolic computation, calculus, linear algebra, and mathematical verification with SymPy/NumPy",
            permission_level=PermissionLevel.LEVEL_0_CONVERSATION,
            is_llm_assisted=False
        )

    def process(self, message: AgentMessage) -> AgentMessage:
        payload = message.payload or {}
        query = payload.get("query", message.goal)
        action = payload.get("action", "solve")

        start_t = time.time()
        try:
            # 1. Deterministic calculation via SymPy engine
            calc_result = handle_math(query)
            duration = round(time.time() - start_t, 4)

            # Verification of output
            has_error = "Error" in str(calc_result) or "Invalid" in str(calc_result)
            status = "FAILED" if has_error else "SUCCESS"

            formatted_response = f"Mathematical Solution:\n{calc_result}"

            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status=status,
                result=str(calc_result),
                confidence=1.0 if status == "SUCCESS" else 0.4,
                payload={
                    "solution": str(calc_result),
                    "query": query,
                    "engine": "SymPy / NumPy (Deterministic)",
                    "execution_time_s": duration,
                    "verified": (status == "SUCCESS")
                }
            )

        except Exception as e:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                result=f"Math execution error: {str(e)}",
                error=str(e),
                confidence=0.0
            )


math_agent = MathematicsAgent()
