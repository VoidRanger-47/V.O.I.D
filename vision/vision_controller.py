"""
vision/vision_controller.py
Central controller and main API facade for the V.O.I.D. Vision Subsystem.
Orchestrates camera acquisition, models, recognition, scene analysis, visual memory,
event notifications, and cognitive reasoning.
"""

import time
import sys
import logging
import threading
import cv2
import numpy as np
from typing import Dict, Any, List, Optional, Generator

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.winmm.timeBeginPeriod(1)
    except Exception:
        pass

from vision.camera.camera_manager import CameraManager
from vision.camera.device_manager import DeviceManager
from vision.camera.frame_processor import FrameProcessor
from vision.models.model_manager import model_manager
from vision.recognition.face_detector import FaceDetector
from vision.recognition.face_recognition import FaceRecognizer
from vision.recognition.object_detector import ObjectDetector
from vision.recognition.scene_analyzer import SceneAnalyzer
from vision.recognition.gesture_detector import GestureDetector
from vision.recognition.subject_analyzer import subject_analyzer
from vision.intelligence.visual_memory import VisualMemory
from vision.intelligence.event_detector import EventDetector
from vision.intelligence.visual_reasoner import VisualReasoner

logger = logging.getLogger("void.vision.controller")

class VisionController:
    """
    Unified High-Level Interface for V.O.I.D. Vision.
    Accessed via void.vision or vision_controller instance.
    """
    _instance: Optional['VisionController'] = None

    def __init__(self):
        self.camera = CameraManager()
        self.device_mgr = DeviceManager()
        self.face_detector = FaceDetector()
        self.face_recognizer = FaceRecognizer()
        self.object_detector = ObjectDetector()
        self.gesture_detector = GestureDetector()
        self.subject_analyzer = subject_analyzer
        self.memory = VisualMemory()
        self.event_detector = EventDetector()
        self.reasoner = VisualReasoner(self.memory)

        self._analysis_thread: Optional[threading.Thread] = None
        self._obj_thread: Optional[threading.Thread] = None
        self._face_thread: Optional[threading.Thread] = None
        self._gest_thread: Optional[threading.Thread] = None
        self._is_analyzing = False
        self._last_perception_cache: Dict[str, Any] = {
            "objects": [],
            "faces": [],
            "scene": {},
            "gestures": [],
            "subject": {
                "detected": False,
                "status": "STANDBY_NO_CAMERA",
                "message": "Camera is offline. Access is granted on the dedicated vision page."
            },
            "camera_active": False,
            "timestamp": 0.0
        }
        self._perception_lock = threading.Lock()
        self._detection_fps = 0.0

        # Asynchronous multi-threaded perception pipelines
        self._async_lock = threading.Lock()
        self._async_objects: List[Dict[str, Any]] = []
        self._async_faces: List[Dict[str, Any]] = []
        self._async_gestures: List[Dict[str, Any]] = []

        # Connect event logger to visual memory
        self.event_detector.subscribe(self._on_vision_event)
        
        # Connect real-time HUD and detection FPS provider callbacks to camera manager
        self.camera.set_hud_provider(self._get_hud_annotations)
        self.camera.set_detection_fps_provider(self.get_detection_fps)
        logger.info("VisionController initialized.")

    def get_detection_fps(self) -> float:
        """Return the current background inference FPS."""
        with self._perception_lock:
            return float(self._detection_fps)

    def _get_hud_annotations(self) -> Dict[str, Any]:
        """Provide latest perception & hardware metrics to camera stream for real-time HUD rendering."""
        with self._perception_lock:
            cache = dict(self._last_perception_cache)
            det_fps = float(self._detection_fps)
        hw_stats = model_manager.get_hardware_telemetry()
        raw_objects = cache.get("objects", [])
        smoothed_objects = FrameProcessor.smooth_bounding_boxes(raw_objects) if raw_objects else []

        return {
            "objects": smoothed_objects,
            "faces": cache.get("faces", []),
            "scene": cache.get("scene", {}),
            "gestures": cache.get("gestures", []),
            "hardware": hw_stats,
            "detection_fps": det_fps
        }


    @classmethod
    def get_instance(cls) -> 'VisionController':
        if cls._instance is None:
            cls._instance = VisionController()
        return cls._instance

    def _on_vision_event(self, event_name: str, payload: Dict[str, Any]):
        """Store triggered vision events in visual memory."""
        person_name = payload.get("name") if ("OWNER" in event_name or "PERSON" in event_name) else None
        object_name = payload.get("new_objects")[0] if payload.get("new_objects") else None
        
        self.memory.record_observation(
            event_type=event_name,
            object_name=object_name,
            person_name=person_name,
            context="ambient_camera",
            confidence=payload.get("confidence", 1.0),
            importance=0.85 if ("OWNER" in event_name or "PERSON_RECOGNIZED" in event_name) else 0.5,
            metadata=payload
        )
        logger.info(f"Vision Event Triggered: {event_name} -> {payload}")

    # ==========================
    # CAMERA LIFECYCLE
    # ==========================
    def start(self, device_index: Optional[int] = None) -> bool:
        """Activate camera and asynchronous perception worker threads."""
        success = self.camera.start(device_index)
        if success:
            with self._perception_lock:
                self._last_perception_cache["camera_active"] = True
            if not self._is_analyzing:
                self._is_analyzing = True
                self._obj_thread = threading.Thread(
                    target=self._object_worker,
                    name="VOID-ObjectWorker",
                    daemon=True
                )
                self._face_thread = threading.Thread(
                    target=self._face_worker,
                    name="VOID-FaceWorker",
                    daemon=True
                )
                self._gest_thread = threading.Thread(
                    target=self._gesture_worker,
                    name="VOID-GestureWorker",
                    daemon=True
                )
                self._analysis_thread = threading.Thread(
                    target=self._perception_loop,
                    name="VOID-PerceptionThread",
                    daemon=True
                )
                self._obj_thread.start()
                self._face_thread.start()
                self._gest_thread.start()
                self._analysis_thread.start()
        return success

    def stop(self) -> bool:
        """Stop camera and perception analysis immediately."""
        self._is_analyzing = False
        threads = [self._analysis_thread, self._obj_thread, self._face_thread, self._gest_thread]
        for t in threads:
            if t and t.is_alive():
                t.join(timeout=0.8)
        self._analysis_thread = None
        self._obj_thread = None
        self._face_thread = None
        self._gest_thread = None

        with self._async_lock:
            self._async_objects = []
            self._async_faces = []
            self._async_gestures = []

        with self._perception_lock:
            self._detection_fps = 0.0
            self._last_perception_cache = {
                "objects": [],
                "faces": [],
                "scene": {},
                "gestures": [],
                "subject": {},
                "camera_active": False,
                "timestamp": time.time()
            }

        return self.camera.stop()

    def set_mode(self, mode_name: str) -> str:
        """Switch performance mode: ECO, BALANCED, or TURBO."""
        return self.camera.set_mode(mode_name)

    def get_devices(self) -> List[Dict[str, Any]]:
        """List available physical cameras."""
        return self.device_mgr.list_devices()

    def switch_device(self, index: int) -> bool:
        """Switch to another camera device."""
        return self.camera.switch_camera(index)

    # ==========================
    # ON-DEMAND PERCEPTION
    # ==========================
    def capture(self, auto_open: bool = True) -> Optional[np.ndarray]:
        """Capture latest single frame."""
        return self.camera.capture_frame(auto_open=auto_open)

    def detect_objects(self, frame: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
        """Run object detection on specified frame or current camera view."""
        if frame is None:
            frame = self.capture(auto_open=True)
        return self.object_detector.detect_objects(frame) if frame is not None else []

    def detect_people(self, frame: Optional[np.ndarray] = None) -> List[Dict[str, Any]]:
        """Run face and person detection on specified frame or current camera view."""
        if frame is None:
            frame = self.capture(auto_open=True)
        return self.face_recognizer.recognize_faces(frame) if frame is not None else []

    def analyze_scene(self, frame: Optional[np.ndarray] = None) -> Dict[str, Any]:
        """Run scene, lighting, and environmental analysis."""
        if frame is None:
            frame = self.capture(auto_open=True)
        if frame is None:
            return {"environment": "unknown", "lighting": "dark", "people_count": 0, "major_objects": [], "summary": "Camera unavailable"}
        
        objs = self.object_detector.detect_objects(frame)
        faces = self.face_recognizer.recognize_faces(frame)
        return SceneAnalyzer.analyze_scene(frame, objs, faces)

    def get_current_context(self) -> Dict[str, Any]:
        """Get structured summary of the current visual perception."""
        with self._perception_lock:
            cached = dict(self._last_perception_cache)

        # Synchronize dynamic hardware state
        cached["camera_active"] = self.camera.is_active

        if not self.camera.is_active:
            cached["subject"] = {
                "detected": False,
                "status": "STANDBY_NO_CAMERA",
                "message": "Camera hardware is offline. Access is granted only on the dedicated vision page."
            }

        telemetry = self.get_telemetry()
        return {
            "perception": cached,
            "telemetry": telemetry
        }

    def get_subject_telemetry(self) -> Dict[str, Any]:
        """Get the full real-time telemetry dossier of the primary subject in view."""
        with self._perception_lock:
            cached_subj = self._last_perception_cache.get("subject")
        if not self.camera.is_active or not cached_subj:
            return {
                "detected": False,
                "status": "STANDBY_NO_CAMERA",
                "message": "Camera hardware is offline. Access is granted only on the dedicated vision page."
            }
        return cached_subj

    def process_query(self, query: str) -> Dict[str, Any]:
        """Answer a natural language visual question."""
        current_ctx = self.get_current_context()
        perception = current_ctx["perception"]
        
        active_frame = None
        # 1. If camera is actively streaming, run fresh real-time inference on the active live frame
        if self.camera.is_active:
            live_frame = self.camera.capture_frame()
            if live_frame is not None:
                active_frame = live_frame
                faces = self.face_recognizer.recognize_faces(live_frame)
                objs = self.object_detector.detect_objects(live_frame)
                scene = SceneAnalyzer.analyze_scene(live_frame, objs, faces)
                gestures = self.gesture_detector.detect_gestures(live_frame)
                subject = self.subject_analyzer.analyze_primary_subject(
                    frame=live_frame,
                    faces=faces,
                    objects=objs,
                    gestures=gestures
                )
                perception = {
                    "objects": objs,
                    "faces": faces,
                    "scene": scene,
                    "gestures": gestures,
                    "subject": subject,
                    "camera_active": True,
                    "timestamp": time.time()
                }
        else:
            # 2. If camera is off, attempt on-demand snapshot if asked to see/inspect
            vision_words = ["see", "look", "holding", "scan", "what is this", "who is", "who am", "recognize", "identify", "wearing", "watching", "front of"]
            if any(w in query.lower() for w in vision_words):
                snap = self.capture(auto_open=True)
                if snap is not None:
                    active_frame = snap
                    objs = self.object_detector.detect_objects(snap)
                    faces = self.face_recognizer.recognize_faces(snap)
                    scene = SceneAnalyzer.analyze_scene(snap, objs, faces)
                    gestures = self.gesture_detector.detect_gestures(snap)
                    subject = self.subject_analyzer.analyze_primary_subject(
                        frame=snap,
                        faces=faces,
                        objects=objs,
                        gestures=gestures
                    )
                    perception = {
                        "objects": objs,
                        "faces": faces,
                        "scene": scene,
                        "gestures": gestures,
                        "subject": subject,
                        "camera_active": True,
                        "timestamp": time.time()
                    }

        return self.reasoner.answer_visual_query(query, perception, frame=active_frame)


    # ==========================
    # ENROLLMENT & PROFILES
    # ==========================
    def enroll_person(
        self,
        name: str,
        is_owner: bool = False,
        samples_count: int = 6,
        notes: str = ""
    ) -> Dict[str, Any]:
        """
        Enroll any person by name (e.g. 'Alice', 'Bob', 'Abhinav').
        Captures multi-angle face samples and generates an identity profile.
        """
        was_active = self.camera.is_active
        if not was_active:
            if not self.camera.start():
                return {"success": False, "error": "Could not open camera for enrollment."}
            time.sleep(0.5)

        crops = []
        full_frames = []
        raw_faces = []
        align_matrices = []
        for _ in range(samples_count * 5):
            frame = self.camera.capture_frame()
            if frame is not None:
                faces = self.face_detector.detect_faces(frame)
                if faces:
                    # Pick largest face in view for primary subject enrollment
                    best_face = max(faces, key=lambda f: f.get("location", {}).get("width", 0) * f.get("location", {}).get("height", 0))
                    if best_face.get("crop") is not None and best_face["crop"].size > 0:
                        crops.append(best_face["crop"])
                        full_frames.append(frame.copy())
                        raw_faces.append(best_face.get("raw"))
                        align_matrices.append(best_face.get("align_matrix"))
                        if len(crops) >= samples_count:
                            break
            time.sleep(0.12)

        if not was_active:
            self.camera.stop()

        if not crops:
            return {"success": False, "error": "No clear face detected in camera view during enrollment."}

        res = self.face_recognizer.enroll_profile(
            name=name,
            face_crops=crops,
            is_owner=is_owner,
            notes=notes,
            full_frames=full_frames,
            raw_faces=raw_faces,
            align_matrices=align_matrices
        )
        if res.get("success"):
            # Record initial enrollment in visual memory
            self.memory.record_person_sighting(
                person_name=name,
                confidence=1.0,
                context="initial_enrollment",
                metadata={"is_owner": is_owner, "samples": len(crops)}
            )
        return res

    def enroll_owner(self, name: str, samples_count: int = 6) -> Dict[str, Any]:
        """Opt-in owner enrollment shortcut."""
        return self.enroll_person(name=name, is_owner=True, samples_count=samples_count)

    def list_people(self) -> List[Dict[str, Any]]:
        """Return list of all enrolled people."""
        return self.face_recognizer.list_enrolled_profiles()

    def switch_object_model(self, model_name: str) -> bool:
        """Switch active object detection model (e.g. 'yolov8s-worldv2.pt', 'yolo11n.pt', 'yolov8n.pt')."""
        return model_manager.set_object_detector_model(model_name)

    def get_model_catalog(self) -> Dict[str, Any]:
        """Get inventory of available vision models and current active engines."""
        return model_manager.get_available_vision_models()

    def set_open_vocabulary(self, classes: List[str]) -> bool:
        """Update active open-vocabulary detection classes live in memory."""
        return model_manager.set_open_vocabulary_classes(classes)

    def get_open_vocabulary(self) -> List[str]:
        """Get currently active open-vocabulary classes."""
        return model_manager.get_open_vocabulary_classes()

    def get_vocabulary_presets(self) -> Dict[str, List[str]]:
        """Get curated open-vocabulary presets."""
        return model_manager.get_vocabulary_presets()

    def delete_person(self, profile_id: str) -> bool:
        """Delete an enrolled profile by ID."""
        return self.face_recognizer.delete_profile(profile_id)

    def rename_person(self, profile_id: str, new_name: str) -> bool:
        """Rename an enrolled profile."""
        return self.face_recognizer.rename_profile(profile_id, new_name)

    def get_people_seen_today(self) -> List[Dict[str, Any]]:
        """Get list of people seen today."""
        return self.memory.query_people_seen_today()

    def get_recent_memories(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent visual memory log."""
        return self.memory.query_recent(limit=limit)

    # ==========================
    # ASYNCHRONOUS PERCEPTION WORKERS
    # ==========================
    def _object_worker(self):
        """Dedicated high-throughput thread for YOLO-World / YOLO11 neural object detection (50-65 FPS on GPU)."""
        logger.info("VisionController: Object detection worker started.")
        while self._is_analyzing and self.camera.is_active:
            try:
                frame = self.camera.capture_frame()
                if frame is None or frame.size == 0:
                    time.sleep(0.005)
                    continue

                h, w = frame.shape[:2]
                scale = 0.5
                small_frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)

                # Fetch latest faces for interaction reasoning
                with self._async_lock:
                    faces_snapshot = list(self._async_faces)

                small_faces = []
                for f in faces_snapshot:
                    floc = f.get("location", {})
                    small_faces.append({
                        **f,
                        "location": {
                            "x": int(floc.get("x", 0) * scale),
                            "y": int(floc.get("y", 0) * scale),
                            "width": int(floc.get("width", 0) * scale),
                            "height": int(floc.get("height", 0) * scale)
                        }
                    })

                raw_objects = self.object_detector.detect_objects(small_frame, faces=small_faces)
                inv_scale = 1.0 / scale
                objects = []
                for obj in raw_objects:
                    loc = obj.get("location", {})
                    traj = obj.get("trajectory", [])
                    scaled_traj = [{"x": int(p["x"] * inv_scale), "y": int(p["y"] * inv_scale)} for p in traj]
                    objects.append({
                        **obj,
                        "location": {
                            "x": int(loc.get("x", 0) * inv_scale),
                            "y": int(loc.get("y", 0) * inv_scale),
                            "width": int(loc.get("width", 0) * inv_scale),
                            "height": int(loc.get("height", 0) * inv_scale)
                        },
                        "trajectory": scaled_traj
                    })

                with self._async_lock:
                    self._async_objects = objects

            except Exception as e:
                logger.debug(f"Object worker exception: {e}")
                time.sleep(0.01)

            time.sleep(0.001)
        logger.info("VisionController: Object detection worker stopped.")

    def _face_worker(self):
        """Dedicated high-speed thread for YuNet, ArcFace biometrics, and cadenced 3D Face Mesh (30-45 FPS)."""
        logger.info("VisionController: Face recognition worker started.")
        while self._is_analyzing and self.camera.is_active:
            try:
                frame = self.camera.capture_frame()
                if frame is None or frame.size == 0:
                    time.sleep(0.005)
                    continue

                faces = self.face_recognizer.recognize_faces(frame)
                with self._async_lock:
                    self._async_faces = faces

            except Exception as e:
                logger.debug(f"Face worker exception: {e}")
                time.sleep(0.01)

            time.sleep(0.002)
        logger.info("VisionController: Face recognition worker stopped.")

    def _gesture_worker(self):
        """Dedicated thread for MediaPipe 21-joint skeletal tracking and gestures (30-40 FPS)."""
        logger.info("VisionController: Gesture detection worker started.")
        while self._is_analyzing and self.camera.is_active:
            try:
                frame = self.camera.capture_frame()
                if frame is None or frame.size == 0:
                    time.sleep(0.005)
                    continue

                with self._async_lock:
                    faces_snapshot = list(self._async_faces)

                gestures = self.gesture_detector.detect_gestures(frame, faces=faces_snapshot)
                with self._async_lock:
                    self._async_gestures = gestures

            except Exception as e:
                logger.debug(f"Gesture worker exception: {e}")
                time.sleep(0.01)

            time.sleep(0.002)
        logger.info("VisionController: Gesture detection worker stopped.")

    # ==========================
    # BACKGROUND PERCEPTION FUSION LOOP
    # ==========================
    def _perception_loop(self):
        """Continuous master loop fusing asynchronous neural detections, kinematics, and HUD telemetry at 30-60 FPS."""
        fps_frame_count = 0
        last_fps_time = time.time()
        frame_idx = 0

        while self._is_analyzing and self.camera.is_active:
            loop_start = time.time()
            frame = self.camera.capture_frame()
            if frame is not None:
                try:
                    frame_idx += 1

                    # 1. Fetch latest asynchronous detections non-blockingly
                    with self._async_lock:
                        objects = list(self._async_objects)
                        faces = list(self._async_faces)
                        gestures = list(self._async_gestures)

                    # 2. Downscale 0.5x for scene analysis (<0.5ms)
                    h, w = frame.shape[:2]
                    scale = 0.5
                    small_frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)

                    cam_telemetry = self.camera.get_telemetry()
                    motion_score = cam_telemetry.get("last_motion_score", 0.0)
                    scene = SceneAnalyzer.analyze_scene(small_frame, objects, faces, motion_score)

                    # 3. Analyze primary subject in view (<0.3ms)
                    subject_data = self.subject_analyzer.analyze_primary_subject(
                        frame=frame,
                        faces=faces,
                        objects=objects,
                        gestures=gestures,
                        motion_score=motion_score
                    )

                    # Calculate master perception throughput FPS (0.5s interval)
                    fps_frame_count += 1
                    now = time.time()
                    dt = now - last_fps_time
                    if dt >= 0.5:
                        calc_fps = round(fps_frame_count / dt, 1)
                        fps_frame_count = 0
                        last_fps_time = now
                        with self._perception_lock:
                            self._detection_fps = calc_fps

                    # 4. Update cached state thread-safely
                    with self._perception_lock:
                        self._last_perception_cache = {
                            "objects": objects,
                            "faces": faces,
                            "scene": scene,
                            "gestures": gestures,
                            "subject": subject_data,
                            "camera_active": True,
                            "timestamp": time.time()
                        }

                    # 5. Evaluate visual events
                    self.event_detector.evaluate_perception(objects, faces, scene, motion_score)

                    # 6. Keep legacy annotated frame updated for snapshots periodically
                    if frame_idx % 30 == 0:
                        hw_stats = model_manager.get_hardware_telemetry()
                        annotated = FrameProcessor.draw_hud_overlay(
                            frame=frame,
                            objects=objects,
                            faces=faces,
                            scene_info=scene,
                            fps=cam_telemetry.get("actual_fps", 0.0),
                            mode=self.camera.mode,
                            hardware_info=hw_stats,
                            gestures=gestures,
                            detection_fps=self.get_detection_fps()
                        )
                        self.camera.update_annotated_frame(annotated)

                except Exception as e:
                    logger.error(f"Error in perception analysis loop: {e}")

            # Target Pacing: TURBO = 60 FPS (16.7ms), BALANCED = 30 FPS (33.3ms), ECO = 15 FPS (66.7ms)
            mode = self.camera.mode
            target_fps = 60 if mode == "TURBO" else 30 if mode == "BALANCED" else 15
            min_cycle_time = 1.0 / target_fps
            elapsed = time.time() - loop_start
            if elapsed < min_cycle_time:
                time.sleep(min_cycle_time - elapsed)
            else:
                time.sleep(0.001)

    def generate_feed(self, use_hud: bool = True) -> Generator[bytes, None, None]:
        """Stream MJPEG feed."""
        return self.camera.generate_mjpeg_stream(use_hud=use_hud)

    def get_telemetry(self) -> Dict[str, Any]:
        """Return combined camera and hardware telemetry."""
        cam_info = self.camera.get_telemetry()
        hw_info = model_manager.get_hardware_telemetry()
        return {
            "camera": cam_info,
            "hardware": hw_info,
            "detection_fps": self.get_detection_fps(),
            "enrolled_profiles": len(self.face_recognizer.list_enrolled_profiles()),
            "status": "active" if cam_info["active"] else "standby"
        }


# Global Singleton Instance
vision_controller = VisionController.get_instance()
