# core/mcp/server.py
"""
V.O.I.D. Model Context Protocol (MCP) Server.
Exposes V.O.I.D.'s local multi-agent capabilities, desktop GUI controls, hardware telemetry,
memory search, and phone controls as standard MCP tools, resources, and prompts.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from core.mcp.protocol import (
    JsonRpcRequest, JsonRpcResponse, MCPTool, MCPResource, MCPPrompt,
    LATEST_PROTOCOL_VERSION, METHOD_NOT_FOUND, INVALID_PARAMS, INTERNAL_ERROR
)
from core.tool_registry import tool_registry
from core.state_manager import state_manager
from skills.computer_control import get_local_system_stats
from skills.desktop_control import (
    list_desktop_windows,
    focus_desktop_window,
    execute_desktop_action
)
from core.desktop.driver import desktop_driver

logger = logging.getLogger("VOID.MCPServer")


class MCPServer:
    """
    Standard Model Context Protocol Server for V.O.I.D.
    Can be consumed via Stdio (Claude Desktop / Cursor) or SSE/HTTP (Web / Remote).
    """
    def __init__(self):
        self.server_name = "void-os-layer"
        self.server_version = "2.0.0"
        self._tools: Dict[str, MCPTool] = {}
        self._resources: Dict[str, MCPResource] = {}
        self._prompts: Dict[str, MCPPrompt] = {}
        self._register_features()

    def _register_features(self):
        # 1. System Telemetry Tool
        self._tools["void_system_stats"] = MCPTool(
            name="void_system_stats",
            description="Inspect local computer hardware metrics: CPU load, RAM usage, Storage, and GPU VRAM offline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Whether to return detailed process statistics."
                    }
                }
            }
        )

        # 2. Desktop Windows List Tool
        self._tools["void_list_windows"] = MCPTool(
            name="void_list_windows",
            description="Enumerate all currently open top-level application windows with titles, PIDs, process names, and screen coordinates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "visible_only": {
                        "type": "boolean",
                        "description": "If true, filters out hidden background and zero-sized utility windows. Default is true."
                    }
                }
            }
        )

        # 3. Focus Window Tool
        self._tools["void_focus_window"] = MCPTool(
            name="void_focus_window",
            description="Bring an open desktop application window to the foreground and restore it if minimized.",
            inputSchema={
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "Window title (exact or partial), executable process name (e.g. 'code.exe', 'notepad.exe'), or HWND."
                    }
                },
                "required": ["target"]
            }
        )

        # 4. Desktop GUI Action Tool
        self._tools["void_desktop_action"] = MCPTool(
            name="void_desktop_action",
            description="Execute precision desktop mouse or keyboard actions (click, move, type text, hotkey shortcut, scroll, close). Includes corner failsafe guard.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["click", "move", "type", "hotkey", "press", "scroll", "focus", "close"],
                        "description": "The desktop control action to perform."
                    },
                    "params": {
                        "type": "object",
                        "description": "Action parameters: for 'click'/'move' pass x and y; for 'type' pass text; for 'hotkey' pass keys array e.g. ['ctrl', 'c']; for 'scroll' pass clicks and direction.",
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "button": {"type": "string", "enum": ["left", "right", "double", "middle"]},
                            "text": {"type": "string"},
                            "keys": {"type": "array", "items": {"type": "string"}},
                            "key": {"type": "string"},
                            "clicks": {"type": "integer"},
                            "direction": {"type": "string", "enum": ["up", "down"]},
                            "target": {"type": "string"}
                        }
                    }
                },
                "required": ["action"]
            }
        )

        # 5. Take Desktop Screenshot Tool
        self._tools["void_take_screenshot"] = MCPTool(
            name="void_take_screenshot",
            description="Capture full desktop screenshot and return screen dimensions and visual availability for multimodal inspection.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )

        # 6. Memory Search Tool
        self._tools["void_memory_search"] = MCPTool(
            name="void_memory_search",
            description="Query V.O.I.D.'s local SQLite multi-tier memory (episodic, semantic, project history, user preferences) offline.",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Natural language search phrase to match against memories."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of relevant memory entries to retrieve. Default is 5."
                    }
                },
                "required": ["query"]
            }
        )

        # 7. Safe Python Sandbox Tool
        self._tools["void_execute_code"] = MCPTool(
            name="void_execute_code",
            description="Safely evaluate Python expressions or algorithms in V.O.I.D.'s AST-sandboxed isolation environment.",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "Python code snippet to execute."
                    }
                },
                "required": ["code"]
            }
        )

        # 8. Mobile Phone Alert Tool
        self._tools["void_phone_notify"] = MCPTool(
            name="void_phone_notify",
            description="Send push notifications or alerts to the user's connected Android phone via ADB.",
            inputSchema={
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "Notification title."
                    },
                    "message": {
                        "type": "string",
                        "description": "Notification text body."
                    }
                },
                "required": ["message"]
            }
        )

        # 9. Mobile Phone Telemetry Tool
        self._tools["void_phone_telemetry"] = MCPTool(
            name="void_phone_telemetry",
            description="Query live smartphone telemetry (battery, charging, screen status, network, top app) via ADB.",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        )

        # Register MCP Resources
        self._resources["void://system/telemetry"] = MCPResource(
            uri="void://system/telemetry",
            name="V.O.I.D. System Telemetry",
            description="Live CPU, RAM, Disk, and GPU VRAM performance metrics.",
            mimeType="application/json"
        )
        self._resources["void://desktop/windows"] = MCPResource(
            uri="void://desktop/windows",
            name="Active Desktop Windows",
            description="Current active and foreground application windows on the desktop.",
            mimeType="application/json"
        )

        # Register Prompts
        self._prompts["void_agent_plan"] = MCPPrompt(
            name="void_agent_plan",
            description="Decompose a complex desktop operating goal into a sequential V.O.I.D. action plan.",
            arguments=[
                {"name": "goal", "description": "The high-level objective to accomplish on the computer.", "required": True}
            ]
        )

    def handle_request(self, request_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Main JSON-RPC 2.0 Request Dispatcher."""
        req = JsonRpcRequest.from_dict(request_dict)

        # 1. Initialize
        if req.method == "initialize":
            return JsonRpcResponse(
                id=req.id,
                result={
                    "protocolVersion": LATEST_PROTOCOL_VERSION,
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False}
                    },
                    "serverInfo": {
                        "name": self.server_name,
                        "version": self.server_version
                    }
                }
            ).to_dict()

        # 2. Notifications (initialized)
        elif req.method == "notifications/initialized":
            return {}

        # 3. Ping
        elif req.method == "ping":
            return JsonRpcResponse(id=req.id, result={}).to_dict()

        # 4. Tools List
        elif req.method == "tools/list":
            return JsonRpcResponse(
                id=req.id,
                result={
                    "tools": [t.to_dict() for t in self._tools.values()]
                }
            ).to_dict()

        # 5. Tools Call
        elif req.method == "tools/call":
            params = req.params or {}
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            if tool_name not in self._tools:
                return JsonRpcResponse(
                    id=req.id,
                    error={"code": METHOD_NOT_FOUND, "message": f"Tool '{tool_name}' not found."}
                ).to_dict()

            call_result = self._execute_tool(tool_name, arguments)
            return JsonRpcResponse(
                id=req.id,
                result={
                    "content": [{"type": "text", "text": call_result.get("text", "")}],
                    "isError": not call_result.get("success", True)
                }
            ).to_dict()

        # 6. Resources List
        elif req.method == "resources/list":
            return JsonRpcResponse(
                id=req.id,
                result={
                    "resources": [r.to_dict() for r in self._resources.values()]
                }
            ).to_dict()

        # 7. Resources Read
        elif req.method == "resources/read":
            uri = (req.params or {}).get("uri", "")
            if uri == "void://system/telemetry":
                stats = get_local_system_stats()
                return JsonRpcResponse(
                    id=req.id,
                    result={
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps({"telemetry": stats}, indent=2)
                        }]
                    }
                ).to_dict()
            elif uri == "void://desktop/windows":
                wins = list_desktop_windows(visible_only=True)
                return JsonRpcResponse(
                    id=req.id,
                    result={
                        "contents": [{
                            "uri": uri,
                            "mimeType": "application/json",
                            "text": json.dumps({"windows": wins}, indent=2)
                        }]
                    }
                ).to_dict()
            else:
                return JsonRpcResponse(
                    id=req.id,
                    error={"code": INVALID_PARAMS, "message": f"Unknown resource URI: {uri}"}
                ).to_dict()

        # 8. Prompts List
        elif req.method == "prompts/list":
            return JsonRpcResponse(
                id=req.id,
                result={
                    "prompts": [p.to_dict() for p in self._prompts.values()]
                }
            ).to_dict()

        # 9. Prompts Get
        elif req.method == "prompts/get":
            name = (req.params or {}).get("name", "")
            if name == "void_agent_plan":
                goal = (req.params or {}).get("arguments", {}).get("goal", "")
                return JsonRpcResponse(
                    id=req.id,
                    result={
                        "description": "V.O.I.D. Planning Template",
                        "messages": [
                            {
                                "role": "user",
                                "content": {
                                    "type": "text",
                                    "text": f"You are acting as V.O.I.D. Operating Layer. Decompose this user desktop goal into actionable tool calls using `void_list_windows`, `void_focus_window`, and `void_desktop_action`:\n\nGOAL: {goal}"
                                }
                            }
                        ]
                    }
                ).to_dict()
            return JsonRpcResponse(
                id=req.id,
                error={"code": METHOD_NOT_FOUND, "message": f"Prompt '{name}' not found."}
            ).to_dict()

        # Fallback Method Not Found
        return JsonRpcResponse(
            id=req.id,
            error={"code": METHOD_NOT_FOUND, "message": f"Method '{req.method}' not implemented."}
        ).to_dict()

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an MCP tool invocation to the underlying VOID subsystem."""
        try:
            if name == "void_system_stats":
                stats = get_local_system_stats()
                return {"success": True, "text": f"V.O.I.D. System Stats:\n{stats}"}

            elif name == "void_list_windows":
                vis = args.get("visible_only", True)
                wins = list_desktop_windows(visible_only=vis)
                return {"success": True, "text": json.dumps({"count": len(wins), "windows": wins}, indent=2)}

            elif name == "void_focus_window":
                target = args.get("target", "")
                res = focus_desktop_window(target)
                return {"success": res.get("success", False), "text": res.get("message", "")}

            elif name == "void_desktop_action":
                action = args.get("action", "")
                params = args.get("params", {})
                res = execute_desktop_action(action, params)
                return {"success": res.get("success", False), "text": json.dumps(res, indent=2)}

            elif name == "void_take_screenshot":
                img = desktop_driver.capture_screen()
                if img:
                    w, h = img.size
                    return {"success": True, "text": f"Screenshot captured successfully: {w}x{h} pixels."}
                return {"success": False, "text": "Screenshot capture unavailable or failed."}

            elif name == "void_memory_search":
                query = args.get("query", "")
                limit = args.get("limit", 5)
                from void_memory.memory import void_memory
                results = void_memory.search(query, limit=limit)
                return {"success": True, "text": json.dumps({"query": query, "results": results}, indent=2)}

            elif name == "void_execute_code":
                code = args.get("code", "")
                from core.security import security_manager
                sec_res = security_manager.execute_sandboxed_python(code)
                return {"success": sec_res.get("success", False), "text": sec_res.get("output", "")}

            elif name == "void_phone_notify":
                title = args.get("title", "V.O.I.D. Notification")
                message = args.get("message", "")
                from void_phone.notifications import phone_notifications
                p_res = phone_notifications.send_phone_notification(title, message)
                return {"success": p_res.get("success", False), "text": json.dumps(p_res, indent=2)}

            elif name == "void_phone_telemetry":
                from void_phone.remote_sensor import phone_sensors
                tel_res = phone_sensors.get_telemetry()
                return {"success": tel_res.get("success", False), "text": json.dumps(tel_res, indent=2)}

            return {"success": False, "text": f"Unknown tool handler: {name}"}

        except Exception as e:
            logger.error(f"Error executing MCP tool '{name}': {e}", exc_info=True)
            return {"success": False, "text": f"Error executing tool '{name}': {str(e)}"}


# Global MCP Server Singleton
mcp_server = MCPServer()
