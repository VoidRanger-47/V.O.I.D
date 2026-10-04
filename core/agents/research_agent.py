# core/agents/research_agent.py
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from skills.web_search import perform_search, extract_search_query
from void_learning.research_agent import WebResearchAgent
from void_learning.knowledge_engine import knowledge_engine

class ResearchAgent(BaseAgent):
    """
    Dedicated Research Agent (Online/Offline Hybrid).
    Handles external web searching, structured deep research, source extraction,
    and factual knowledge acquisition.
    Fails gracefully with a clear no-internet statement when disconnected.
    """
    def __init__(self):
        super().__init__(
            name="research_agent",
            role="Performs structured web research, source verification, and knowledge acquisition",
            permission_level=PermissionLevel.LEVEL_6_NETWORK,
            is_llm_assisted=False
        )
        self.web_researcher = WebResearchAgent()

    def process(self, message: AgentMessage) -> AgentMessage:
        query = message.payload.get("query", message.goal)
        mode = message.payload.get("mode", "search")  # "search" or "deep_research" or "learn"
        clean_q = extract_search_query(query) if query else ""

        if mode in ("deep_research", "learn") or any(k in clean_q.lower() for k in ["learn about", "deep research", "study"]):
            # Run structured research cycle
            research_data = self.web_researcher.research(clean_q)
            is_offline = bool(research_data.get("offline"))

            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="OFFLINE" if is_offline else "SUCCESS",
                result=research_data.get("research_summary", ""),
                payload={
                    "research_data": research_data,
                    "offline": is_offline,
                    "query": clean_q
                }
            )

        # Standard fast search
        search_output = perform_search(clean_q)
        is_offline = "[Offline Mode]" in search_output or "No Internet Access" in search_output

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="OFFLINE" if is_offline else "SUCCESS",
            result=search_output,
            payload={
                "search_results": search_output,
                "offline": is_offline,
                "query": clean_q
            }
        )

