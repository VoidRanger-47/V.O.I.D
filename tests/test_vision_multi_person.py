"""
tests/test_vision_multi_person.py
Unit and integration tests for multi-person recognition, object detection,
persistent visual memory, and cognitive visual reasoning in V.O.I.D.
"""

import os
import sys
import shutil
import tempfile
import unittest
import numpy as np
import cv2

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from vision.recognition.face_recognition import FaceRecognizer
from vision.recognition.object_detector import ObjectDetector
from vision.intelligence.visual_memory import VisualMemory
from vision.intelligence.visual_reasoner import VisualReasoner
from vision.intelligence.event_detector import EventDetector
from core.agents.vision_agent import VisionAgent
from core.agents.protocol import AgentMessage, AgentMessageType, AgentPriority


def create_synthetic_face(person_id: int = 1, sample_variant: int = 0) -> np.ndarray:
    """Create a synthetic 96x96 face crop image with distinct facial features per person."""
    np.random.seed(person_id * 100 + sample_variant)
    face = np.full((96, 96, 3), 160 + (person_id % 3) * 20, dtype=np.uint8)
    
    if person_id == 1:
        # Person 1 (Alice): round face, high eyes, small mouth, bangs
        cv2.circle(face, (28, 30), 7, (20, 20, 20), -1)
        cv2.circle(face, (68, 30), 7, (20, 20, 20), -1)
        cv2.line(face, (48, 35), (48, 52), (40, 40, 40), 2)
        cv2.ellipse(face, (48, 68), (14, 6), 0, 0, 180, (30, 30, 30), 2)
        cv2.rectangle(face, (10, 10), (86, 24), (30, 20, 10), -1)
    else:
        # Person 2 (Owner): lower eyes, wider mouth, beard contour
        cv2.circle(face, (34, 44), 9, (20, 20, 20), -1)
        cv2.circle(face, (62, 44), 9, (20, 20, 20), -1)
        cv2.line(face, (48, 46), (48, 64), (40, 40, 40), 3)
        cv2.ellipse(face, (48, 76), (22, 10), 0, 0, 180, (30, 30, 30), 3)
        cv2.ellipse(face, (48, 82), (32, 12), 0, 0, 180, (20, 20, 20), -1)

    noise = (np.random.rand(96, 96, 3) * 10).astype(np.uint8)
    return cv2.add(face, noise)


class TestMultiPersonFaceRecognition(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_multi_person_enrollment_and_matching(self):
        profiles_file = os.path.join(self.temp_dir, "profiles.json")
        recognizer = FaceRecognizer(profiles_path=profiles_file)

        # 1. Enroll Alice (person_id=1)
        alice_crops = [create_synthetic_face(person_id=1, sample_variant=i) for i in range(4)]
        res_alice = recognizer.enroll_person("Alice", alice_crops, is_owner=False)
        self.assertTrue(res_alice["success"])
        self.assertEqual(res_alice["name"], "Alice")

        # 2. Enroll Owner (person_id=2)
        owner_crops = [create_synthetic_face(person_id=2, sample_variant=i) for i in range(4)]
        res_owner = recognizer.enroll_person("Abhinav", owner_crops, is_owner=True)
        self.assertTrue(res_owner["success"])
        self.assertTrue(res_owner["is_owner"])

        # 3. Verify enrolled profiles listing
        profiles = recognizer.list_enrolled_profiles()
        self.assertEqual(len(profiles), 2)
        names = [p["name"] for p in profiles]
        self.assertIn("Alice", names)
        self.assertIn("Abhinav", names)

        # 4. Compute embeddings and verify discrimination
        emb_alice = recognizer.compute_face_embedding(alice_crops[0])
        emb_owner = recognizer.compute_face_embedding(owner_crops[0])
        emb_alice_test = recognizer.compute_face_embedding(alice_crops[1])

        sim_same = float(np.dot(emb_alice, emb_alice_test))
        sim_diff = float(np.dot(emb_alice, emb_owner))

        self.assertGreater(sim_same, 0.85)
        self.assertGreater(sim_same, sim_diff)

        # 5. Test deletion
        deleted = recognizer.delete_profile("alice")
        self.assertTrue(deleted)
        self.assertEqual(len(recognizer.list_enrolled_profiles()), 1)

    def test_owner_vs_stranger_discrimination(self):
        """Verify that when only the owner is enrolled, strangers are NOT falsely recognized as the owner."""
        profiles_file = os.path.join(self.temp_dir, "profiles_discrim.json")
        recognizer = FaceRecognizer(profiles_path=profiles_file)

        # Enroll Owner
        owner_crops = [create_synthetic_face(person_id=2, sample_variant=i) for i in range(5)]
        res_owner = recognizer.enroll_person("Abhinav", owner_crops, is_owner=True)
        self.assertTrue(res_owner["success"])

        # Construct a frame with a stranger face (person_id=1)
        stranger_crop = create_synthetic_face(person_id=1, sample_variant=0)
        stranger_frame = np.full((300, 300, 3), 220, dtype=np.uint8)
        # Place stranger crop at (50, 50)
        stranger_frame[50:146, 50:146] = stranger_crop

        # Also construct frame with owner face
        owner_test_crop = create_synthetic_face(person_id=2, sample_variant=6)
        owner_frame = np.full((300, 300, 3), 220, dtype=np.uint8)
        owner_frame[50:146, 50:146] = owner_test_crop

        # Test embedding similarity directly
        emb_owner_enrolled = np.array(recognizer._profiles["abhinav"]["embedding"], dtype=np.float32)
        emb_owner_test = recognizer.compute_face_embedding(owner_test_crop)
        emb_stranger = recognizer.compute_face_embedding(stranger_crop)

        sim_owner = float(np.dot(emb_owner_enrolled, emb_owner_test))
        sim_stranger = float(np.dot(emb_owner_enrolled, emb_stranger))

        # Owner must have higher similarity than stranger
        self.assertGreater(sim_owner, sim_stranger)
        self.assertGreater(sim_owner, 0.85)




class TestObjectDetectorAndNMS(unittest.TestCase):
    def test_object_detector_initialization_and_nms(self):
        detector = ObjectDetector(confidence_threshold=0.35)
        
        # Test NMS
        duplicate_boxes = [
            {"label": "phone", "confidence": 0.90, "location": {"x": 100, "y": 100, "width": 50, "height": 80}},
            {"label": "phone", "confidence": 0.85, "location": {"x": 102, "y": 101, "width": 48, "height": 79}},
            {"label": "bottle", "confidence": 0.75, "location": {"x": 300, "y": 200, "width": 40, "height": 100}}
        ]
        filtered = detector._apply_nms(duplicate_boxes)
        self.assertEqual(len(filtered), 2)
        labels = [d["label"] for d in filtered]
        self.assertIn("phone", labels)
        self.assertIn("bottle", labels)


class TestVisualMemory(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_visual_memory_people_and_objects(self):
        db_file = os.path.join(self.temp_dir, "observations.db")
        memory = VisualMemory(db_path=db_file)

        # Record sightings
        memory.record_person_sighting("Alice", confidence=0.92, context="office_room")
        memory.record_person_sighting("Bob", confidence=0.88, context="meeting_area")
        memory.record_observation(event_type="OBJECT_DETECTED", object_name="laptop", context="desk_1")
        memory.record_observation(event_type="OBJECT_DETECTED", object_name="phone", context="desk_1")

        # Query history
        alice_history = memory.query_person_history("Alice")
        self.assertGreaterEqual(len(alice_history), 1)
        self.assertEqual(alice_history[0]["person"], "Alice")

        # Query today's people
        people_today = memory.query_people_seen_today()
        names = [p["name"] for p in people_today]
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

        # Query objects
        laptop_obs = memory.query_by_object("laptop")
        self.assertGreaterEqual(len(laptop_obs), 1)
        self.assertEqual(laptop_obs[0]["object"], "laptop")

        last_phone = memory.query_last_seen_object("phone")
        self.assertIsNotNone(last_phone)
        self.assertEqual(last_phone["object"], "phone")


class TestVisualReasoner(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_reasoning_about_people_and_memory(self):
        db_file = os.path.join(self.temp_dir, "observations.db")
        memory = VisualMemory(db_path=db_file)
        memory.record_person_sighting("Alice", confidence=0.95, context="desk")
        memory.record_observation(event_type="OBJECT_DETECTED", object_name="headphones", context="table")

        reasoner = VisualReasoner(visual_memory=memory)

        # 1. Ask about Alice
        res_alice = reasoner.answer_visual_query("Did you see Alice earlier?", {})
        self.assertIn("Alice", res_alice["natural_response"])
        self.assertIn("desk", res_alice["natural_response"])

        # 2. Ask about visitors
        res_visitors = reasoner.answer_visual_query("Who have you seen today?", {})
        self.assertIn("Alice", res_visitors["natural_response"])

        # 3. Ask about object
        res_headphones = reasoner.answer_visual_query("Where is my headphones?", {})
        self.assertIn("headphones", res_headphones["natural_response"])


class TestVisionAgentActions(unittest.TestCase):
    def test_vision_agent_message_protocol(self):
        agent = VisionAgent()

        # 1. List enrolled profiles
        msg = AgentMessage(
            sender="executive",
            receiver="vision_agent",
            message_type=AgentMessageType.REQUEST,
            priority=AgentPriority.NORMAL,
            goal="List people",
            task_id="task_1",
            payload={"action": "list_people"}
        )
        resp = agent.process(msg)
        self.assertEqual(resp.status, "SUCCESS")
        self.assertIn("profiles", resp.payload)

        # 2. Query today's visitors
        msg_visitors = AgentMessage(
            sender="executive",
            receiver="vision_agent",
            message_type=AgentMessageType.REQUEST,
            priority=AgentPriority.NORMAL,
            goal="Check visitors",
            task_id="task_2",
            payload={"action": "people_seen_today"}
        )
        resp_visitors = agent.process(msg_visitors)
        self.assertEqual(resp_visitors.status, "SUCCESS")
        self.assertIn("people_today", resp_visitors.payload)


if __name__ == "__main__":
    unittest.main()
