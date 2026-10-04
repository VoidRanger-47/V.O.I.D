# core/state_manager.py
import datetime
import os
import platform
import psutil
import time
from typing import Dict, Any, List, Optional
import torch

from lib.offline_manager import offline_mgr
from core.event_bus import event_bus, SystemEvent

class StateManager:
    """
    Maintains the local World State and Guardian telemetry for V.O.I.D.
    Tracks hardware metrics, active task, active window/project, and triggers guardian alerts.
    """
    _instance: Optional['StateManager'] = None

    def __init__(self):
        self.current_project = "V.O.I.D."
        self.current_task: Optional[str] = None
        self.last_tool: Optional[str] = None
        self.pending_tasks: List[Dict[str, Any]] = []
        self.last_alert_time: Dict[str, float] = {}
        self.alert_cooldown_seconds = 60.0

    @classmethod
    def get_instance(cls) -> 'StateManager':
        if cls._instance is None:
            cls._instance = StateManager()
        return cls._instance

    def set_current_task(self, task_name: Optional[str]):
        self.current_task = task_name
        if task_name:
            event_bus.publish(SystemEvent.TASK_UPDATED, {"task": task_name})

    def set_last_tool(self, tool_name: str):
        self.last_tool = tool_name

    def get_active_window_info(self) -> Dict[str, str]:
        """Returns the title and process of the active window on Windows."""
        try:
            if sys_platform := platform.system() == "Windows":
                import ctypes
                user32 = ctypes.windll.user32
                hwnd = user32.GetForegroundWindow()
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                return {"window_title": title if title else "Desktop", "app": "Windows"}
        except Exception:
            pass
        return {"window_title": "Desktop / VS Code", "app": "Local System"}

    def get_world_state(self) -> Dict[str, Any]:
        """
        Collects comprehensive, safe local World State telemetry.
        """
        now = datetime.datetime.now()
        cpu_percent = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage(os.path.abspath(os.sep))
        battery = psutil.sensors_battery()

        # GPU metrics
        vram_used_gb = 0.0
        vram_total_gb = 0.0
        gpu_name = "CPU Only"
        if torch.cuda.is_available():
            try:
                gpu_name = torch.cuda.get_device_name(0)
                vram_used_gb = round(torch.cuda.memory_allocated(0) / (1024**3), 2)
                vram_total_gb = round(torch.cuda.get_device_properties(0).total_memory / (1024**3), 2)
            except Exception:
                pass

        active_win = self.get_active_window_info()
        is_online = offline_mgr.is_online()

        state = {
            "current_time": now.strftime("%Y-%m-%d %H:%M:%S (%A)"),
            "active_window": active_win.get("window_title", "Unknown"),
            "active_application": active_win.get("app", "Unknown"),
            "current_project": self.current_project,
            "current_task": self.current_task or "Standby",
            "last_tool": self.last_tool or "None",
            "offline_mode": not is_online,
            "network_status": "ONLINE" if is_online else "OFFLINE (100% Local)",
            "cpu_usage_percent": cpu_percent,
            "ram_used_gb": round(ram.used / (1024**3), 2),
            "ram_total_gb": round(ram.total / (1024**3), 2),
            "ram_percent": ram.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "disk_total_gb": round(disk.total / (1024**3), 2),
            "gpu_name": gpu_name,
            "vram_used_gb": vram_used_gb,
            "vram_total_gb": vram_total_gb,
            "battery_percent": battery.percent if battery else None,
            "battery_plugged": battery.power_plugged if battery else None,
            "pending_tasks_count": len(self.pending_tasks)
        }

        self._check_guardian_alerts(state)
        return state

    def _check_guardian_alerts(self, state: Dict[str, Any]):
        """Evaluates hardware thresholds and emits rate-limited guardian alerts."""
        now = time.time()

        # VRAM Alert (Approaching 4GB limit)
        if state["vram_total_gb"] > 0:
            vram_ratio = state["vram_used_gb"] / state["vram_total_gb"]
            if vram_ratio > 0.90:
                if now - self.last_alert_time.get("vram", 0) > self.alert_cooldown_seconds:
                    self.last_alert_time["vram"] = now
                    event_bus.publish(
                        SystemEvent.SYSTEM_ALERT,
                        {"level": "WARNING", "message": f"GPU VRAM usage high ({state['vram_used_gb']} GB / {state['vram_total_gb']} GB)."}
                    )

        # RAM Alert
        if state["ram_percent"] > 92.0:
            if now - self.last_alert_time.get("ram", 0) > self.alert_cooldown_seconds:
                self.last_alert_time["ram"] = now
                event_bus.publish(
                    SystemEvent.SYSTEM_ALERT,
                    {"level": "WARNING", "message": f"Host RAM usage at {state['ram_percent']}%."}
                )

state_manager = StateManager.get_instance()
