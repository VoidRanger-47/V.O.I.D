"""
skills/vision_engine.py
Skill engine for V.O.I.D. Vision.
Bridges skill routing, voice assistant, and multi-agent pipelines to the vision subsystem.
"""

from typing import Dict, Any, Optional
from vision.vision_controller import vision_controller

class VisionEngine:
    """
    Skill Engine interface for V.O.I.D. Vision capabilities.
    """
    _instance: Optional['VisionEngine'] = None

    def __init__(self):
        self.controller = vision_controller

    @classmethod
    def get_instance(cls) -> 'VisionEngine':
        if cls._instance is None:
            cls._instance = VisionEngine()
        return cls._instance

    def handle_query(self, query: str) -> str:
        """Handle a vision-related user prompt or command."""
        q_low = query.lower().strip()

        # Direct control commands - Activation
        activation_triggers = [
            "activate vision", "start vision", "turn on vision", "enable vision", "open vision",
            "turn on camera", "open camera", "start camera", "enable camera", "launch camera",
            "switch on camera", "switch on vision"
        ]
        if any(w in q_low for w in activation_triggers) or (("vision" in q_low or "camera" in q_low) and any(w in q_low for w in ["activate", "turn on", "switch on", "start up", "launch"])):
            started = self.controller.start()
            status_desc = "Optical sensors initialized and tracking active." if started else "Camera hardware initialized for dedicated stream."
            return f"👁️ **Vision System Activated**\n\n{status_desc} Camera access and subject scanning are available on the dedicated **Vision & Perception HUD** webpage.\n\n[🚀 Open Dedicated Vision & Subject Scanner](/vision)"

        # Direct control commands - Deactivation
        deactivation_triggers = [
            "deactivate vision", "stop vision", "turn off vision", "disable vision", "kill vision",
            "close vision", "shut vision", "shutdown vision", "halt vision",
            "turn off camera", "close camera", "stop camera", "deactivate camera", "disable camera",
            "kill camera", "shut camera", "shutdown camera", "halt camera", "stop watching",
            "switch off camera", "switch off vision"
        ]
        if any(w in q_low for w in deactivation_triggers) or (("vision" in q_low or "camera" in q_low) and any(w in q_low for w in ["deactivate", "turn off", "switch off", "shut off", "disable", "kill", "halt", "stop", "close"])):
            self.controller.stop()
            return "🔒 **Vision System Deactivated**. Camera feed terminated and hardware released."

        # Status queries
        status_triggers = [
            "vision status", "camera status", "is vision on", "is camera on",
            "is camera active", "is vision active", "vision active?", "camera active?"
        ]
        if any(w in q_low for w in status_triggers):
            active = self.controller.camera.is_active
            if active:
                return "👁️ **Vision System Active**: Live optical perception and subject tracking are running. View the live HUD feed at [Vision HUD](/vision)."
            else:
                return "💤 **Vision System Standby**: Camera is offline. Say 'activate vision' or visit [Vision HUD](/vision) to initiate optical sensors."

        if "learn my face" in q_low or "enroll my face" in q_low or "register face" in q_low:
            # Check for name in query, e.g. "learn my face as Abhinav"
            name = "Owner"
            if "as " in q_low:
                name = query.split("as ", 1)[1].strip()
            res = self.controller.enroll_owner(name)
            if res.get("success"):
                return f"✅ **Face Profile Enrolled**: {res.get('message')}"
            else:
                return f"⚠️ **Enrollment Failed**: {res.get('error')}"

        # Visual reasoning / Q&A
        res = self.controller.process_query(query)
        return res.get("natural_response", "Visual analysis complete.")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summarized vision telemetry."""
        return self.controller.get_telemetry()


vision_engine = VisionEngine.get_instance()
