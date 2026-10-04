# core/tool_registry.py
import subprocess
import time
from dataclasses import dataclass, field
from typing import Dict, Any, Callable, Optional, List

from core.security import PermissionLevel, security_manager, SecurityViolationError
from core.event_bus import event_bus, SystemEvent
from core.state_manager import state_manager
from skills.math import handle_math
from skills.nlp import VOID_NLP, summarize, summarize_eli12
from skills.web_search import perform_search, extract_search_query, is_search_request
from skills.computer_control import get_local_system_stats, analyze_local_document, launch_application
from skills.phone_control import handle_phone_control

def safe_launch_application(app_name: str) -> str:
    """
    Safely launches any local desktop application with permission and error handling.
    """
    return launch_application(app_name)


@dataclass
class Tool:
    name: str
    description: str
    permission_level: PermissionLevel
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    execute_func: Callable[..., Any]
    input_schema: Dict[str, str] = field(default_factory=dict)
    output_schema: Dict[str, str] = field(default_factory=dict)
    timeout_seconds: float = 10.0

    def run(self, *args, **kwargs) -> Any:
        # Verify permission before running
        security_manager.verify_permission(self.permission_level, self.name)
        state_manager.set_last_tool(self.name)

        event_bus.publish(SystemEvent.TOOL_STARTED, {"tool": self.name, "args": str(args)[:100]})
        start_t = time.time()
        try:
            result = self.execute_func(*args, **kwargs)
            duration = round(time.time() - start_t, 4)
            event_bus.publish(SystemEvent.TOOL_FINISHED, {
                "tool": self.name,
                "status": "SUCCESS",
                "duration": duration,
                "summary": str(result)[:200]
            })
            return result
        except Exception as e:
            duration = round(time.time() - start_t, 4)
            event_bus.publish(SystemEvent.TOOL_FAILED, {
                "tool": self.name,
                "status": "FAILED",
                "duration": duration,
                "error": str(e)
            })
            return f"❌ Tool '{self.name}' failed: {str(e)}"

class ToolRegistry:
    """
    Central Registry for all V.O.I.D. system, information, development, and automation tools.
    """
    _instance: Optional['ToolRegistry'] = None

    def __init__(self):
        self._tools: Dict[str, Tool] = {}
        self._nlp = VOID_NLP()
        self._register_default_tools()

    @classmethod
    def get_instance(cls) -> 'ToolRegistry':
        if cls._instance is None:
            cls._instance = ToolRegistry()
        return cls._instance

    def register_tool(self, tool: Tool):
        self._tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        return self._tools.get(name)

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission_level": t.permission_level.name,
                "risk_level": t.risk_level,
                "timeout_seconds": t.timeout_seconds
            }
            for t in self._tools.values()
        ]

    def execute_tool(self, tool_name: str, *args, **kwargs) -> Any:
        tool = self.get_tool(tool_name)
        if not tool:
            return f"❌ Unknown tool '{tool_name}'."
        return tool.run(*args, **kwargs)

    def _register_default_tools(self):
        # 1. System Info
        self.register_tool(Tool(
            name="system_info",
            description="Get current real-world timestamp, OS, and local date offline",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda q="": state_manager.get_world_state()["current_time"]
        ))

        # 2. Local System Monitor
        self.register_tool(Tool(
            name="system_monitor",
            description="Inspect CPU, RAM, Disk space, and GPU VRAM hardware metrics offline",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda q="": get_local_system_stats()
        ))

        # 3. World State
        self.register_tool(Tool(
            name="world_state",
            description="Get the full local computer context including active window, task, and hardware",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda q="": state_manager.get_world_state()
        ))

        # 4. Math Solver
        self.register_tool(Tool(
            name="math_solver",
            description="Solve math formulas, equations, calculus, and matrix linear algebra locally with SymPy",
            permission_level=PermissionLevel.LEVEL_0_CONVERSATION,
            risk_level="LOW",
            execute_func=lambda query: handle_math(query)
        ))

        # 5. Sandboxed Python Interpreter
        self.register_tool(Tool(
            name="python_interpreter",
            description="Safely execute Python code snippets in an AST-verified sandbox environment",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="MEDIUM",
            execute_func=lambda code: security_manager.execute_sandboxed_python(code)["output"]
        ))

        # 6. Local Document Reader
        self.register_tool(Tool(
            name="local_document",
            description="Parse and summarize local text and PDF documents offline",
            permission_level=PermissionLevel.LEVEL_2_READ_FILES,
            risk_level="LOW",
            execute_func=lambda path: analyze_local_document(path)
        ))

        # 7. Safe Computer Control (App Launcher)
        self.register_tool(Tool(
            name="computer_control",
            description="Launch approved local desktop applications (VS Code, Notepad, Explorer, Calculator, Terminal)",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="MEDIUM",
            execute_func=lambda app_name: safe_launch_application(app_name)
        ))

        # 8. NLP Toolkit
        self.register_tool(Tool(
            name="nlp_toolkit",
            description="Analyze sentiment, summarize text, extract entities, and detect language locally",
            permission_level=PermissionLevel.LEVEL_0_CONVERSATION,
            risk_level="LOW",
            execute_func=lambda query: (
                summarize_eli12(query.replace("eli12", "").strip()) if "eli12" in query.lower()
                else summarize(query.replace("summarize", "").strip()) if "summarize" in query.lower() or "summary" in query.lower()
                else self._nlp.run(query)
            )
        ))

        # 9. Optional Web Search (Isolated with offline guard)
        self.register_tool(Tool(
            name="web_search",
            description="Search the web for external real-time information (optional network tool)",
            permission_level=PermissionLevel.LEVEL_6_NETWORK,
            risk_level="LOW",
            execute_func=lambda query: perform_search(extract_search_query(query) if is_search_request(query) else query)
        ))

        # 10. Android Phone Control (ADB Automation)
        self.register_tool(Tool(
            name="phone_control",
            description="Control connected Android phone via ADB: unlock, launch apps (JioCinema, WhatsApp, YouTube), call contacts, adjust volume",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="MEDIUM",
            execute_func=lambda query: handle_phone_control(query)
        ))

        # 11. Computer Vision & Scene Perception
        from skills.vision_engine import vision_engine
        self.register_tool(Tool(
            name="vision_scanner",
            description="Perceive environment through webcam, recognize objects, detect owner identity, and answer visual questions",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda query="": vision_engine.handle_query(query)
        ))

        # 12. Camera Control (Start / Stop)
        self.register_tool(Tool(
            name="vision_camera_control",
            description="Start or stop webcam hardware explicitly",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="LOW",
            execute_func=lambda action="start": vision_engine.handle_query("activate vision" if action == "start" else "turn off camera")
        ))

        # 13. Visual Memory Recall
        self.register_tool(Tool(
            name="visual_memory_recall",
            description="Query episodic visual memory for previously detected objects, desk items, or events",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda query="": vision_engine.handle_query(query)
        ))

        # 14. Desktop Window Listing
        from skills.desktop_control import list_desktop_windows, focus_desktop_window, execute_desktop_action
        from core.desktop.driver import desktop_driver

        self.register_tool(Tool(
            name="list_desktop_windows",
            description="List all active top-level desktop windows with process names and coordinates",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda visible_only=True: list_desktop_windows(visible_only=visible_only)
        ))

        # 15. Focus Desktop Window
        self.register_tool(Tool(
            name="focus_desktop_window",
            description="Bring an open application window to foreground by title, process name, or PID",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="LOW",
            execute_func=lambda target: focus_desktop_window(target)
        ))

        # 16. Desktop Action (Click, Type, Hotkey, Move, Scroll)
        self.register_tool(Tool(
            name="desktop_action",
            description="Perform desktop interaction (mouse click, move, type text, keyboard shortcut, scroll)",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="HIGH",
            execute_func=lambda action, params=None: execute_desktop_action(action, params)
        ))

        # 17. Desktop Screen Capture
        self.register_tool(Tool(
            name="desktop_screenshot",
            description="Capture full desktop or window region screenshot",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda region=None: desktop_driver.capture_screen(region)
        ))

        # 18. Phone Push Notification
        from skills.phone_control import (
            send_phone_notification,
            show_phone_toast,
            get_phone_telemetry,
            capture_phone_screen,
            read_phone_sms,
            read_phone_notifications,
            get_phone_briefing
        )

        self.register_tool(Tool(
            name="phone_notify",
            description="Push a heads-up alert or mission notification to connected smartphone",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="LOW",
            execute_func=lambda title, message, priority="normal": send_phone_notification(title, message, priority)
        ))

        # 19. Phone Toast Alert
        self.register_tool(Tool(
            name="phone_toast",
            description="Display an instant toast alert banner on connected smartphone display",
            permission_level=PermissionLevel.LEVEL_4_APP_CONTROL,
            risk_level="LOW",
            execute_func=lambda message: show_phone_toast(message)
        ))

        # 20. Phone Telemetry & Sensing
        self.register_tool(Tool(
            name="phone_telemetry",
            description="Extract live smartphone telemetry (battery, display, top app, network, storage)",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda: get_phone_telemetry()
        ))

        # 21. Phone Screen Capture
        self.register_tool(Tool(
            name="phone_screenshot",
            description="Capture screenshot frame of connected smartphone screen",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda max_dimension=1080: capture_phone_screen(max_dimension)
        ))

        # 22. Phone SMS & Notification Reading
        self.register_tool(Tool(
            name="phone_read_sms",
            description="Read recent incoming SMS messages from the phone inbox",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="MEDIUM",
            execute_func=lambda limit=5: read_phone_sms(limit)
        ))

        self.register_tool(Tool(
            name="phone_notifications",
            description="Read active status notifications posted in the smartphone notification tray",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda limit=10: read_phone_notifications(limit)
        ))

        self.register_tool(Tool(
            name="phone_briefing",
            description="Generate an executive natural language briefing of pending phone communications",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            execute_func=lambda: get_phone_briefing()
        ))

        # 23. Offline Image Generator
        self.register_tool(Tool(
            name="generate_image",
            description="Generate high-resolution visual art and concept images locally offline from a text prompt",
            permission_level=PermissionLevel.LEVEL_1_READ_INFO,
            risk_level="LOW",
            input_schema={"prompt": "string", "style": "optional string"},
            output_schema={"response": "string"},
            execute_func=lambda prompt, style=None: __import__('skills.media_engine', fromlist=['media_skill_engine']).media_skill_engine.handle_query(f"{style + ' ' if style else ''}{prompt}")
        ))

        # 24. Dynamic Plugins Registration
        try:
            from core.plugin_manager import PluginManager
            plugin_mgr = PluginManager.get_instance()
            plugin_mgr.register_tools_to_registry(self)
        except Exception as e:
            print(f"⚠️ [ToolRegistry] Error loading plugins: {e}")

tool_registry = ToolRegistry.get_instance()

