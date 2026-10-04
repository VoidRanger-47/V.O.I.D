# core/agents/knowledge_agent.py
import os
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from skills.computer_control import analyze_local_document
from skills.agentic import retrieve_local_knowledge

class KnowledgeAgent(BaseAgent):
    """
    Dedicated Knowledge Agent (100% Offline).
    Specialized in parsing local PDFs, project documentation, code files, and knowledge base retrieval.
    """
    def __init__(self):
        super().__init__(
            name="knowledge_agent",
            role="Extracts and searches local offline documentation, PDFs, and repository knowledge",
            permission_level=PermissionLevel.LEVEL_2_READ_FILES,
            is_llm_assisted=False
        )

    def process(self, message: AgentMessage) -> AgentMessage:
        filepath = message.payload.get("filepath")
        query = message.payload.get("query", message.goal)

        if filepath and os.path.exists(filepath):
            doc_summary = analyze_local_document(filepath)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=doc_summary,
                payload={"document_analysis": doc_summary}
            )

        # Knowledge retrieval
        snippets = retrieve_local_knowledge(query, top_k=3)
        if snippets:
            joined = "\n\n".join(snippets)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=joined,
                payload={"snippets": snippets}
            )

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="SUCCESS",
            result="No local knowledge passages found for this query.",
            payload={"snippets": []}
        )
