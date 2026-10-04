"""
tests/test_advanced_vision.py
Comprehensive unit & integration test suite for Advanced Vision Subsystems:
1. YOLO11 Neural Object Detection & Multi-Object Tracking (MOT with track_id & kinematics).
2. MediaPipe 3D Dense Face Mesh, EAR calculation, and canonical 5-point alignment.
3. ArcFace 512-d deep biometric embedding extraction and backwards compatibility.
4. Passive 3D Anti-Spoofing / Liveness Analyzer (micro-motion, blink EAR, texture analysis).
5. Dynamic Neural Model Switching.
6. Enriched Subject Dossier & Interaction Reasoning.
"""

import os
import sys
import unittest
import numpy as np
import cv2
import time

# Ensure project root in sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.models.model_manager import VisionModelManager, model_manager
from vision.recognition.object_detector import ObjectDetector
from vision.recognition.face_detector import FaceDetector, ARCFACE_CANONICAL_5PTS
from vision.recognition.face_recognition import FaceRecognizer, LivenessAnalyzer
from vision.recognition.subject_analyzer import SubjectAnalyzer
from vision.camera.frame_processor import FrameProcessor


class MockLandmark:
    def __init__(self, x: float, y: float, z: float = 0.0):
        self.x = x
        self.y = y
        self.z = z


class TestAdvancedVisionSystem(unittest.TestCase):

    def setUp(self):
        self.mgr = VisionModelManager.get_instance()
        # Synthetic 640x480 test frame
        self.test_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        # Add realistic color gradient and features
        for y in range(480):
            self.test_frame[y, :] = [int(y / 480 * 180), int(120 - y / 480 * 60), 100]
        # Draw face-like ellipse
        cv2.ellipse(self.test_frame, (320, 240), (70, 95), 0, 0, 360, (190, 170, 150), -1)
        # Eyes
        cv2.circle(self.test_frame, (295, 215), 10, (240, 240, 240), -1)
        cv2.circle(self.test_frame, (295, 215), 5, (40, 30, 20), -1)
        cv2.circle(self.test_frame, (345, 215), 10, (240, 240, 240), -1)
        cv2.circle(self.test_frame, (345, 215), 5, (40, 30, 20), -1)
        # Mouth
        cv2.ellipse(self.test_frame, (320, 290), (25, 10), 0, 0, 180, (60, 50, 120), -1)

    def test_01_yolo11_model_loading_and_tracking(self):
        """Test YOLO11 model loading, multi-object tracking (MOT), and kinematics."""
        detector = ObjectDetector()
        det_info = detector._model_mgr.load_object_detector()
        self.assertIsNotNone(det_info, "YOLO detector info failed to load")
        self.assertIn(det_info["type"], ["ultralytics_yolo", "ultralytics_yolo_world"])

        active_model = model_manager.get_active_object_model_name()
        print(f"[TEST 1] Active neural object model: {active_model}")
        self.assertTrue(any(k in active_model.lower() for k in ["yolo11", "yolov8", "world"]))

        # Test detection & MOT tracking on test frame
        results = detector.detect_objects(self.test_frame)
        self.assertIsInstance(results, list)
        print(f"[TEST 1] YOLO11 executed tracking on frame, found: {len(results)} items.")

        # Test tracker state kinematics
        tracker = detector._tracker
        mock_det = [{
            "label": "cell phone",
            "confidence": 0.88,
            "location": {"x": 200, "y": 150, "width": 80, "height": 120},
            "raw_track_id": 1
        }]
        t1 = tracker.update_tracks(mock_det, self.test_frame.shape)
        self.assertEqual(len(t1), 1)
        self.assertEqual(t1[0]["track_id"], "obj_#1")
        self.assertEqual(t1[0]["movement"]["status"], "STATIONARY")

        # Second update at offset position to test velocity
        mock_det2 = [{
            "label": "cell phone",
            "confidence": 0.90,
            "location": {"x": 230, "y": 170, "width": 80, "height": 120},
            "raw_track_id": 1
        }]
        time.sleep(0.05)
        t2 = tracker.update_tracks(mock_det2, self.test_frame.shape)
        self.assertEqual(len(t2), 1)
        self.assertGreater(t2[0]["dwell_time_sec"], 0.0)
        print(f"[TEST 1] MOT Kinematics verified: Speed={t2[0]['movement']['speed_px_s']}px/s, Dwell={t2[0]['dwell_time_sec']}s")

    def test_02_subject_object_interaction_correlation(self):
        """Test spatial correlation of held objects (e.g. phone, cup) with subject."""
        detector = ObjectDetector()
        faces = [{
            "location": {"x": 280, "y": 140, "width": 100, "height": 120},
            "identity": "owner"
        }]
        objects = [
            {
                "label": "cell phone",
                "confidence": 0.92,
                "location": {"x": 260, "y": 280, "width": 50, "height": 80}, # near chest/hands
                "track_id": "obj_#1",
                "movement": {"status": "Stationary", "speed_px_s": 0.0}
            },
            {
                "label": "chair",
                "confidence": 0.85,
                "location": {"x": 20, "y": 300, "width": 120, "height": 150}, # far away
                "track_id": "obj_#2",
                "movement": {"status": "Stationary", "speed_px_s": 0.0}
            }
        ]

        interactions = detector.correlate_interactions(objects, faces, self.test_frame.shape)
        print(f"[TEST 2] Objects processed with interaction reasoning: {len(interactions)}")
        self.assertEqual(len(interactions), 2)
        phone_int = next((i for i in interactions if i["label"] == "cell phone"), None)
        self.assertIsNotNone(phone_int)
        self.assertIsNotNone(phone_int.get("interaction"))
        self.assertTrue(phone_int["interaction"]["is_held"])
        self.assertIn("holding", phone_int["interaction"]["action"].lower())

    def test_03_mediapipe_3d_landmarks_and_alignment(self):
        """Test Eye Aspect Ratio (EAR), gaze estimation, and canonical 5-point alignment."""
        detector = FaceDetector()
        
        # Test EAR calculation with open vs closed eye landmarks
        open_eye_pts = [
            MockLandmark(0.10, 0.20), MockLandmark(0.15, 0.15), MockLandmark(0.25, 0.15),
            MockLandmark(0.30, 0.20), MockLandmark(0.25, 0.25), MockLandmark(0.15, 0.25)
        ]
        ear_open = detector._calculate_ear(open_eye_pts, [0, 1, 2, 3, 4, 5])
        self.assertGreater(ear_open, 0.25, f"Open eye EAR should be > 0.25, got {ear_open}")

        closed_eye_pts = [
            MockLandmark(0.10, 0.20), MockLandmark(0.15, 0.202), MockLandmark(0.25, 0.202),
            MockLandmark(0.30, 0.20), MockLandmark(0.25, 0.198), MockLandmark(0.15, 0.198)
        ]
        ear_closed = detector._calculate_ear(closed_eye_pts, [0, 1, 2, 3, 4, 5])
        self.assertLess(ear_closed, 0.15, f"Closed eye EAR should be < 0.15, got {ear_closed}")
        print(f"[TEST 3] EAR Open: {ear_open:.3f}, EAR Closed: {ear_closed:.3f}")

        # Test Canonical 5-point ArcFace similarity alignment matrix
        five_pts = np.array([
            [295.0, 215.0],  # left eye
            [345.0, 215.0],  # right eye
            [320.0, 250.0],  # nose tip
            [305.0, 285.0],  # mouth left
            [335.0, 285.0]   # mouth right
        ], dtype=np.float32)
        align_matrix, _ = cv2.estimateAffinePartial2D(five_pts, ARCFACE_CANONICAL_5PTS)
        self.assertEqual(align_matrix.shape, (2, 3), "Affine transformation matrix must be 2x3")
        warped = cv2.warpAffine(self.test_frame, align_matrix, (112, 112))
        self.assertEqual(warped.shape, (112, 112, 3), "ArcFace canonical crop must be 112x112x3")
        print("[TEST 3] Canonical 5-point ArcFace alignment matrix verified.")

    def test_04_arcface_512d_embeddings(self):
        """Test ArcFace 512-dimensional deep embedding extraction."""
        recognizer = FaceRecognizer()
        
        # Test extraction from 112x112 aligned face crop
        aligned_crop = cv2.resize(self.test_frame[160:320, 240:400], (112, 112))
        embedding = recognizer._compute_arcface_embedding(aligned_crop, full_frame=None, align_matrix=None)
        
        self.assertIsNotNone(embedding, "ArcFace embedding extraction failed")
        self.assertEqual(embedding.shape, (512,), f"Embedding must be 512-d, got {embedding.shape}")
        
        # Check L2 normalization
        norm = np.linalg.norm(embedding)
        self.assertAlmostEqual(norm, 1.0, places=2, msg="Embedding vector must be L2-normalized")
        print(f"[TEST 4] ArcFace embedding verified: 512-d, L2-norm={norm:.4f}")

        # Cosine similarity self-match
        sim_self = recognizer._cosine_similarity(embedding, embedding)
        self.assertAlmostEqual(sim_self, 1.0, places=3)

        # Cosine similarity with slightly perturbed vector
        noisy_embedding = embedding + np.random.normal(0, 0.02, 512)
        noisy_embedding = noisy_embedding / np.linalg.norm(noisy_embedding)
        sim_noisy = recognizer._cosine_similarity(embedding, noisy_embedding)
        self.assertGreater(sim_noisy, 0.85)
        print(f"[TEST 4] Cosine similarity self: {sim_self:.4f}, perturbed: {sim_noisy:.4f}")

    def test_05_passive_liveness_analyzer(self):
        """Test Passive 3D Anti-Spoofing / Liveness Analyzer."""
        analyzer = LivenessAnalyzer()
        
        # Scenario A: Genuine Live Subject (varying EAR, subtle head motion, sharp texture)
        face_crop = self.test_frame[180:300, 260:380]
        liveness_real = None
        for i in range(12):
            ear = 0.28 + 0.06 * np.sin(i * 0.8) # natural blink variation
            pose = {"pitch": float(np.sin(i * 0.5)), "yaw": float(np.cos(i * 0.5)), "roll": 0.0}
            liveness_real = analyzer.evaluate_liveness(
                track_key="test_subject",
                face_crop=face_crop,
                biometrics={"ear": ear},
                head_pose=pose
            )

        print(f"[TEST 5] Live subject evaluation: {liveness_real}")
        self.assertIn(liveness_real["status"], ["REAL", "VERIFYING"])
        self.assertGreater(liveness_real["score"], 0.45)

        # Scenario B: 2D Static Photo Replay Attack (zero motion delta, zero blink variation, flat texture)
        flat_photo = np.ones((120, 120, 3), dtype=np.uint8) * 128
        static_pose = {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}
        liveness_spoof = None
        for i in range(15):
            liveness_spoof = analyzer.evaluate_liveness(
                track_key="static_attacker",
                face_crop=flat_photo,
                biometrics={"ear": 0.30}, # static EAR
                head_pose=static_pose
            )

        print(f"[TEST 5] Static spoof evaluation: {liveness_spoof}")
        # Score must drop significantly compared to genuine subject
        self.assertLess(liveness_spoof["score"], liveness_real["score"])
        self.assertIn(liveness_spoof["status"], ["SPOOF_SUSPECTED", "VERIFYING"])

    def test_06_model_catalog_and_dynamic_switching(self):
        """Test model catalog retrieval and switching between YOLO11 and YOLOv8."""
        models = model_manager.get_available_vision_models()
        self.assertIn("object_detection", models)
        self.assertIn("face_detection", models)
        self.assertIn("face_recognition", models)
        print(f"[TEST 6] Available models catalog: {models['object_detection']}")

        # Test switching to YOLOv8
        switched = model_manager.set_object_detector_model("yolov8n.pt")
        self.assertTrue(switched)
        self.assertEqual(model_manager.get_active_object_model_name(), "yolov8n.pt")

        # Switch back to YOLO11
        switched_back = model_manager.set_object_detector_model("yolo11n.pt")
        self.assertTrue(switched_back)
        self.assertEqual(model_manager.get_active_object_model_name(), "yolo11n.pt")
        print("[TEST 6] Dynamic model switching between YOLOv8 and YOLO11 verified.")

    def test_07_subject_analyzer_enriched_telemetry(self):
        """Test SubjectAnalyzer real-time dossier extraction with 3D pose, fatigue, and held objects."""
        analyzer = SubjectAnalyzer()
        
        mock_faces = [{
            "identity": "owner",
            "name": "Abhinav",
            "confidence": 0.96,
            "track_id": "face_1",
            "location": {"x": 240, "y": 140, "width": 160, "height": 180},
            "head_pose": {"pitch": 2.5, "yaw": -4.0, "roll": 1.2},
            "gaze": {"direction": "CENTER"},
            "biometrics": {"ear": 0.32, "mar": 0.12},
            "liveness": {"status": "REAL", "score": 0.94, "reason": "Blink dynamics verified"},
            "blendshapes": {"mouthSmileLeft": 0.65, "mouthSmileRight": 0.60}
        }]
        
        mock_objects = [{
            "label": "cell phone",
            "confidence": 0.89,
            "track_id": "obj_#1",
            "location": {"x": 230, "y": 290, "width": 60, "height": 90},
            "is_held": True,
            "interaction": {"is_held": True, "action": "Holding phone in left hand"}
        }]

        dossier = analyzer.analyze_primary_subject(
            frame=self.test_frame,
            faces=mock_faces,
            objects=mock_objects,
            gestures=["resting"],
            motion_score=0.03
        )

        self.assertTrue(dossier["detected"])
        self.assertEqual(dossier["identity"]["name"], "Abhinav")
        self.assertEqual(dossier["identity"]["liveness"]["status"], "REAL")
        self.assertIn("euler_angles", dossier["cognitive_and_pose"])
        self.assertGreater(dossier["cognitive_and_pose"]["attention_score"], 80)
        self.assertIn("Smiling", dossier["cognitive_and_pose"]["mood"])
        self.assertGreaterEqual(len(dossier["vicinity_objects"]), 1)
        self.assertTrue(dossier["vicinity_objects"][0]["is_held"])
        print(f"[TEST 7] Subject Dossier Narrative: {dossier['natural_summary']}")

    def test_08_hud_overlay_drawing_with_mot_and_interactions(self):
        """Test FrameProcessor HUD rendering with trajectories, track IDs, and interactions."""
        faces = [{
            "identity": "owner",
            "name": "Abhinav",
            "track_id": "face_1",
            "confidence": 0.95,
            "location": {"x": 240, "y": 140, "width": 160, "height": 180},
            "liveness": {"status": "REAL", "score": 0.94},
            "mesh_3d": [[280, 180], [360, 180], [320, 220]]
        }]
        objects = [{
            "label": "laptop",
            "track_id": "obj_#1",
            "confidence": 0.91,
            "location": {"x": 80, "y": 280, "width": 160, "height": 120},
            "interaction": {"is_held": True, "action": "Working on laptop"}
        }]

        annotated = FrameProcessor.draw_hud_overlay(
            frame=self.test_frame.copy(),
            objects=objects,
            faces=faces,
            scene_info={"lighting": "normal", "environment": "indoor"},
            fps=30.0,
            mode="TURBO"
        )
        self.assertEqual(annotated.shape, self.test_frame.shape)
        # Verify HUD modification
        diff = cv2.absdiff(annotated, self.test_frame)
        self.assertGreater(np.count_nonzero(diff), 500)
        print("[TEST 8] HUD overlay with MOT tracks & interaction lines rendered successfully.")

    def test_09_open_vocabulary_yolo_world_dynamic_classes(self):
        """Test YOLO-World open-vocabulary loading, dynamic class injection, and inference."""
        switched = model_manager.set_object_detector_model("yolov8s-worldv2.pt")
        self.assertTrue(switched)
        self.assertTrue(model_manager.is_open_vocabulary_active())

        # Test dynamic class injection live in-memory
        custom_targets = ["coffee mug", "water bottle", "smartwatch", "pen", "keys"]
        res = model_manager.set_open_vocabulary_classes(custom_targets)
        self.assertTrue(res)
        self.assertEqual(model_manager.get_open_vocabulary_classes(), custom_targets)

        detector = ObjectDetector()
        results = detector.detect_objects(self.test_frame)
        self.assertIsInstance(results, list)
        print(f"[TEST 9] YOLO-World dynamic vocabulary ({len(custom_targets)} custom items) executed, detected: {len(results)} items.")

        # Test preset loading
        presets = model_manager.get_vocabulary_presets()
        self.assertIn("Desk & Office", presets)
        model_manager.set_open_vocabulary_classes(presets["Desk & Office"])
        self.assertEqual(len(model_manager.get_open_vocabulary_classes()), len(presets["Desk & Office"]))
        print(f"[TEST 9] Preset 'Desk & Office' loaded with {len(presets['Desk & Office'])} categories successfully.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
