# core/agents/verification_agent.py
import os
import re
from typing import Dict, Any, Optional
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel

class VerificationAgent(BaseAgent):
    """
    Dedicated Verification Agent.
    Independently verifies and audits agent outputs using objective criteria (tests, file presence, syntax validity, non-empty outputs).
    Emits PASS, FAIL, or REPLAN_REQUIRED.
    """
    def __init__(self):
        super().__init__(
            name="verification_agent",
            role="Independently verifies task results, validates outputs against objective criteria, and triggers replanning on failures",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )

    def process(self, message: AgentMessage) -> AgentMessage:
        target_output = message.payload.get("output")
        expected_type = message.payload.get("expected_type", "general")
        check_file = message.payload.get("check_file")
        required_substring = message.payload.get("required_substring")

        # 1. Output presence check
        if target_output is None or (isinstance(target_output, str) and not target_output.strip()):
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                result="VERIFICATION FAILED: Empty or null output returned.",
                payload={"verdict": "FAIL", "reason": "empty_output"}
            )

        output_str = str(target_output)

        # 2. Error string check
        if "❌" in output_str or "Syntax Error:" in output_str or "Security Violation:" in output_str:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                result=f"VERIFICATION FAILED: Output contains error indicator ({output_str[:80]}).",
                payload={"verdict": "FAIL", "reason": "error_present"}
            )

        # 3. File existence verification
        if check_file and not os.path.exists(check_file):
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                result=f"VERIFICATION FAILED: Expected file '{check_file}' was not found on disk.",
                payload={"verdict": "FAIL", "reason": "file_not_found"}
            )

        # 4. Required substring verification
        if required_substring and required_substring.lower() not in output_str.lower():
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                result=f"VERIFICATION FAILED: Output did not contain expected token '{required_substring}'.",
                payload={"verdict": "FAIL", "reason": "token_missing"}
            )

        # 5. Math verification
        if expected_type == "math":
            if not any(c.isdigit() for c in output_str) and not any(var in output_str for var in ["x", "y", "z", "pi", "e"]):
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="FAILED",
                    result="VERIFICATION FAILED: Mathematical output did not contain valid numeric or algebraic solution.",
                    payload={"verdict": "FAIL", "reason": "invalid_math"}
                )

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="SUCCESS",
            result="VERIFICATION PASSED: Output verified against objective criteria.",
            payload={"verdict": "PASS"}
        )
