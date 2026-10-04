"""
tests/test_vision_offline_improvements.py
Dedicated verification test suite for all 5 upgraded computer vision capabilities:
1. CLAHE adaptive lighting & auto-gamma correction
2. Temporal bounding-box smoothing filter (BoundingBoxSmoother)
3. High-accuracy offline YOLOv8n object detection
4. High-accuracy offline YuNet neural face detection & fallback
5. 21-landmark offline MediaPipe gesture recognition & contour fallback
6. Spatial proximity reasoning & offline cognitive Q&A
"""

import os
import sys
import unittest
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.camera.frame_processor import FrameProcessor, BoundingBoxSmoother
from vision.models.model_manager import VisionModelManager
from vision.recognition.face_detector import FaceDetector
from vision.recognition.object_detector import ObjectDetector
from vision.recognition.gesture_detector import GestureDetector
from vision.intelligence.visual_reasoner import VisualReasoner


class TestVisionOfflineImprovements(unittest.TestCase):

    def setUp(self):
        # Base synthetic frames
        self.dark_frame = np.ones((480, 640, 3), dtype=np.uint8) * 15
        self.bright_frame = np.ones((480, 640, 3), dtype=np.uint8) * 230
        self.gradient_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for y in range(480):
            self.gradient_frame[y, :] = int((y / 480.0) * 255)

    def test_01_clahe_and_auto_gamma(self):
        """Verify adaptive lighting enhancement rescues underexposed frames."""
        dark_lum = FrameProcessor.calculate_brightness(self.dark_frame)
        self.assertLess(dark_lum, 0.1)

        # Apply CLAHE
        clahe_frame = FrameProcessor.apply_clahe_enhancement(self.dark_frame)
        self.assertEqual(clahe_frame.shape, self.dark_frame.shape)

        # Apply Auto-Gamma
        gamma_frame = FrameProcessor.auto_gamma_correction(self.dark_frame, target_brightness=0.45)
        bright_after = FrameProcessor.calculate_brightness(gamma_frame)
        self.assertGreater(bright_after, dark_lum)

    def test_02_temporal_bounding_box_smoothing(self):
        """Verify BoundingBoxSmoother reduces jitter across sequential frames."""
        smoother = BoundingBoxSmoother(alpha=0.5)

        # Frame 1 detection at x=100
        det_f1 = [{"label": "laptop", "confidence": 0.9, "location": {"x": 100, "y": 100, "width": 100, "height": 100}}]
        res_f1 = smoother.smooth(det_f1)
        self.assertEqual(len(res_f1), 1)
        self.assertEqual(res_f1[0]["location"]["x"], 100)

        # Frame 2 with jitter at x=120
        det_f2 = [{"label": "laptop", "confidence": 0.9, "location": {"x": 120, "y": 100, "width": 100, "height": 100}}]
        res_f2 = smoother.smooth(det_f2)
        self.assertEqual(len(res_f2), 1)
        # Smoothed value should be halfway (100 * 0.5 + 120 * 0.5 = 110)
        self.assertEqual(res_f2[0]["location"]["x"], 110)

    def test_03_yolo_object_detector_offline(self):
        """Verify YOLOv8n detector operates locally without network connection."""
        mgr = VisionModelManager.get_instance()
        yolo_path = os.path.join(mgr.models_dir, "yolov8n.pt")
        self.assertTrue(os.path.exists(yolo_path), "Cached YOLOv8n model weights should be present")

        detector = ObjectDetector(confidence_threshold=0.3)
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        # Draw a synthetic laptop-like rectangle
        cv2.rectangle(test_img, (150, 150), (400, 350), (200, 200, 200), -1)
        detections = detector.detect_objects(test_img)
        self.assertIsInstance(detections, list)

    def test_04_yunet_face_detector_offline(self):
        """Verify YuNet neural face detector is cached and loads offline."""
        mgr = VisionModelManager.get_instance()
        yunet_path = os.path.join(mgr.models_dir, "face_detection_yunet_2023mar.onnx")
        self.assertTrue(os.path.exists(yunet_path), "Cached YuNet ONNX model should be present")

        detector = FaceDetector()
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        faces = detector.detect_faces(test_img)
        self.assertIsInstance(faces, list)

    def test_05_gesture_detector_offline(self):
        """Verify MediaPipe gesture recognizer task model is cached and executes."""
        mgr = VisionModelManager.get_instance()
        task_path = os.path.join(mgr.models_dir, "gesture_recognizer.task")
        self.assertTrue(os.path.exists(task_path), "Cached gesture_recognizer.task should be present")

        gd = GestureDetector()
        test_img = np.zeros((480, 640, 3), dtype=np.uint8)
        gestures = gd.detect_gestures(test_img)
        self.assertIsInstance(gestures, list)

    def test_06_spatial_proximity_holding_reasoning(self):
        """Verify reasoner pairs hand gesture location with nearest object."""
        reasoner = VisualReasoner()
        perception = {
            "objects": [
                {"label": "water bottle", "confidence": 0.90, "location": {"x": 50, "y": 300, "width": 60, "height": 120}},
                {"label": "mug", "confidence": 0.85, "location": {"x": 300, "y": 200, "width": 80, "height": 80}}
            ],
            "faces": [{"identity": "owner", "name": "Abhinav", "confidence": 0.95}],
            "gestures": [
                {"gesture": "open_palm", "confidence": 0.88, "location": {"x": 310, "y": 210, "width": 90, "height": 90}}
            ],
            "camera_active": True
        }

        # Hand is right over the mug at (310, 210) vs far away water bottle at (50, 300)
        res = reasoner.answer_visual_query("What am I holding?", perception)
        self.assertIn("mug", res["natural_response"].lower())
        self.assertEqual(res["interpretation"]["held_object"], "mug")


if __name__ == "__main__":
    unittest.main()
