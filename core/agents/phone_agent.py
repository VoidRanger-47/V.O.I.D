"""
core/agents/phone_agent.py
Dedicated Phone Control Agent for V.O.I.D.
Handles smartphone automation over ADB: unlocking, launching apps (JioCinema, WhatsApp, YouTube),
initiating phone calls, volume/media adjustments, and device telemetry.
"""

from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from skills.phone_control import (
    handle_phone_control,
    unlock_phone,
    launch_phone_app,
    call_phone_contact,
    get_phone_status,
    send_phone_notification,
    show_phone_toast,
    get_phone_telemetry,
    capture_phone_screen,
    read_phone_sms,
    read_phone_notifications,
    get_phone_briefing
)


class PhoneAgent(BaseAgent):
    """
    Dedicated Android Phone Control Agent.
    Supports app automation, dialing, remote notifications, screen awareness, and SMS ingestion.
    """
    def __init__(self):
        super().__init__(
            name="phone_agent",
            role="Performs Android smartphone automation, app launching, phone calling, notifications, and telemetry",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            is_llm_assisted=False
        )

    def process(self, message: AgentMessage) -> AgentMessage:
        action = message.payload.get("action", "auto")
        goal_text = message.payload.get("command", message.goal)

        try:
            payload_res = {}
            if action == "unlock":
                pin = message.payload.get("pin")
                res = unlock_phone(pin=pin)
            elif action == "launch":
                app_name = message.payload.get("app_name", goal_text)
                res = launch_phone_app(app_name)
            elif action == "call":
                target = message.payload.get("target", goal_text)
                res = call_phone_contact(target)
            elif action in ["status", "telemetry"]:
                telemetry = get_phone_telemetry()
                payload_res = telemetry
                res = f"Phone Telemetry: Battery {telemetry.get('battery', {}).get('level')}%, Status {telemetry.get('battery', {}).get('status')}, App {telemetry.get('foreground_app', {}).get('package')}"
            elif action in ["notify", "send_notification"]:
                title = message.payload.get("title", "V.O.I.D. Alert")
                msg = message.payload.get("message", goal_text)
                prio = message.payload.get("priority", "normal")
                notif_res = send_phone_notification(title=title, message=msg, priority=prio)
                payload_res = notif_res
                res = f"Notification pushed: {title} - {msg}" if notif_res.get("success") else f"Failed: {notif_res.get('error')}"
            elif action == "toast":
                msg = message.payload.get("message", goal_text)
                t_res = show_phone_toast(message=msg)
                payload_res = t_res
                res = f"Toast sent: {msg}" if t_res.get("success") else f"Toast failed: {t_res.get('error')}"
            elif action in ["screen", "screenshot", "phone_screen"]:
                max_dim = message.payload.get("max_dimension", 1080)
                screen_res = capture_phone_screen(max_dimension=max_dim)
                payload_res = screen_res
                res = f"Screen captured ({screen_res.get('width')}x{screen_res.get('height')})" if screen_res.get("success") else f"Capture failed: {screen_res.get('error')}"
            elif action in ["sms", "read_sms"]:
                limit = message.payload.get("limit", 5)
                sms_res = read_phone_sms(limit=limit)
                payload_res = sms_res
                res = f"Retrieved {len(sms_res.get('messages', []))} SMS messages" if sms_res.get("success") else f"SMS read failed: {sms_res.get('error')}"
            elif action in ["notifications", "read_notifications"]:
                limit = message.payload.get("limit", 10)
                notifs = read_phone_notifications(limit=limit)
                payload_res = notifs
                res = f"Retrieved {len(notifs.get('notifications', []))} active notifications"
            elif action in ["briefing", "phone_briefing"]:
                res = get_phone_briefing()
            else:
                # Auto-parse natural language command
                res = handle_phone_control(goal_text)

            is_success = "❌" not in res and "Error" not in res and "failed" not in res.lower()
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="SUCCESS" if is_success else "FAILED",
                result=res,
                payload={"output": res, **payload_res}
            )

        except Exception as e:
            return AgentMessage(
                sender=self.name,
                receiver=message.sender,
                task_id=message.task_id,
                mission_id=message.mission_id,
                message_type=AgentMessageType.RESPONSE,
                status="FAILED",
                error=str(e),
                result=f"PhoneAgent execution error: {str(e)}"
            )
