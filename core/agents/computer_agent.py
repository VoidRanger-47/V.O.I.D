# core/agents/computer_agent.py
"""
V.O.I.D. Computer Agent.
Autonomous Operating Layer Agent for controlled desktop interaction, application management,
active window manipulation, precision mouse/keyboard navigation, and multi-step GUI workflows.
"""

from typing import Dict, Any, List
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel, security_manager
from core.tool_registry import safe_launch_application
from skills.desktop_control import (
    list_desktop_windows,
    focus_desktop_window,
    execute_desktop_action,
    execute_desktop_macro
)
from core.desktop.driver import desktop_driver


class ComputerAgent(BaseAgent):
    """
    Dedicated Computer Agent.
    Handles secure desktop automation, application launching, window controls,
    mouse/keyboard interactions, and sequential GUI macros under Level 4 permissions.
    """
    def __init__(self):
        super().__init__(
            name="computer_agent",
            role="Performs controlled desktop interaction, OS window control, and GUI automation",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            is_llm_assisted=False
        )

    def process(self, message: AgentMessage) -> AgentMessage:
        # Verify Level 4 permission
        security_manager.verify_permission(self.permission_level, "computer_agent")

        payload = message.payload or {}
        action = payload.get("action", "").lower().strip()
        goal = message.goal or ""

        # Default action inference if not explicitly passed
        if not action:
            goal_low = goal.lower()
            if any(k in goal_low for k in ["list windows", "open windows", "active windows", "show windows"]):
                action = "list_windows"
            elif any(k in goal_low for k in ["focus ", "switch to ", "bring up "]):
                action = "focus"
            elif any(k in goal_low for k in ["click", "press", "type", "hotkey"]):
                action = "action"
            else:
                action = "launch"

        # 1. Launch application
        if action == "launch":
            app_name = payload.get("app_name", goal)
            res = safe_launch_application(app_name)
            is_success = "🚀 Launched" in res or "✅" in res
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS" if is_success else "FAILED",
                result=res,
                payload={"action": "launch", "app_name": app_name, "output": res}
            )

        # 2. List open desktop windows
        elif action in ["list_windows", "windows"]:
            visible_only = payload.get("visible_only", True)
            windows = list_desktop_windows(visible_only=visible_only)
            summary = f"🖥️ **Active Windows ({len(windows)}):**\n" + "\n".join(
                [f"- **{w['title']}** (PID: {w['pid']}, App: {w['process_name']})" for w in windows[:15]]
            )
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS",
                result=summary,
                payload={"action": "list_windows", "windows": windows, "count": len(windows)}
            )

        # 3. Focus a specific window
        elif action in ["focus", "focus_window"]:
            target = payload.get("target") or payload.get("app_name") or goal
            # Clean common prefixes from goal
            for pfx in ["focus window", "focus", "switch to", "bring up"]:
                if target.lower().startswith(pfx):
                    target = target[len(pfx):].strip()
            focus_res = focus_desktop_window(target)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS" if focus_res.get("success") else "FAILED",
                result=focus_res.get("message", "Focus attempt completed."),
                payload=focus_res
            )

        # 4. Single Desktop Action (click, type, hotkey, scroll, etc.)
        elif action in ["action", "desktop_action", "click", "type", "hotkey", "scroll"]:
            sub_action = payload.get("sub_action", action)
            if sub_action in ["action", "desktop_action"]:
                sub_action = payload.get("action_type", "click")
            params = payload.get("params", payload)
            res = execute_desktop_action(sub_action, params)
            is_success = res.get("success", False)
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS" if is_success else "FAILED",
                result=f"Desktop action '{sub_action}': {'Success' if is_success else res.get('error')}",
                payload=res
            )

        # 5. Multi-step Macro Workflow
        elif action in ["macro", "workflow"]:
            steps = payload.get("steps", [])
            macro_res = execute_desktop_macro(steps)
            is_success = macro_res.get("success", False)
            msg = (
                f"✅ Completed {macro_res.get('completed_steps')}/{macro_res.get('total_steps')} macro steps."
                if is_success else
                f"❌ Macro stopped at step {macro_res.get('completed_steps')}: {macro_res.get('error')}"
            )
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS" if is_success else "FAILED",
                result=msg,
                payload=macro_res
            )

        # 6. Screen Capture
        elif action in ["screenshot", "capture_screen"]:
            img = desktop_driver.capture_screen()
            if img:
                w, h = img.size
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="SUCCESS",
                    result=f"📸 Captured desktop screen ({w}x{h}).",
                    payload={"action": "screenshot", "width": w, "height": h}
                )
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                error="Failed to capture desktop screenshot.",
                result="❌ Failed to capture desktop screenshot."
            )

        return AgentMessage(
            sender=self.name,
            receiver=message.sender,
            task_id=message.task_id,
            mission_id=message.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="FAILED",
            error=f"Unsupported computer action: {action}",
            result=f"Action '{action}' is not supported by ComputerAgent."
        )
