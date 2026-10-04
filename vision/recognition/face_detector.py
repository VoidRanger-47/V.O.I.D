"""
vision/recognition/face_detector.py
Advanced multi-tier neural face detection and 3D facial mesh perception.
Combines OpenCV YuNet ONNX, Google MediaPipe 478-Point 3D Face Landmarker,
52 Action Unit blendshapes, Euler angle head pose, and multi-scale cascade fallback.
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from vision.models.model_manager import model_manager

logger = logging.getLogger("void.vision.face_detector")

# Standard ArcFace 112x112 5-point alignment reference coordinates
ARCFACE_CANONICAL_5PTS = np.array([
    [38.2946, 51.6963],  # left eye
    [73.5318, 51.5014],  # right eye
    [56.0252, 71.7366],  # nose tip
    [41.5493, 92.3655],  # left mouth corner
    [70.7299, 92.2041]   # right mouth corner
], dtype=np.float32)


class FaceDetector:
    """
    Detects human faces with deep bounding boxes, 3D dense facial landmarks,
    52 action unit blendshapes, 3D head pose (Pitch/Yaw/Roll), and canonical
    affine alignment transforms for high-fidelity face recognition.
    """
    def __init__(self):
        self._model_mgr = model_manager
        self._counter = 0
        self._last_mesh_cache: List[Dict[str, Any]] = []

    def detect_faces(self, frame: np.ndarray, min_size: int = 24, fast_mode: bool = True) -> List[Dict[str, Any]]:
        """
        Detect faces in frame with high-throughput 60+ FPS scaling, 3D landmarks, and pose estimations.
        Returns list of structured detection dicts.
        """
        if frame is None or frame.size == 0:
            return []

        h, w = frame.shape[:2]
        detections: List[Dict[str, Any]] = []
        self._counter += 1

        # 1. Primary Pass: High-speed scaled YuNet neural detector (~3.8ms)
        use_downscale = fast_mode and (w > 320 or h > 240)
        target_w, target_h = (320, 240) if use_downscale else (w, h)
        scale_x = w / float(target_w)
        scale_y = h / float(target_h)

        yunet = self._model_mgr.load_yunet_face_detector(frame_width=target_w, frame_height=target_h, score_threshold=0.38)
        if yunet is not None:
            try:
                yunet.setInputSize((target_w, target_h))
                yunet.setScoreThreshold(0.38)
                detect_img = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_NEAREST) if use_downscale else frame
                _, faces_data = yunet.detect(detect_img)

                if (faces_data is None or len(faces_data) == 0) and not fast_mode:
                    enhanced_frame = self._enhance_illumination(detect_img)
                    _, faces_data = yunet.detect(enhanced_frame)

                if faces_data is not None and len(faces_data) > 0:
                    if use_downscale:
                        scaled_data = np.array(faces_data, copy=True)
                        scaled_data[:, [0, 2, 4, 6, 8, 10, 12]] *= scale_x
                        scaled_data[:, [1, 3, 5, 7, 9, 11, 13]] *= scale_y
                        detections = self._process_yunet_detections(scaled_data, frame, min_size)
                    else:
                        detections = self._process_yunet_detections(faces_data, frame, min_size)
            except Exception as e:
                logger.debug(f"YuNet inference exception: {e}")

        # 2. Secondary: Fallback to multi-scale Haar Cascades only when not in fast mode or periodic check
        if not detections and (not fast_mode or self._counter % 20 == 0):
            detections = self._detect_cascade_fallback(frame, min_size)

        # 3. Tertiary Biometric Enhancement: MediaPipe 3D Dense Face Mesh & Blendshapes (only on detected faces)
        if detections:
            # Cadence: On keyframes (every 2nd frame in fast mode or initial frame), run 3D landmarker;
            # on intermediate frames, smoothly carry forward previous mesh/gaze/pose attributes
            if not fast_mode or self._counter % 2 == 1 or not self._last_mesh_cache:
                detections = self._enrich_with_3d_landmarker(frame, detections, min_size)
                self._last_mesh_cache = detections
            else:
                detections = self._propagate_cached_mesh_attributes(detections, self._last_mesh_cache)

        return detections

    def _propagate_cached_mesh_attributes(self, detections: List[Dict[str, Any]], prev_cache: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Carry forward 3D mesh, blendshapes, and head pose from previous frame for intermediate cadenced frames."""
        for d in detections:
            loc = d.get("location", {})
            cx, cy = loc.get("x", 0) + loc.get("width", 0) // 2, loc.get("y", 0) + loc.get("height", 0) // 2
            best_match = None
            min_dist = float("inf")
            for prev in prev_cache:
                ploc = prev.get("location", {})
                pcx, pcy = ploc.get("x", 0) + ploc.get("width", 0) // 2, ploc.get("y", 0) + ploc.get("height", 0) // 2
                dist = np.hypot(cx - pcx, cy - pcy)
                if dist < max(loc.get("width", 50), 50) * 0.75 and dist < min_dist:
                    min_dist = dist
                    best_match = prev
            
            if best_match is not None:
                d["mesh_3d"] = best_match.get("mesh_3d")
                d["blendshapes"] = best_match.get("blendshapes", {})
                d["head_pose"] = best_match.get("head_pose", {"pitch": 0.0, "yaw": 0.0, "roll": 0.0})
                d["gaze"] = best_match.get("gaze", {"direction": "CENTER", "horizontal_ratio": 0.5, "vertical_ratio": 0.5})
                d["biometrics"] = best_match.get("biometrics", {"ear": 0.30, "mar": 0.05})
                if best_match.get("align_matrix") is not None and d.get("align_matrix") is None:
                    d["align_matrix"] = best_match.get("align_matrix")
        return detections

    def _enhance_illumination(self, frame: np.ndarray) -> np.ndarray:
        """Apply adaptive histogram equalization and auto-gamma to recover underexposed/backlit faces."""
        try:
            from vision.camera.frame_processor import FrameProcessor
            enhanced = FrameProcessor.apply_clahe_enhancement(frame)
            return FrameProcessor.auto_gamma_correction(enhanced, target_brightness=0.48)
        except Exception:
            return frame

    def _process_yunet_detections(self, faces_data: np.ndarray, frame: np.ndarray, min_size: int) -> List[Dict[str, Any]]:
        """Convert raw YuNet 15-float detection arrays into structured detection objects."""
        h, w = frame.shape[:2]
        results = []
        for face in faces_data:
            fx = max(0, int(round(face[0])))
            fy = max(0, int(round(face[1])))
            fw = min(w - fx, int(round(face[2])))
            fh = min(h - fy, int(round(face[3])))
            conf = round(float(face[14]), 2)

            if fw < min_size or fh < min_size:
                continue

            # Padding for natural framing
            pad_x = int(fw * 0.08)
            pad_y = int(fh * 0.08)
            nx = max(0, fx - pad_x)
            ny = max(0, fy - pad_y)
            nw = min(w - nx, fw + 2 * pad_x)
            nh = min(h - ny, fh + 2 * pad_y)

            crop = frame[ny:ny+nh, nx:nx+nw]

            # 5 canonical facial landmarks: right eye, left eye, nose tip, right mouth, left mouth
            landmarks = [
                (int(round(face[4])), int(round(face[5]))),
                (int(round(face[6])), int(round(face[7]))),
                (int(round(face[8])), int(round(face[9]))),
                (int(round(face[10])), int(round(face[11]))),
                (int(round(face[12])), int(round(face[13])))
            ]

            # 5-point alignment transformation matrix for deep face recognition
            src_5pts = np.array(landmarks, dtype=np.float32)
            align_matrix, _ = cv2.estimateAffinePartial2D(src_5pts, ARCFACE_CANONICAL_5PTS)

            results.append({
                "location": {"x": nx, "y": ny, "width": nw, "height": nh},
                "confidence": conf,
                "crop": crop,
                "landmarks": landmarks,
                "raw": np.array(face, copy=True),
                "align_matrix": align_matrix,
                "mesh_3d": None,
                "blendshapes": {},
                "head_pose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "gaze": {"direction": "CENTER", "horizontal_ratio": 0.5, "vertical_ratio": 0.5},
                "biometrics": {"ear": 0.30, "mar": 0.05}
            })

        return results

    def _detect_cascade_fallback(self, frame: np.ndarray, min_size: int = 24) -> List[Dict[str, Any]]:
        """Multi-scale cascade fallback for legacy or synthetic frame testing."""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        norm_gray = clahe.apply(gray)
        
        h, w = frame.shape[:2]
        effective_min_size = min_size if w > 360 else max(16, int(min_size * (w / 640.0)))
        
        detector = self._model_mgr.load_face_detector()
        
        faces_rects = detector.detectMultiScale(
            norm_gray,
            scaleFactor=1.1,
            minNeighbors=4,
            minSize=(effective_min_size, effective_min_size),
            flags=cv2.CASCADE_SCALE_IMAGE
        )

        if len(faces_rects) == 0:
            profile_detector = self._model_mgr.load_profile_face_detector()
            if profile_detector is not None:
                p_rects = profile_detector.detectMultiScale(
                    norm_gray,
                    scaleFactor=1.1,
                    minNeighbors=3,
                    minSize=(effective_min_size, effective_min_size)
                )
                if len(p_rects) > 0:
                    faces_rects = p_rects

        results = []
        for (x, y, bw, bh) in faces_rects:
            pad_x = int(bw * 0.08)
            pad_y = int(bh * 0.08)
            nx = max(0, x - pad_x)
            ny = max(0, y - pad_y)
            nw = min(w - nx, bw + 2 * pad_x)
            nh = min(h - ny, bh + 2 * pad_y)

            crop = frame[ny:ny+nh, nx:nx+nw]
            aspect_ratio = float(bw) / float(max(bh, 1))
            aspect_score = 1.0 - min(abs(aspect_ratio - 1.0), 0.5)
            size_score = min(float(bw * bh) / (60 * 60), 1.0)
            confidence = round(0.78 + (aspect_score * 0.12) + (size_score * 0.08), 2)

            results.append({
                "location": {"x": nx, "y": ny, "width": nw, "height": nh},
                "confidence": confidence,
                "crop": crop,
                "landmarks": [],
                "raw": None,
                "align_matrix": None,
                "mesh_3d": None,
                "blendshapes": {},
                "head_pose": {"pitch": 0.0, "yaw": 0.0, "roll": 0.0},
                "gaze": {"direction": "CENTER", "horizontal_ratio": 0.5, "vertical_ratio": 0.5},
                "biometrics": {"ear": 0.30, "mar": 0.05}
            })

        return results

    def _enrich_with_3d_landmarker(
        self,
        frame: np.ndarray,
        detections: List[Dict[str, Any]],
        min_size: int
    ) -> List[Dict[str, Any]]:
        """
        Enrich faces with dense 478 3D landmarks, blendshapes, head pose Euler angles,
        and gaze vectors via MediaPipe FaceLandmarker.
        """
        landmarker = self._model_mgr.load_face_landmarker()
        if landmarker is None or not detections:
            return detections

        h, w = frame.shape[:2]
        try:
            import mediapipe as mp
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            landmarker_result = landmarker.detect(mp_image)
        except Exception as e:
            logger.debug(f"MediaPipe FaceLandmarker detection skipped: {e}")
            return detections

        if not landmarker_result or not landmarker_result.face_landmarks:
            return detections

        for i, landmarks_list in enumerate(landmarker_result.face_landmarks):
            pts_px = [(int(round(pt.x * w)), int(round(pt.y * h)), float(pt.z * w)) for pt in landmarks_list]
            
            # Compute 2D bounding box from mesh
            xs = [p[0] for p in pts_px]
            ys = [p[1] for p in pts_px]
            min_x, max_x = max(0, min(xs)), min(w, max(xs))
            min_y, max_y = max(0, min(ys)), min(h, max(ys))
            mesh_w, mesh_h = max_x - min_x, max_y - min_y

            if mesh_w < min_size or mesh_h < min_size:
                continue

            # Extract blendshapes
            blendshapes = {}
            if landmarker_result.face_blendshapes and i < len(landmarker_result.face_blendshapes):
                for category in landmarker_result.face_blendshapes[i]:
                    blendshapes[category.category_name] = round(float(category.score), 3)

            # Compute Head Pose Euler Angles from 4x4 matrix
            pitch, yaw, roll = 0.0, 0.0, 0.0
            if landmarker_result.facial_transformation_matrixes and i < len(landmarker_result.facial_transformation_matrixes):
                mat = landmarker_result.facial_transformation_matrixes[i]
                if hasattr(mat, "shape") and mat.shape == (4, 4):
                    R = mat[:3, :3]
                elif len(mat) >= 16:
                    R = np.array(mat, dtype=np.float32).reshape((4, 4))[:3, :3]
                else:
                    R = None
                
                if R is not None:
                    try:
                        angles, _, _, _, _, _ = cv2.RQDecomp3x3(R)
                        pitch, yaw, roll = round(float(angles[0]), 1), round(float(angles[1]), 1), round(float(angles[2]), 1)
                    except Exception:
                        pass

            # Calculate Eye Aspect Ratio (EAR) for blink detection
            ear_left = self._calculate_ear(landmarks_list, [33, 160, 158, 133, 153, 144])
            ear_right = self._calculate_ear(landmarks_list, [362, 385, 387, 263, 373, 380])
            avg_ear = round(float((ear_left + ear_right) / 2.0), 3)

            # Calculate Mouth Aspect Ratio (MAR)
            mar = self._calculate_mar(landmarks_list, 13, 14, 78, 308)

            # Estimate Gaze Direction
            gaze_dir = self._estimate_gaze_direction(blendshapes, yaw, pitch)

            # 5 Key landmarks: Left Eye (468), Right Eye (473), Nose Tip (1), Left Mouth (61), Right Mouth (291)
            p_right_eye = (pts_px[33][0], pts_px[33][1])
            p_left_eye = (pts_px[263][0], pts_px[263][1])
            p_nose = (pts_px[1][0], pts_px[1][1])
            p_mouth_r = (pts_px[61][0], pts_px[61][1])
            p_mouth_l = (pts_px[291][0], pts_px[291][1])
            dense_5pts = [p_right_eye, p_left_eye, p_nose, p_mouth_r, p_mouth_l]

            # Sample key contour points for visual HUD rendering (silhouette, eyes, lips)
            key_mesh_indices = [
                10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
                397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
                172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
                33, 160, 158, 133, 153, 144, 362, 385, 387, 263, 373, 380,
                1, 2, 98, 327, 61, 146, 91, 181, 84, 17, 314, 405, 321, 375, 291
            ]
            sampled_mesh = [{"x": pts_px[idx][0], "y": pts_px[idx][1]} for idx in key_mesh_indices if idx < len(pts_px)]

            # Associate with existing detection or create new one
            matched_det = None
            mesh_cx, mesh_cy = min_x + mesh_w // 2, min_y + mesh_h // 2
            for d in detections:
                loc = d["location"]
                dcx, dcy = loc["x"] + loc["width"] // 2, loc["y"] + loc["height"] // 2
                dist = np.sqrt((mesh_cx - dcx) ** 2 + (mesh_cy - dcy) ** 2)
                if dist < max(loc["width"], mesh_w) * 0.65:
                    matched_det = d
                    break

            align_matrix, _ = cv2.estimateAffinePartial2D(np.array(dense_5pts, dtype=np.float32), ARCFACE_CANONICAL_5PTS)

            if matched_det is not None:
                matched_det["landmarks"] = dense_5pts
                matched_det["mesh_3d"] = sampled_mesh
                matched_det["blendshapes"] = blendshapes
                matched_det["head_pose"] = {"pitch": pitch, "yaw": yaw, "roll": roll}
                matched_det["gaze"] = gaze_dir
                matched_det["biometrics"] = {"ear": avg_ear, "mar": mar}
                if align_matrix is not None:
                    matched_det["align_matrix"] = align_matrix
            else:
                # Add new detection discovered by dense 3D mesh
                pad_x = int(mesh_w * 0.08)
                pad_y = int(mesh_h * 0.08)
                nx = max(0, min_x - pad_x)
                ny = max(0, min_y - pad_y)
                nw = min(w - nx, mesh_w + 2 * pad_x)
                nh = min(h - ny, mesh_h + 2 * pad_y)
                crop = frame[ny:ny+nh, nx:nx+nw]

                detections.append({
                    "location": {"x": nx, "y": ny, "width": nw, "height": nh},
                    "confidence": 0.95,
                    "crop": crop,
                    "landmarks": dense_5pts,
                    "raw": None,
                    "align_matrix": align_matrix,
                    "mesh_3d": sampled_mesh,
                    "blendshapes": blendshapes,
                    "head_pose": {"pitch": pitch, "yaw": yaw, "roll": roll},
                    "gaze": gaze_dir,
                    "biometrics": {"ear": avg_ear, "mar": mar}
                })

        return detections

    def _calculate_ear(self, landmarks_list, indices: List[int]) -> float:
        """Eye Aspect Ratio (EAR) based on vertical vs horizontal distances between eye landmarks."""
        try:
            p1, p2, p3, p4, p5, p6 = [landmarks_list[i] for i in indices]
            # Vertical distances
            d_v1 = np.sqrt((p2.x - p6.x)**2 + (p2.y - p6.y)**2)
            d_v2 = np.sqrt((p3.x - p5.x)**2 + (p3.y - p5.y)**2)
            # Horizontal distance
            d_h = np.sqrt((p1.x - p4.x)**2 + (p1.y - p4.y)**2)
            if d_h < 1e-5:
                return 0.3
            return float((d_v1 + d_v2) / (2.0 * d_h))
        except Exception:
            return 0.3

    def _calculate_mar(self, landmarks_list, top_idx: int, bot_idx: int, left_idx: int, right_idx: int) -> float:
        """Mouth Aspect Ratio (MAR) based on lip aperture vs mouth width."""
        try:
            top = landmarks_list[top_idx]
            bot = landmarks_list[bot_idx]
            left = landmarks_list[left_idx]
            right = landmarks_list[right_idx]
            d_v = np.sqrt((top.x - bot.x)**2 + (top.y - bot.y)**2)
            d_h = np.sqrt((left.x - right.x)**2 + (left.y - right.y)**2)
            if d_h < 1e-5:
                return 0.05
            return round(float(d_v / d_h), 3)
        except Exception:
            return 0.05

    def _estimate_gaze_direction(self, blendshapes: Dict[str, float], yaw: float, pitch: float) -> Dict[str, Any]:
        """Estimate whether the subject is looking at screen or looking away."""
        look_left = blendshapes.get("eyeLookOutLeft", 0.0) + blendshapes.get("eyeLookInRight", 0.0)
        look_right = blendshapes.get("eyeLookInLeft", 0.0) + blendshapes.get("eyeLookOutRight", 0.0)
        look_up = (blendshapes.get("eyeLookUpLeft", 0.0) + blendshapes.get("eyeLookUpRight", 0.0)) / 2.0
        look_down = (blendshapes.get("eyeLookDownLeft", 0.0) + blendshapes.get("eyeLookDownRight", 0.0)) / 2.0

        if abs(yaw) > 28.0 or abs(pitch) > 25.0:
            direction = "LOOKING_AWAY"
        elif look_left > 0.45 or yaw > 16.0:
            direction = "LOOKING_LEFT"
        elif look_right > 0.45 or yaw < -16.0:
            direction = "LOOKING_RIGHT"
        elif look_down > 0.50 or pitch < -18.0:
            direction = "LOOKING_DOWN"
        elif look_up > 0.50 or pitch > 18.0:
            direction = "LOOKING_UP"
        else:
            direction = "CENTER"

        return {
            "direction": direction,
            "horizontal_ratio": round(float(0.5 + (look_right - look_left) * 0.5), 2),
            "vertical_ratio": round(float(0.5 + (look_up - look_down) * 0.5), 2)
        }

