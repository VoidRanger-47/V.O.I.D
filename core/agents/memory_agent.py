# core/agents/memory_agent.py
from typing import Dict, Any
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from void_memory.memory import void_memory, MemoryTier

class MemoryAgent(BaseAgent):
    """
    Dedicated Memory Agent.
    Sole interface for querying, storing, ranking, and explicitly forgetting memories across all 6 tiers.
    """
    def __init__(self):
        super().__init__(
            name="memory_agent",
            role="Manages multi-tier persistent memory (Working, Episodic, Semantic, Preference, Project, Procedural)",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            is_llm_assisted=False
        )
        self.memory = void_memory

    def process(self, message: AgentMessage) -> AgentMessage:
        action = message.payload.get("action", "retrieve")
        query = message.payload.get("query", message.goal)
        tier = message.payload.get("tier")
        top_k = message.payload.get("top_k", 3)

        if action == "forget":
            target = message.payload.get("target", query)
            count = self.memory.forget_memory(target)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=f"Purged {count} memory record(s) matching '{target}'.",
                payload={"forgotten_count": count}
            )

        elif action == "store":
            text = message.payload.get("text", query)
            importance = float(message.payload.get("importance", 0.7))
            saved = self.memory.store_memory(text, tier=tier or MemoryTier.SEMANTIC, importance=importance)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS" if saved else "FAILED",
                result="Memory saved successfully." if saved else "Failed to save memory.",
                payload={"stored": saved}
            )

        elif action == "inject_context":
            prompt_context = self.memory.inject_memory_into_prompt(query)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=prompt_context,
                payload={"context": prompt_context}
            )

        else:
            # Default: retrieve
            records = self.memory.retrieve_memory(query, tier=tier, top_k=top_k)
            summary = "\n".join([f"- {r['text']}" for r in records])
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=summary if summary else "No matching memory records found.",
                payload={"records": records}
            )
