# core/agents/network.py
from core.agents.coordinator import agent_coordinator
from core.agents.executive import ExecutiveAgent
from core.agents.perception import PerceptionAgent
from core.agents.memory_agent import MemoryAgent
from core.agents.planning_agent import PlanningAgent
from core.agents.verification_agent import VerificationAgent
from core.agents.coding_agent import CodingAgent
from core.agents.system_agent import SystemAgent
from core.agents.computer_agent import ComputerAgent
from core.agents.knowledge_agent import KnowledgeAgent
from core.agents.research_agent import ResearchAgent
from core.agents.vision_agent import VisionAgent
from core.agents.voice_agent import VoiceAgent
from core.agents.automation_agent import AutomationAgent
from core.agents.phone_agent import PhoneAgent
from core.agents.mathematics_agent import MathematicsAgent

def initialize_multi_agent_network():
    """
    Initializes and registers specialized agents into the central Agent Coordinator.
    """
    agents = [
        ExecutiveAgent(),
        PerceptionAgent(),
        MemoryAgent(),
        PlanningAgent(),
        VerificationAgent(),
        CodingAgent(),
        MathematicsAgent(),
        SystemAgent(),
        ComputerAgent(),
        KnowledgeAgent(),
        ResearchAgent(),
        VisionAgent(),
        VoiceAgent(),
        AutomationAgent(),
        PhoneAgent()
    ]

    for agent in agents:
        agent_coordinator.register_agent(agent)

    return agent_coordinator

# Initialize network at startup
initialize_multi_agent_network()
