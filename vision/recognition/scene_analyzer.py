"""
vision/recognition/scene_analyzer.py
Comprehensive environmental and scene understanding for V.O.I.D.
Analyzes lighting, environment type, motion activity, and major object distributions.
"""

import cv2
import numpy as np
from typing import Dict, Any, List
from vision.camera.frame_processor import FrameProcessor

class SceneAnalyzer:
    """
    Evaluates broader environmental properties and produces structured scene data.
    """

    @staticmethod
    def analyze_lighting(frame: np.ndarray) -> Dict[str, Any]:
        """Classify lighting condition based on luminance histogram."""
        if frame is None or frame.size == 0:
            return {"condition": "unknown", "luminance": 0.0, "is_dark": True, "is_glare": False}

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mean_lum = float(np.mean(gray) / 255.0)
        hist = cv2.calcHist([gray], [0], None, [256], [0, 256])
        total_pixels = gray.size

        dark_pixels = float(np.sum(hist[:40]) / total_pixels)
        bright_pixels = float(np.sum(hist[215:]) / total_pixels)

        if mean_lum < 0.18 or dark_pixels > 0.65:
            condition = "dark"
        elif mean_lum < 0.35:
            condition = "low"
        elif mean_lum > 0.80 or bright_pixels > 0.50:
            condition = "bright"
        else:
            condition = "normal"

        return {
            "condition": condition,
            "luminance": round(mean_lum, 2),
            "is_dark": condition == "dark",
            "is_glare": bright_pixels > 0.40
        }

    @staticmethod
    def analyze_scene(
        frame: np.ndarray,
        detected_objects: List[Dict[str, Any]] = None,
        detected_faces: List[Dict[str, Any]] = None,
        motion_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Produce a high-level structured scene analysis.
        Returns:
        {
            "environment": "indoor",
            "lighting": "normal",
            "people_count": 1,
            "major_objects": ["laptop", "desk", "chair"],
            "activity_level": "moderate_motion",
            "summary": "You appear to be in a room with a desk setup."
        }
        """
        detected_objects = detected_objects or []
        detected_faces = detected_faces or []
        
        lighting_info = SceneAnalyzer.analyze_lighting(frame)
        lighting = lighting_info["condition"]

        # Activity level
        if motion_score < 0.01:
            activity = "static"
        elif motion_score < 0.06:
            activity = "low_motion"
        elif motion_score < 0.20:
            activity = "moderate_motion"
        else:
            activity = "high_activity"

        # Unique major objects
        obj_labels = [o.get("label", "") for o in detected_objects if o.get("label")]
        # Count frequencies
        unique_major_objects = list(dict.fromkeys(obj_labels))

        # People count
        people_from_objects = sum(1 for o in detected_objects if o.get("label") == "person")
        people_from_faces = len(detected_faces)
        people_count = max(people_from_objects, people_from_faces)

        # Environment estimation
        desk_items = {"laptop", "keyboard", "mouse", "chair", "table", "tv", "book", "cup", "bottle", "phone"}
        has_desk_setup = len(set(obj_labels).intersection(desk_items)) >= 2

        if has_desk_setup:
            environment = "desk_setup"
        elif "car" in obj_labels or "traffic light" in obj_labels:
            environment = "outdoor"
        else:
            environment = "indoor"

        # Natural summary sentence
        if lighting == "dark":
            summary = "The camera view is currently dark or obscured."
        elif has_desk_setup:
            summary = f"You appear to be at a desk workspace with {len(unique_major_objects)} identified items."
        elif people_count > 1:
            summary = f"The scene contains multiple people ({people_count}) in an indoor environment."
        elif people_count == 1:
            summary = "A person is present in the frame."
        elif unique_major_objects:
            summary = f"I can see {', '.join(unique_major_objects[:4])} in the scene."
        else:
            summary = f"An {environment} space with {lighting} lighting conditions."

        return {
            "environment": environment,
            "lighting": lighting,
            "luminance": lighting_info["luminance"],
            "people_count": people_count,
            "major_objects": unique_major_objects,
            "activity_level": activity,
            "motion_score": round(motion_score, 4),
            "summary": summary
        }
