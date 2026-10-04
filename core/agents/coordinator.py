# core/agents/coordinator.py
import time
from typing import Dict, Any, List, Optional
from core.agents.base import BaseAgent, AgentStatus
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority
from core.event_bus import event_bus, SystemEvent
from core.audit_logger import audit_logger

from core.agents.workspace import SharedWorkspace
from core.agents.scheduler import task_scheduler

class AgentCoordinator:
    """
    Central Coordinator for the V.O.I.D. Multi-Agent Network.
    Manages agent registration, inter-agent messaging, task graph DAG execution, and replanning triggers.
    """
    _instance: Optional['AgentCoordinator'] = None

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_trace: List[Dict[str, Any]] = []
        self.scheduler = task_scheduler

    @classmethod
    def get_instance(cls) -> 'AgentCoordinator':
        if cls._instance is None:
            cls._instance = AgentCoordinator()
        return cls._instance

    def register_agent(self, agent: BaseAgent):
        self.agents[agent.name] = agent

    def get_agent(self, name: str) -> Optional[BaseAgent]:
        return self.agents.get(name)

    def list_agents_state(self) -> List[Dict[str, Any]]:
        return [agent.get_state() for agent in self.agents.values()]

    def route_message(self, message: AgentMessage) -> AgentMessage:
        """
        Routes a typed message to the designated receiver agent.
        """
        receiver_name = message.receiver
        target_agent = self.agents.get(receiver_name)

        if not target_agent:
            return AgentMessage(
                sender="coordinator",
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                error=f"Destination agent '{receiver_name}' not registered in coordinator.",
                result=f"❌ Unknown Agent: '{receiver_name}'."
            )

        # Log trace
        event_bus.publish(SystemEvent.AGENT_TASK_CREATED, {
            "task_id": message.task_id,
            "sender": message.sender,
            "receiver": message.receiver,
            "goal": message.goal
        })

        start_t = time.time()
        response_msg = target_agent.receive_message(message)
        duration = round(time.time() - start_t, 4)

        trace_entry = {
            "task_id": message.task_id,
            "sender": message.sender,
            "receiver": message.receiver,
            "status": response_msg.status,
            "duration": duration,
            "error": response_msg.error,
            "timestamp": time.time()
        }
        self.message_trace.append(trace_entry)
        if len(self.message_trace) > 100:
            self.message_trace.pop(0)

        audit_logger.log(
            event=f"AGENT_COMM_{message.sender}_TO_{message.receiver}",
            tool=message.receiver,
            status=response_msg.status,
            task_id=message.task_id,
            duration=duration,
            error=response_msg.error,
            result_summary=str(response_msg.result)[:150] if response_msg.result else None
        )

        return response_msg

    def execute_parallel_dag(
        self,
        steps: List[Dict[str, Any]],
        workspace: Optional[SharedWorkspace] = None,
        mission_id: Optional[str] = None
    ) -> List[AgentMessage]:
        """
        Executes a planned DAG graph of agent tasks with parallel concurrency.
        """
        if workspace is None:
            workspace = SharedWorkspace(
                task_id=f"dag_{int(time.time())}",
                goal=steps[0].get("goal", "Multi-Agent DAG Goal") if steps else "Task",
                mission_id=mission_id
            )

        return self.scheduler.execute_dag(
            steps=steps,
            workspace=workspace,
            route_func=self.route_message,
            mission_id=mission_id
        )

    def execute_plan_graph(self, steps: List[Dict[str, Any]], mission_id: Optional[str] = None) -> List[AgentMessage]:
        """
        Executes a sequence / graph of planned agent delegations.
        Automatically uses parallel DAG execution if steps contain dependencies or parallelism flags.
        """
        has_dag_structure = any("dependencies" in s for s in steps)
        if has_dag_structure:
            return self.execute_parallel_dag(steps=steps, mission_id=mission_id)

        results = []
        for step in steps:
            target_agent = step.get("agent")
            goal = step.get("goal", "")
            payload = step.get("payload", {})
            priority = step.get("priority", AgentPriority.NORMAL)

            msg = AgentMessage(
                sender="executive",
                receiver=target_agent,
                goal=goal,
                mission_id=mission_id,
                payload=payload,
                priority=priority
            )

            res = self.route_message(msg)
            results.append(res)

            # If a critical step fails, stop and return results for replanning
            if res.status == "FAILED" and priority in [AgentPriority.CRITICAL, AgentPriority.HIGH]:
                break

        return results

agent_coordinator = AgentCoordinator.get_instance()
