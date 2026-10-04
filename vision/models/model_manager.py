"""
vision/models/model_manager.py
Centralized model manager supporting on-demand lazy loading, CPU/GPU acceleration,
model caching, and offline-first vision inference.
"""

import os
import torch
import cv2
import psutil
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger("void.vision.model_manager")

VOCABULARY_PRESETS: Dict[str, List[str]] = {
    "Everyday Carry": [
        "keys", "keychain", "wallet", "purse", "backpack", "credit card", "passport", "id badge",
        "cell phone", "smartphone", "smartwatch", "wristwatch", "headphones", "earbuds",
        "charging cable", "eyeglasses", "sunglasses", "jacket", "umbrella"
    ],
    "Desk & Office": [
        "laptop", "computer mouse", "keyboard", "tablet", "monitor", "webcam", "coffee mug",
        "water bottle", "pen", "pencil", "notebook", "book", "paper", "sticky note",
        "scissors", "stapler", "calculator", "desk lamp", "marker", "folder"
    ],
    "Tech & Electronics": [
        "cell phone", "laptop", "tablet", "computer mouse", "keyboard", "headphones",
        "earbuds", "charging cable", "power bank", "charger", "remote control", "smartwatch",
        "usb drive", "monitor", "speaker", "microphone", "game controller"
    ],
    "Tools & Hardware": [
        "screwdriver", "wrench", "pliers", "hammer", "flashlight", "tape measure",
        "box cutter", "scissors", "drill", "multimeter", "soldering iron", "screws"
    ],
    "Food & Drinkware": [
        "coffee mug", "water bottle", "cup", "thermos", "tumbler", "drinking glass",
        "beverage can", "soda can", "bowl", "plate", "fork", "knife", "spoon",
        "apple", "banana", "sandwich", "snack bag"
    ]
}

# Aggregate unified open vocabulary: 100+ fine-grained real world objects
DEFAULT_OPEN_VOCABULARY: List[str] = sorted(list({
    # EDC & Valuables
    "keys", "keychain", "wallet", "purse", "backpack", "credit card", "passport", "id badge",
    # Personal Tech & Devices
    "cell phone", "smartphone", "smartwatch", "wristwatch", "laptop", "tablet", "computer mouse",
    "keyboard", "headphones", "earbuds", "charging cable", "power bank", "charger", "remote control",
    "stylus", "usb drive", "monitor", "webcam", "microphone", "speaker", "game controller",
    # Desk & Office Supplies
    "pen", "pencil", "notebook", "book", "paper", "sticky note", "scissors", "stapler",
    "ruler", "eraser", "calculator", "tape", "folder", "clipboard", "desk lamp", "marker",
    # Drinkware & Containers
    "coffee mug", "water bottle", "thermos", "tumbler", "drinking glass", "cup", "can",
    "beverage can", "soda can", "bowl", "plate", "fork", "knife", "spoon", "straw",
    # Eyewear & Accessories
    "eyeglasses", "sunglasses", "hat", "cap", "jacket", "coat", "scarf", "gloves",
    "ring", "bracelet", "necklace", "umbrella",
    # Daily Tools, First Aid & Personal Care
    "pill bottle", "medicine bottle", "lip balm", "hand sanitizer", "tissue box",
    "screwdriver", "wrench", "pliers", "hammer", "flashlight", "tape measure", "box cutter",
    # Room Fixtures & Common Elements
    "chair", "desk", "table", "door", "window", "trash can", "clock", "fan", "plant", "person"
}))

class VisionModelManager:
    """
    Manages lifecycle, memory allocation, and inference devices (CPU/CUDA)
    for all local vision neural networks and computer vision models.
    """
    _instance: Optional['VisionModelManager'] = None

    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.use_gpu = torch.cuda.is_available()
        self._models: Dict[str, Any] = {}
        self._models_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "models")
        os.makedirs(self._models_dir, exist_ok=True)
        self._open_vocabulary: List[str] = list(DEFAULT_OPEN_VOCABULARY)
        logger.info(f"VisionModelManager initialized. Device: {self.device} (GPU: {self.use_gpu})")

    @classmethod
    def get_instance(cls) -> 'VisionModelManager':
        if cls._instance is None:
            cls._instance = VisionModelManager()
        return cls._instance

    @property
    def models_dir(self) -> str:
        return self._models_dir

    def get_hardware_telemetry(self) -> Dict[str, Any]:
        """Collect current system hardware telemetry (CPU, RAM, GPU VRAM)."""
        cpu_pct = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory()
        
        gpu_info = {
            "gpu_available": self.use_gpu,
            "gpu_name": torch.cuda.get_device_name(0) if self.use_gpu else "N/A (CPU Mode)",
            "gpu_vram_used_mb": round(torch.cuda.memory_allocated(0) / (1024 * 1024), 1) if self.use_gpu else 0,
            "gpu_vram_total_mb": round(torch.cuda.get_device_properties(0).total_memory / (1024 * 1024), 1) if self.use_gpu else 0
        }

        return {
            "cpu_percent": cpu_pct,
            "ram_used_mb": round(ram.used / (1024 * 1024), 1),
            "ram_percent": ram.percent,
            **gpu_info
        }

    def load_yunet_face_detector(self, frame_width: int = 320, frame_height: int = 240, score_threshold: float = 0.45) -> Optional[Any]:
        """Load local YuNet ONNX neural face detector if present with adaptive score threshold."""
        model_path = os.path.join(self._models_dir, "face_detection_yunet_2023mar.onnx")
        if not os.path.exists(model_path):
            return None

        if "yunet_detector" not in self._models:
            try:
                detector = cv2.FaceDetectorYN.create(
                    model_path,
                    "",
                    (frame_width, frame_height),
                    score_threshold=score_threshold,
                    nms_threshold=0.3,
                    top_k=5000
                )
                self._models["yunet_detector"] = detector
                logger.info(f"OpenCV YuNet face detector loaded from {model_path} (score_thresh={score_threshold}).")
            except Exception as e:
                logger.warning(f"Failed to initialize YuNet face detector: {e}")
                return None

        detector = self._models.get("yunet_detector")
        if detector is not None:
            detector.setInputSize((frame_width, frame_height))
            detector.setScoreThreshold(score_threshold)
        return detector

    def load_sface_recognizer(self) -> Optional[Any]:
        """Load local SFace deep neural face recognition network if present."""
        model_path = os.path.join(self._models_dir, "face_recognition_sface_2021dec.onnx")
        if not os.path.exists(model_path):
            return None

        if "sface_recognizer" not in self._models:
            try:
                recognizer = cv2.FaceRecognizerSF.create(model_path, "")
                self._models["sface_recognizer"] = recognizer
                logger.info(f"OpenCV SFace deep neural face recognizer loaded from {model_path}.")
            except Exception as e:
                logger.warning(f"Failed to initialize SFace recognizer: {e}")
                return None

        return self._models.get("sface_recognizer")

    def load_face_detector(self) -> Any:
        """Load local face detector cascade."""
        if "face_cascade" not in self._models:
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if not os.path.exists(cascade_path):
                raise FileNotFoundError(f"OpenCV cascade not found at {cascade_path}")
            detector = cv2.CascadeClassifier(cascade_path)
            self._models["face_cascade"] = detector
            logger.info("Face detector cascade loaded.")
        return self._models["face_cascade"]

    def load_profile_face_detector(self) -> Any:
        """Load local profile face detector cascade."""
        if "profile_face_cascade" not in self._models:
            cascade_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
            if os.path.exists(cascade_path):
                self._models["profile_face_cascade"] = cv2.CascadeClassifier(cascade_path)
        return self._models.get("profile_face_cascade")

    def load_fullbody_detector(self) -> Any:
        """Load local fullbody / person detector cascade."""
        if "fullbody_cascade" not in self._models:
            cascade_path = cv2.data.haarcascades + "haarcascade_fullbody.xml"
            if os.path.exists(cascade_path):
                self._models["fullbody_cascade"] = cv2.CascadeClassifier(cascade_path)
        return self._models.get("fullbody_cascade")

    def load_upperbody_detector(self) -> Any:
        """Load local upperbody detector cascade."""
        if "upperbody_cascade" not in self._models:
            cascade_path = cv2.data.haarcascades + "haarcascade_upperbody.xml"
            if os.path.exists(cascade_path):
                self._models["upperbody_cascade"] = cv2.CascadeClassifier(cascade_path)
        return self._models.get("upperbody_cascade")

    def load_face_landmarker(self) -> Optional[Any]:
        """
        Load MediaPipe FaceLandmarker with 478 3D landmarks and 52 Action Unit blendshapes.
        Provides high-fidelity facial geometry, gaze tracking, eye aspect ratios, and head pose.
        """
        task_path = os.path.join(self._models_dir, "face_landmarker.task")
        if not os.path.exists(task_path):
            return None

        if "face_landmarker" not in self._models:
            try:
                import mediapipe as mp
                from mediapipe.tasks.python import vision
                from mediapipe.tasks.python import BaseOptions

                options = vision.FaceLandmarkerOptions(
                    base_options=BaseOptions(model_asset_path=task_path),
                    output_face_blendshapes=True,
                    output_facial_transformation_matrixes=True,
                    num_faces=4,
                    running_mode=vision.RunningMode.IMAGE
                )
                landmarker = vision.FaceLandmarker.create_from_options(options)
                self._models["face_landmarker"] = landmarker
                logger.info("MediaPipe 3D FaceLandmarker loaded successfully with 52 blendshapes.")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe FaceLandmarker: {e}")
                return None

        return self._models.get("face_landmarker")

    def load_arcface_recognizer(self) -> Optional[Any]:
        """
        Load local ArcFace (ResNet/MobileFaceNet) 512-dimensional deep face embedding network
        using ONNX Runtime with CUDA / CPU execution providers.
        """
        model_paths = [
            os.path.join(self._models_dir, "arcface.onnx"),
            os.path.join(self._models_dir, "arcface_w600k_r50.onnx"),
            os.path.join(self._models_dir, "w600k_r50.onnx")
        ]
        target_path = next((p for p in model_paths if os.path.exists(p)), None)
        if not target_path:
            return None

        if "arcface_recognizer" not in self._models:
            try:
                # On Windows, register PyTorch CUDA libraries (cublas, cudnn) for ONNX Runtime
                try:
                    import torch
                    torch_lib = os.path.join(os.path.dirname(torch.__file__), 'lib')
                    if os.path.exists(torch_lib):
                        if hasattr(os, 'add_dll_directory'):
                            os.add_dll_directory(torch_lib)
                        if torch_lib not in os.environ.get('PATH', ''):
                            os.environ['PATH'] = torch_lib + os.pathsep + os.environ.get('PATH', '')
                except Exception:
                    pass

                import onnxruntime as ort
                providers = ['CUDAExecutionProvider', 'CPUExecutionProvider'] if self.use_gpu else ['CPUExecutionProvider']
                session = ort.InferenceSession(target_path, providers=providers)
                input_name = session.get_inputs()[0].name
                output_name = session.get_outputs()[0].name
                self._models["arcface_recognizer"] = {
                    "session": session,
                    "input_name": input_name,
                    "output_name": output_name,
                    "path": target_path
                }
                logger.info(f"ArcFace 512-d recognizer loaded from {target_path} (providers={session.get_providers()}).")
            except Exception as e:
                logger.warning(f"Failed to initialize ArcFace recognizer: {e}")
                return None

        return self._models.get("arcface_recognizer")

    def set_object_detector_model(self, model_name: str) -> bool:
        """
        Switch active YOLO model (e.g. 'yolov8s-worldv2.pt', 'yolo11n.pt', 'yolov8n.pt').
        Supports instant Open-Vocabulary YOLO-World and standard COCO models.
        """
        clean_name = os.path.basename(model_name).strip()
        local_path = os.path.join(self._models_dir, clean_name)
        weight_target = local_path if os.path.exists(local_path) else clean_name
        device_str = "0" if self.use_gpu else "cpu"
        
        try:
            if "world" in clean_name.lower():
                from ultralytics import YOLOWorld
                world_model = YOLOWorld(weight_target)
                if self._open_vocabulary:
                    world_model.set_classes(self._open_vocabulary)
                self._models["object_detector"] = {
                    "type": "ultralytics_yolo_world",
                    "model_name": clean_name,
                    "model": world_model,
                    "device": device_str,
                    "categories": world_model.names if hasattr(world_model, "names") else {i: c for i, c in enumerate(self._open_vocabulary)}
                }
                logger.info(f"Open-Vocabulary YOLO-World activated: {clean_name} ({len(self._open_vocabulary)} classes on {device_str}).")
            else:
                from ultralytics import YOLO
                yolo_model = YOLO(weight_target)
                self._models["object_detector"] = {
                    "type": "ultralytics_yolo",
                    "model_name": clean_name,
                    "model": yolo_model,
                    "device": device_str,
                    "categories": yolo_model.names
                }
                logger.info(f"Standard YOLO activated: {clean_name} on {device_str}.")
            return True
        except Exception as e:
            logger.error(f"Failed to switch object detector to {clean_name}: {e}")
            return False

    def set_open_vocabulary_classes(self, custom_classes: List[str]) -> bool:
        """
        Dynamically update detection vocabulary in-memory without retraining.
        Affects active YOLO-World model instantly.
        """
        cleaned = [c.strip().lower() for c in custom_classes if c and c.strip()]
        if not cleaned:
            logger.warning("Empty custom classes list provided to set_open_vocabulary_classes.")
            return False

        self._open_vocabulary = cleaned
        current = self._models.get("object_detector", {})
        if current.get("type") == "ultralytics_yolo_world":
            try:
                model = current["model"]
                model.set_classes(self._open_vocabulary)
                current["categories"] = model.names if hasattr(model, "names") else {i: c for i, c in enumerate(self._open_vocabulary)}
                logger.info(f"YOLO-World dynamic vocabulary updated to {len(self._open_vocabulary)} classes: {self._open_vocabulary[:8]}...")
                return True
            except Exception as e:
                logger.error(f"Failed to update YOLO-World custom classes: {e}")
                return False
        return True

    def get_open_vocabulary_classes(self) -> List[str]:
        """Return the current active open-vocabulary classes."""
        return list(self._open_vocabulary)

    def get_vocabulary_presets(self) -> Dict[str, List[str]]:
        """Return curated vocabulary presets."""
        return dict(VOCABULARY_PRESETS)

    def is_open_vocabulary_active(self) -> bool:
        """Check if currently active object detector is open-vocabulary YOLO-World."""
        current = self._models.get("object_detector", {})
        return current.get("type") == "ultralytics_yolo_world"

    def get_active_object_model_name(self) -> str:
        """Return the filename of the active object detector model."""
        current_obj_detector = self._models.get("object_detector", {})
        if "model_name" in current_obj_detector:
            return current_obj_detector["model_name"]
        available_yolos = [f for f in os.listdir(self._models_dir) if f.endswith(".pt") and "yolo" in f.lower()]
        if "yolov8s-worldv2.pt" in available_yolos:
            return "yolov8s-worldv2.pt"
        return "yolo11n.pt" if "yolo11n.pt" in available_yolos else "yolov8n.pt"

    def get_available_vision_models(self) -> Dict[str, Any]:
        """Inspect available local model weights and active configurations."""
        available_files = [f for f in os.listdir(self._models_dir) if f.endswith(".pt") and "yolo" in f.lower()]
        current_obj_detector = self._models.get("object_detector", {})
        active_yolo = current_obj_detector.get("model_name", self.get_active_object_model_name())

        # Build detailed model list for UI dropdown
        model_list = []
        for f in available_files:
            fpath = os.path.join(self._models_dir, f)
            size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 1) if os.path.exists(fpath) else 0.0
            is_world = "world" in f.lower()
            label = f"{f} (Open-Vocab 2M+ Objects)" if is_world else f"{f} (COCO-80 Standard)"
            model_list.append({
                "filename": f,
                "label": label,
                "size_mb": size_mb,
                "is_open_vocabulary": is_world,
                "active": (f == active_yolo)
            })

        return {
            "object_detection": {
                "active_model": active_yolo,
                "available_models": available_files,
                "available_object_models": model_list,
                "detector_type": current_obj_detector.get("type", "ultralytics_yolo_world" if "world" in active_yolo.lower() else "ultralytics_yolo"),
                "accelerator": "CUDA (NVIDIA GPU)" if self.use_gpu else "CPU",
                "is_open_vocabulary": "world" in active_yolo.lower(),
                "active_vocabulary_count": len(self._open_vocabulary),
                "active_vocabulary": self._open_vocabulary,
                "presets": VOCABULARY_PRESETS
            },
            "face_detection": {
                "yunet_2d": os.path.exists(os.path.join(self._models_dir, "face_detection_yunet_2023mar.onnx")),
                "mediapipe_3d_mesh": os.path.exists(os.path.join(self._models_dir, "face_landmarker.task")),
                "active_engine": "MediaPipe 3D Mesh + YuNet Hybrid"
            },
            "face_recognition": {
                "sface_128d": os.path.exists(os.path.join(self._models_dir, "face_recognition_sface_2021dec.onnx")),
                "arcface_512d": any(os.path.exists(os.path.join(self._models_dir, n)) for n in ["arcface.onnx", "arcface_w600k_r50.onnx"]),
                "active_engine": "ArcFace 512-d + SFace 128-d Dual Pipeline"
            }
        }

    def load_object_detector(self) -> Any:
        """
        Load high-performance local object detector.
        Priority:
        1. Ultralytics YOLO-World v2 (Open-Vocabulary 2M+ categories on CUDA GPU)
        2. Ultralytics YOLO11 / YOLOv8 (CUDA / CPU with cached weights)
        3. TorchVision MobileNetV3 SSDLite
        4. OpenCV Fallback
        """
        if "object_detector" not in self._models:
            preferred_models = ["yolov8s-worldv2.pt", "yolo11n.pt", "yolov8n.pt"]
            for model_file in preferred_models:
                yolo_weights = os.path.join(self._models_dir, model_file)
                if os.path.exists(yolo_weights):
                    device_str = "0" if self.use_gpu else "cpu"
                    try:
                        if "world" in model_file.lower():
                            from ultralytics import YOLOWorld
                            world_model = YOLOWorld(yolo_weights)
                            if self._open_vocabulary:
                                world_model.set_classes(self._open_vocabulary)
                            self._models["object_detector"] = {
                                "type": "ultralytics_yolo_world",
                                "model_name": model_file,
                                "model": world_model,
                                "device": device_str,
                                "categories": world_model.names if hasattr(world_model, "names") else {i: c for i, c in enumerate(self._open_vocabulary)}
                            }
                            logger.info(f"Open-Vocabulary YOLO-World loaded from {yolo_weights} ({len(self._open_vocabulary)} classes on {device_str}).")
                            return self._models["object_detector"]
                        else:
                            from ultralytics import YOLO
                            yolo_model = YOLO(yolo_weights)
                            self._models["object_detector"] = {
                                "type": "ultralytics_yolo",
                                "model_name": model_file,
                                "model": yolo_model,
                                "device": device_str,
                                "categories": yolo_model.names
                            }
                            logger.info(f"YOLO object detector loaded from {yolo_weights} (Device: {device_str}).")
                            return self._models["object_detector"]
                    except Exception as e:
                        logger.warning(f"Could not load local {model_file} model: {e}")

            # 2. Try TorchVision SSDLite
            try:
                import torchvision.models.detection as detection
                try:
                    weights = detection.SSDLite320_MobileNet_V3_Large_Weights.DEFAULT
                    model = detection.ssdlite320_mobilenet_v3_large(weights=weights)
                    model.eval().to(self.device)
                    self._models["object_detector"] = {
                        "type": "torchvision_ssdlite",
                        "model": model,
                        "transforms": weights.transforms(),
                        "categories": weights.meta["categories"]
                    }
                    logger.info(f"TorchVision SSDLite object detector loaded onto {self.device}.")
                    return self._models["object_detector"]
                except Exception as e:
                    logger.warning(f"Could not load TorchVision weights ({e}), fallback to OpenCV.")
            except Exception as e:
                logger.warning(f"Torchvision detection unavailable ({e}), fallback to OpenCV.")

            # 3. OpenCV fallback
            self._models["object_detector"] = {"type": "opencv_fallback"}

        return self._models["object_detector"]

    def load_gesture_recognizer(self) -> Optional[Any]:
        """Load MediaPipe GestureRecognizer if available."""
        task_path = os.path.join(self._models_dir, "gesture_recognizer.task")
        if not os.path.exists(task_path):
            return None

        if "gesture_recognizer" not in self._models:
            try:
                import mediapipe as mp
                from mediapipe.tasks.python import vision
                from mediapipe.tasks.python import BaseOptions

                options = vision.GestureRecognizerOptions(
                    base_options=BaseOptions(model_asset_path=task_path),
                    running_mode=vision.RunningMode.IMAGE,
                    num_hands=2,
                    min_hand_detection_confidence=0.5,
                    min_hand_presence_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                recognizer = vision.GestureRecognizer.create_from_options(options)
                self._models["gesture_recognizer"] = recognizer
                logger.info("MediaPipe GestureRecognizer loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to initialize MediaPipe GestureRecognizer: {e}")
                return None

        return self._models.get("gesture_recognizer")

    def unload_unused_models(self):
        """Unload models to free system RAM and GPU VRAM."""
        keys = list(self._models.keys())
        for k in keys:
            del self._models[k]
        if self.use_gpu:
            torch.cuda.empty_cache()
        logger.info(f"Unloaded all models ({len(keys)} freed).")


model_manager = VisionModelManager.get_instance()
