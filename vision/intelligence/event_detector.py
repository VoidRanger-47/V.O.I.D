"""
vision/intelligence/event_detector.py
Event-based vision perception system for V.O.I.D.
Generates structured visual events (PERSON_ENTERED, OWNER_RECOGNIZED, NEW_OBJECT, etc.)
with anti-spam debounce timers and event notification dispatchers.
"""

import time
import logging
from typing import Dict, Any, List, Optional, Callable, Set

logger = logging.getLogger("void.vision.event_detector")

VISION_EVENTS = [
    "PERSON_ENTERED",
    "PERSON_LEFT",
    "OWNER_RECOGNIZED",
    "PERSON_RECOGNIZED",
    "NEW_OBJECT_DETECTED",
    "MOTION_DETECTED",
    "CAMERA_BLOCKED",
    "LIGHTING_CHANGED"
]

class EventDetector:
    """
    Evaluates frame perception diffs and triggers high-level vision events
    without overwhelming the user with duplicate alerts.
    """

    DEFAULT_COOLDOWN_SECONDS = {
        "PERSON_ENTERED": 12.0,
        "PERSON_LEFT": 12.0,
        "OWNER_RECOGNIZED": 20.0,
        "PERSON_RECOGNIZED": 15.0,
        "NEW_OBJECT_DETECTED": 10.0,
        "MOTION_DETECTED": 8.0,
        "CAMERA_BLOCKED": 12.0,
        "LIGHTING_CHANGED": 20.0
    }

    def __init__(self):
        self._last_event_times: Dict[str, float] = {}
        self._subscribers: List[Callable[[str, Dict[str, Any]], None]] = []

        # Tracking state
        self._prev_person_count = 0
        self._prev_owner_present = False
        self._prev_recognized_names: Set[str] = set()
        self._prev_objects: Set[str] = set()
        self._prev_lighting = "normal"

    def subscribe(self, callback: Callable[[str, Dict[str, Any]], None]):
        """Register a callback for visual events."""
        self._subscribers.append(callback)

    def _can_fire(self, event_name: str) -> bool:
        """Check if event is past its cooldown window."""
        now = time.time()
        last_t = self._last_event_times.get(event_name, 0.0)
        cooldown = self.DEFAULT_COOLDOWN_SECONDS.get(event_name, 10.0)
        return (now - last_t) >= cooldown

    def _dispatch(self, event_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Record timestamp and notify subscribers."""
        self._last_event_times[event_name] = time.time()
        event_data = {
            "event": event_name,
            "timestamp": time.time(),
            "payload": payload
        }
        for sub in self._subscribers:
            try:
                sub(event_name, payload)
            except Exception as e:
                logger.error(f"Error in vision event subscriber: {e}")
        return event_data

    def evaluate_perception(
        self,
        objects: List[Dict[str, Any]],
        faces: List[Dict[str, Any]],
        scene: Dict[str, Any],
        motion_score: float
    ) -> List[Dict[str, Any]]:
        """
        Compare current perception state against previous state and return triggered events.
        """
        events_triggered = []
        current_person_count = scene.get("people_count", 0)
        current_lighting = scene.get("lighting", "normal")
        current_objects = set(o.get("label", "") for o in objects if o.get("label"))

        # 1. Check Multi-Person Identity Recognition
        current_recognized_faces = [
            f for f in faces 
            if (f.get("recognized") or f.get("identity") in ("owner", "enrolled")) and f.get("name")
        ]
        current_recognized_names = set(f.get("name") for f in current_recognized_faces)
        newly_spotted_names = current_recognized_names - self._prev_recognized_names

        for face in current_recognized_faces:
            name = face.get("name", "Unknown Person")
            is_owner = face.get("identity") == "owner"
            conf = face.get("confidence", 1.0)
            
            # If newly entered or cooled down
            event_key = f"PERSON_RECOGNIZED_{name}"
            if (name in newly_spotted_names) or self._can_fire(event_key):
                self._last_event_times[event_key] = time.time()
                
                event_name = "OWNER_RECOGNIZED" if is_owner else "PERSON_RECOGNIZED"
                if self._can_fire(event_name):
                    events_triggered.append(self._dispatch(event_name, {
                        "name": name,
                        "identity": face.get("identity", "enrolled"),
                        "confidence": conf,
                        "associated_objects": list(current_objects - {"person"})
                    }))

        # 2. Check Person Entered / Left (Generic Count)
        if current_person_count > self._prev_person_count:
            if self._can_fire("PERSON_ENTERED"):
                events_triggered.append(self._dispatch("PERSON_ENTERED", {
                    "count": current_person_count,
                    "delta": current_person_count - self._prev_person_count
                }))
        elif current_person_count < self._prev_person_count and self._prev_person_count > 0:
            if self._can_fire("PERSON_LEFT"):
                events_triggered.append(self._dispatch("PERSON_LEFT", {
                    "count": current_person_count
                }))

        # 3. Check New Object Detected
        new_items = current_objects - self._prev_objects - {"person"}
        if new_items and self._can_fire("NEW_OBJECT_DETECTED"):
            events_triggered.append(self._dispatch("NEW_OBJECT_DETECTED", {
                "new_objects": list(new_items)
            }))

        # 4. Check Camera Blocked / Darkness
        if current_lighting == "dark" and self._prev_lighting != "dark":
            if self._can_fire("CAMERA_BLOCKED"):
                events_triggered.append(self._dispatch("CAMERA_BLOCKED", {
                    "luminance": scene.get("luminance", 0.0)
                }))

        # 5. Check Lighting Change
        if current_lighting != self._prev_lighting and current_lighting != "dark":
            if self._can_fire("LIGHTING_CHANGED"):
                events_triggered.append(self._dispatch("LIGHTING_CHANGED", {
                    "from": self._prev_lighting,
                    "to": current_lighting
                }))

        # 6. Significant Motion
        if motion_score > 0.25 and self._can_fire("MOTION_DETECTED"):
            events_triggered.append(self._dispatch("MOTION_DETECTED", {
                "motion_score": round(motion_score, 3)
            }))

        # Update historical state
        self._prev_person_count = current_person_count
        self._prev_owner_present = any(f.get("identity") == "owner" for f in faces)
        self._prev_recognized_names = current_recognized_names
        self._prev_objects = current_objects
        self._prev_lighting = current_lighting

        return events_triggered
