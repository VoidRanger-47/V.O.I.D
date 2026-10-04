"""
tests/test_vision_system.py
Comprehensive unit and integration test suite for the V.O.I.D. Vision Subsystem.
"""

import os
import sys
import unittest
import numpy as np
import cv2
import time

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.camera.device_manager import DeviceManager
from vision.camera.frame_processor import FrameProcessor
from vision.camera.camera_manager import CameraManager
from vision.models.model_manager import VisionModelManager, model_manager
from vision.recognition.face_detector import FaceDetector
from vision.recognition.face_recognition import FaceRecognizer
from vision.recognition.object_detector import ObjectDetector
from vision.recognition.scene_analyzer import SceneAnalyzer
from vision.recognition.gesture_detector import GestureDetector
from vision.intelligence.visual_memory import VisualMemory
from vision.intelligence.event_detector import EventDetector
from vision.intelligence.visual_reasoner import VisualReasoner
from vision.vision_controller import VisionController
from skills.vision_engine import VisionEngine
from core.agents.vision_agent import VisionAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.tool_registry import tool_registry
from skills.router import skill_router, SkillType


class TestVisionSubsystem(unittest.TestCase):

    def setUp(self):
        # Create synthetic test frames
        self.blank_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        # Frame with a bright circle (simulating light)
        self.bright_frame = np.ones((480, 640, 3), dtype=np.uint8) * 220
        
        # Frame with synthetic face-like structure
        self.face_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.circle(self.face_frame, (320, 240), 80, (200, 180, 160), -1) # Head
        cv2.circle(self.face_frame, (290, 220), 10, (50, 50, 50), -1)     # Left eye
        cv2.circle(self.face_frame, (350, 220), 10, (50, 50, 50), -1)     # Right eye
        cv2.ellipse(self.face_frame, (320, 270), (30, 12), 0, 0, 180, (30, 30, 120), -1) # Mouth

    def test_01_device_manager(self):
        """Test device scanning and availability check."""
        devices = DeviceManager.list_devices(max_check=2)
        self.assertIsInstance(devices, list)
        print(f"[TEST 1] Available devices found: {len(devices)}")

    def test_02_frame_processor(self):
        """Test resizing, brightness, motion diff, HUD overlay, and JPEG encoding."""
        resized = FrameProcessor.resize_with_aspect(self.blank_frame, 320, 240)
        self.assertEqual(resized.shape, (240, 320, 3))

        dark_lum = FrameProcessor.calculate_brightness(self.blank_frame)
        bright_lum = FrameProcessor.calculate_brightness(self.bright_frame)
        self.assertLess(dark_lum, 0.1)
        self.assertGreater(bright_lum, 0.8)

        # Motion calculation
        gray1 = cv2.cvtColor(self.blank_frame, cv2.COLOR_BGR2GRAY)
        gray2 = cv2.cvtColor(self.bright_frame, cv2.COLOR_BGR2GRAY)
        motion, _ = FrameProcessor.compute_motion(gray1, gray2)
        self.assertGreater(motion, 0.5)

        # HUD Overlay drawing
        annotated = FrameProcessor.draw_hud_overlay(
            frame=self.face_frame,
            objects=[{"label": "laptop", "confidence": 0.9, "location": {"x": 50, "y": 50, "width": 100, "height": 80}}],
            faces=[{"identity": "owner", "name": "Abhinav", "confidence": 0.95, "location": {"x": 240, "y": 160, "width": 160, "height": 160}}],
            scene_info={"lighting": "normal", "environment": "desk_setup"},
            fps=24.0,
            mode="BALANCED"
        )
        self.assertEqual(annotated.shape, self.face_frame.shape)

        # JPEG & Base64
        jpeg_bytes = FrameProcessor.to_jpeg_bytes(annotated)
        self.assertGreater(len(jpeg_bytes), 1000)
        b64_str = FrameProcessor.to_base64(annotated)
        self.assertTrue(b64_str.startswith("data:image/jpeg;base64,"))
        print("[TEST 2] FrameProcessor tests passed.")

    def test_03_model_manager_telemetry(self):
        """Test ModelManager hardware telemetry."""
        mgr = VisionModelManager.get_instance()
        telemetry = mgr.get_hardware_telemetry()
        self.assertIn("cpu_percent", telemetry)
        self.assertIn("ram_percent", telemetry)
        self.assertIn("gpu_available", telemetry)
        print(f"[TEST 3] Telemetry: CPU={telemetry['cpu_percent']}%, GPU={telemetry['gpu_name']}")

    def test_04_face_enrollment_and_recognition(self):
        """Test opt-in local face embedding extraction, enrollment, and recognition."""
        test_profiles_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_profiles.json")
        if os.path.exists(test_profiles_path):
            os.remove(test_profiles_path)

        recognizer = FaceRecognizer(profiles_path=test_profiles_path)
        
        # Create synthetic face crop
        face_crop = self.face_frame[160:320, 240:400]
        emb = recognizer.compute_face_embedding(face_crop)
        self.assertEqual(len(emb), recognizer.EMBEDDING_DIM)
        self.assertAlmostEqual(float(np.linalg.norm(emb)), 1.0, places=2)

        # Enroll test owner
        res = recognizer.enroll_profile("Abhinav", [face_crop, face_crop], is_owner=True)
        self.assertTrue(res["success"])
        self.assertEqual(len(recognizer.list_enrolled_profiles()), 1)

        # Clean up test file
        if os.path.exists(test_profiles_path):
            os.remove(test_profiles_path)
        print("[TEST 4] Face enrollment & embedding vector generation passed.")

    def test_05_scene_analyzer(self):
        """Test scene lighting and environmental classification."""
        dark_scene = SceneAnalyzer.analyze_scene(self.blank_frame)
        self.assertEqual(dark_scene["lighting"], "dark")

        desk_objs = [
            {"label": "laptop", "confidence": 0.9},
            {"label": "keyboard", "confidence": 0.85},
            {"label": "mouse", "confidence": 0.88}
        ]
        desk_scene = SceneAnalyzer.analyze_scene(self.bright_frame, detected_objects=desk_objs)
        self.assertEqual(desk_scene["environment"], "desk_setup")
        self.assertIn("desk workspace", desk_scene["summary"].lower())
        print("[TEST 5] SceneAnalyzer environment heuristics passed.")

    def test_06_visual_memory(self):
        """Test SQLite visual observations logging and querying."""
        test_db = os.path.join(os.path.dirname(os.path.abspath(__file__)), "test_obs.db")
        if os.path.exists(test_db):
            os.remove(test_db)

        vmem = VisualMemory(db_path=test_db)
        obs_id = vmem.record_observation(
            event_type="NEW_OBJECT_DETECTED",
            object_name="wireless mouse",
            context="user workspace",
            confidence=0.94,
            importance=0.7
        )
        self.assertGreater(obs_id, 0)

        recent = vmem.query_recent(limit=5)
        self.assertEqual(len(recent), 1)
        self.assertEqual(recent[0]["object"], "wireless mouse")

        by_obj = vmem.query_by_object("mouse")
        self.assertEqual(len(by_obj), 1)

        today_objs = vmem.query_today_objects()
        self.assertIn("wireless mouse", today_objs)

        # Allow garbage collection on Windows before remove
        del vmem
        import gc
        gc.collect()
        try:
            if os.path.exists(test_db):
                os.remove(test_db)
        except Exception:
            pass
        print("[TEST 6] VisualMemory SQLite queries passed.")

    def test_07_event_detector(self):
        """Test event trigger evaluation with debounce protection."""
        detector = EventDetector()
        events = []
        detector.subscribe(lambda name, payload: events.append(name))

        scene = {"people_count": 1, "lighting": "normal"}
        objs = [{"label": "laptop"}]
        faces = [{"identity": "owner", "name": "Abhinav", "confidence": 0.95}]

        # First trigger
        fired = detector.evaluate_perception(objs, faces, scene, motion_score=0.0)
        self.assertTrue(any(e["event"] == "OWNER_RECOGNIZED" for e in fired))
        self.assertIn("OWNER_RECOGNIZED", events)

        # Immediate re-evaluation should be debounced (no duplicate owner alert)
        fired2 = detector.evaluate_perception(objs, faces, scene, motion_score=0.0)
        self.assertFalse(any(e["event"] == "OWNER_RECOGNIZED" for e in fired2))
        print("[TEST 7] EventDetector debouncing passed.")

    def test_08_visual_reasoner(self):
        """Test natural language visual QA reasoning."""
        reasoner = VisualReasoner()
        perception = {
            "objects": [{"label": "phone", "confidence": 0.92, "location": {"x": 10, "y": 10, "width": 50, "height": 80}}],
            "faces": [{"identity": "owner", "name": "Abhinav", "confidence": 0.96}],
            "scene": {"environment": "desk_setup", "lighting": "normal", "people_count": 1},
            "gestures": [],
            "camera_active": True
        }

        # Query 1: "What am I holding?"
        res1 = reasoner.answer_visual_query("What am I holding?", perception)
        self.assertIn("phone", res1["natural_response"].lower())

        # Query 2: "Who do you see?"
        res2 = reasoner.answer_visual_query("Who do you see?", perception)
        self.assertIn("abhinav", res2["natural_response"].lower())

        # Query 3: "What do you see?"
        res3 = reasoner.answer_visual_query("What do you see?", perception)
        self.assertIn("abhinav", res3["natural_response"].lower())
        print("[TEST 8] VisualReasoner natural language Q&A passed.")

    def test_09_vision_controller_api(self):
        """Test high level VisionController API."""
        ctrl = VisionController.get_instance()
        telemetry = ctrl.get_telemetry()
        self.assertIn("camera", telemetry)
        self.assertIn("hardware", telemetry)
        
        # Test mode setting
        self.assertEqual(ctrl.set_mode("TURBO"), "TURBO")
        self.assertEqual(ctrl.set_mode("BALANCED"), "BALANCED")
        print("[TEST 9] VisionController API telemetry passed.")

    def test_10_agent_and_tool_integration(self):
        """Test VisionAgent and ToolRegistry integration."""
        agent = VisionAgent()
        msg = AgentMessage(
            sender="user",
            receiver="vision_agent",
            task_id="task-01",
            mission_id="m-01",
            message_type=AgentMessageType.REQUEST,
            payload={"action": "query", "query": "Describe what you see"}
        )
        resp = agent.process(msg)
        self.assertEqual(resp.status, "SUCCESS")

        # Verify tool registry contains vision tools
        tool = tool_registry.get_tool("vision_scanner")
        self.assertIsNotNone(tool)
        self.assertEqual(tool.name, "vision_scanner")
        print("[TEST 10] VisionAgent and ToolRegistry integration passed.")

    def test_11_skill_router_intents(self):
        """Test SkillRouter classification for vision intents."""
        q1 = "V.O.I.D., activate vision."
        d1 = skill_router.route(q1)
        self.assertEqual(d1.skill, SkillType.VISION)

        q2 = "What do you see?"
        d2 = skill_router.route(q2)
        self.assertEqual(d2.skill, SkillType.VISION)

        q3 = "What am I holding?"
        d3 = skill_router.route(q3)
        self.assertEqual(d3.skill, SkillType.VISION)

        q4 = "Turn off camera"
        d4 = skill_router.route(q4)
        self.assertEqual(d4.skill, SkillType.VISION)
    def test_12_standby_false_alarm_fix(self):
        """Test that active camera does NOT trigger false standby message even when objects/faces are empty."""
        reasoner = VisualReasoner()
        
        # Scenario A: Camera is active, but frame has no objects/faces yet
        empty_active_perception = {
            "objects": [],
            "faces": [],
            "scene": {"environment": "indoor", "lighting": "normal"},
            "gestures": [],
            "subject": {"detected": False},
            "camera_active": True
        }
        res_a = reasoner.answer_visual_query("what do you see?", empty_active_perception)
        self.assertNotIn("standby", res_a["natural_response"].lower())
        self.assertIn("clear", res_a["natural_response"].lower())

        # Scenario B: Perception nested inside a context dict
        nested_context = {
            "perception": {
                "objects": [],
                "faces": [],
                "scene": {"environment": "indoor", "lighting": "normal"},
                "camera_active": True
            }
        }
        res_b = reasoner.answer_visual_query("what do you see?", nested_context)
        self.assertNotIn("standby", res_b["natural_response"].lower())

        # Scenario C: "who am i" and "identify me" route to people reasoning
        res_c = reasoner.answer_visual_query("who am i", empty_active_perception)
        self.assertNotIn("standby", res_c["natural_response"].lower())
        self.assertIn("face", res_c["natural_response"].lower())

        # Scenario D: When camera is genuinely offline and not seeing, returns actionable status
        offline_perception = {
            "objects": [],
            "faces": [],
            "scene": {},
            "gestures": [],
            "camera_active": False
        }
        res_d = reasoner.answer_visual_query("what do you see?", offline_perception)
        self.assertIn("standby", res_d["natural_response"].lower())
        print("[TEST 12] False standby alarm prevention passed.")


if __name__ == "__main__":
    unittest.main()
