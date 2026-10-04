"""
V.O.I.D. Vision Subsystem
Modular, local-first, futuristic computer vision and perception system.
"""

from vision.vision_controller import VisionController, vision_controller
from vision.camera.camera_manager import CameraManager
from vision.camera.frame_processor import FrameProcessor
from vision.camera.device_manager import DeviceManager
from vision.recognition.face_detector import FaceDetector
from vision.recognition.face_recognition import FaceRecognizer
from vision.recognition.object_detector import ObjectDetector
from vision.recognition.scene_analyzer import SceneAnalyzer
from vision.recognition.gesture_detector import GestureDetector
from vision.intelligence.visual_memory import VisualMemory
from vision.intelligence.event_detector import EventDetector, VISION_EVENTS
from vision.intelligence.visual_reasoner import VisualReasoner
from vision.models.model_manager import VisionModelManager, model_manager

__all__ = [
    "VisionController",
    "vision_controller",
    "CameraManager",
    "FrameProcessor",
    "DeviceManager",
    "FaceDetector",
    "FaceRecognizer",
    "ObjectDetector",
    "SceneAnalyzer",
    "GestureDetector",
    "VisualMemory",
    "EventDetector",
    "VISION_EVENTS",
    "VisualReasoner",
    "VisionModelManager",
    "model_manager"
]
