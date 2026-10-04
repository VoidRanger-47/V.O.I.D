"""
vision/recognition/gesture_detector.py
Extensible gesture and 21-landmark 3D hand tracking using modern Google MediaPipe
with robust offline morphology and convexity defect fallback.
"""

import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional
from vision.models.model_manager import model_manager

logger = logging.getLogger("void.vision.gesture_detector")

class GestureDetector:
    """
    Detects hands and human gestures (open palm, pointing, thumbs up, peace sign, fist)
    in real-time webcam frames with bounding boxes and confidence metrics.
    """

    GESTURE_MAPPINGS = {
        "open_palm": "open_palm",
        "pointing_up": "pointing",
        "thumb_up": "thumbs_up",
        "thumb_down": "thumbs_down",
        "victory": "peace",
        "closed_fist": "fist",
        "iloveyou": "rock_on",
        "none": "hand_present"
    }

    def __init__(self):
        self._model_mgr = model_manager

    def detect_gestures(self, frame: np.ndarray, faces: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Detect hands and gestures in the frame.
        Returns structured list:
        [
            {
                "gesture": "open_palm" | "pointing" | "thumbs_up" | "peace" | "fist" | "hand_present",
                "confidence": float,
                "location": {"x": int, "y": int, "width": int, "height": int},
                "landmarks": [{"x": int, "y": int, "z": float}, ...],
                "handedness": "Left" | "Right"
            }
        ]
        """
        if frame is None or frame.size == 0:
            return []

        # 1. Primary: Try MediaPipe GestureRecognizer
        recognizer = self._model_mgr.load_gesture_recognizer()
        if recognizer is not None:
            try:
                import mediapipe as mp
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
                results = recognizer.recognize(mp_img)

                gestures_out = []
                h, w = frame.shape[:2]

                if results.gestures and len(results.gestures) > 0:
                    for idx, hand_gestures in enumerate(results.gestures):
                        if not hand_gestures:
                            continue
                        top_g = hand_gestures[0]
                        raw_cat = top_g.category_name.lower().replace(" ", "_")
                        mapped_name = self.GESTURE_MAPPINGS.get(raw_cat, "hand_present")
                        conf = float(top_g.score)

                        # Bounding box & 21 3D Landmarks
                        box = {"x": 0, "y": 0, "width": 0, "height": 0}
                        landmarks_out = []
                        if results.hand_landmarks and idx < len(results.hand_landmarks):
                            lms = results.hand_landmarks[idx]
                            xs = [lm.x * w for lm in lms]
                            ys = [lm.y * h for lm in lms]
                            min_x = max(0, int(min(xs)))
                            min_y = max(0, int(min(ys)))
                            max_x = min(w, int(max(xs)))
                            max_y = min(h, int(max(ys)))
                            pad = int((max_x - min_x) * 0.15)
                            box = {
                                "x": max(0, min_x - pad),
                                "y": max(0, min_y - pad),
                                "width": min(w, (max_x - min_x) + 2 * pad),
                                "height": min(h, (max_y - min_y) + 2 * pad)
                            }
                            landmarks_out = [{"x": int(x), "y": int(y), "z": float(lm.z)} for x, y, lm in zip(xs, ys, lms)]

                        # Handedness (Left / Right)
                        handedness = "Hand"
                        if results.handedness and idx < len(results.handedness):
                            top_h = results.handedness[idx][0]
                            handedness = top_h.category_name

                        gestures_out.append({
                            "gesture": mapped_name,
                            "confidence": round(conf, 2),
                            "handedness": handedness,
                            "location": box,
                            "landmarks": landmarks_out
                        })

                # If MediaPipe neural model is loaded and ran successfully,
                # return its detected gestures directly (empty list if no hand is in view).
                # NEVER fall through to skin-color contour fallback when neural model is active!
                return gestures_out

            except Exception as e:
                logger.debug(f"MediaPipe gesture recognition fallback: {e}")

        # 2. Secondary: Fallback to skin & edge morphological contour analysis ONLY if MediaPipe is unavailable
        return self._detect_contour_fallback(frame, faces=faces)

    def _detect_contour_fallback(self, frame: np.ndarray, faces: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Adaptive lighting invariant skin-color and convexity defect gesture analyzer (offline fallback)."""
        h, w = frame.shape[:2]
        ycrcb = cv2.cvtColor(frame, cv2.COLOR_BGR2YCrCb)
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        mask = cv2.inRange(ycrcb, lower_skin, upper_skin)

        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        mask = cv2.erode(mask, kernel, iterations=1)
        mask = cv2.dilate(mask, kernel, iterations=2)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        gestures = []

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if area < (w * h * 0.02) or area > (w * h * 0.35):
                continue

            x, y, bw, bh = cv2.boundingRect(cnt)
            aspect = float(bw) / float(bh) if bh > 0 else 0
            if aspect < 0.3 or aspect > 2.5:
                continue

            # Reject contours that overlap with faces or upper torso to avoid false ghost hands
            if faces:
                cx, cy = x + bw // 2, y + bh // 2
                is_face_overlap = False
                for f in faces:
                    floc = f.get("location", {})
                    fx, fy = floc.get("x", 0), floc.get("y", 0)
                    fw, fh = floc.get("width", 0), floc.get("height", 0)
                    if (fx - 30) <= cx <= (fx + fw + 30) and (fy - 30) <= cy <= (fy + fh + int(fh * 0.8)):
                        is_face_overlap = True
                        break
                if is_face_overlap:
                    continue

            hull = cv2.convexHull(cnt, returnPoints=False)
            if len(hull) > 3 and len(cnt) > 3:
                try:
                    defects = cv2.convexityDefects(cnt, hull)
                    finger_count = 0
                    if defects is not None:
                        for i in range(defects.shape[0]):
                            s, e, f, d = defects[i, 0]
                            start = cnt[s][0]
                            end = cnt[e][0]
                            far = cnt[f][0]

                            a = np.linalg.norm(end - start)
                            b = np.linalg.norm(far - start)
                            c = np.linalg.norm(end - far)
                            angle = np.arccos(np.clip((b**2 + c**2 - a**2) / (2*b*c + 1e-6), -1.0, 1.0))

                            if angle <= np.pi / 2 and d > 2000:
                                finger_count += 1

                    # Require at least 1 clear finger defect to prevent flat blobs from becoming hands
                    if finger_count < 1:
                        continue

                    if finger_count >= 3:
                        gesture_name = "open_palm"
                        confidence = 0.85
                    elif finger_count == 1:
                        gesture_name = "pointing"
                        confidence = 0.75
                    elif finger_count == 2:
                        gesture_name = "peace"
                        confidence = 0.80
                    else:
                        gesture_name = "hand_present"
                        confidence = 0.70

                    gestures.append({
                        "gesture": gesture_name,
                        "confidence": confidence,
                        "finger_count": finger_count,
                        "location": {"x": int(x), "y": int(y), "width": int(bw), "height": int(bh)},
                        "landmarks": []
                    })
                except Exception:
                    pass

        return gestures
