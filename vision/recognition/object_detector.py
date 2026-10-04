"""
vision/recognition/object_detector.py
Advanced real-time local object detection and multi-object tracking (MOT).
Powered by Ultralytics YOLO11 and YOLOv8 with CUDA GPU acceleration,
persistent object trajectories, velocity vectors, dwell times, and spatial
person-object interaction reasoning ("holding phone", "drinking from cup").
"""

import time
from collections import deque
import cv2
import torch
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from vision.models.model_manager import model_manager

logger = logging.getLogger("void.vision.object_detector")


class ObjectTrackerState:
    """Maintains kinematics, velocity vectors, and dwell times per tracked object."""
    def __init__(self):
        self._tracks: Dict[str, Dict[str, Any]] = {}
        self._counter = 0

    def update_tracks(self, detections: List[Dict[str, Any]], frame_shape: Tuple[int, int]) -> List[Dict[str, Any]]:
        now = time.time()
        h, w = frame_shape[:2]
        updated = []

        # Cleanup expired tracks (> 2.5s unobserved)
        for tid, tdata in list(self._tracks.items()):
            if now - tdata["last_seen"] > 2.5:
                del self._tracks[tid]

        for det in detections:
            loc = det["location"]
            cx = loc["x"] + loc["width"] // 2
            cy = loc["y"] + loc["height"] // 2
            label = det["label"]
            raw_id = det.get("raw_track_id")

            matched_tid = None

            # 1. Match by model track ID if available
            if raw_id is not None:
                tid_str = f"obj_#{raw_id}"
                if tid_str in self._tracks and self._tracks[tid_str]["label"] == label:
                    matched_tid = tid_str
                elif tid_str not in self._tracks:
                    matched_tid = tid_str

            # 2. Fallback: match by label + spatial distance
            if matched_tid is None:
                best_dist = float("inf")
                for tid, tdata in self._tracks.items():
                    if tdata["label"] == label:
                        dist = np.sqrt((cx - tdata["last_cx"]) ** 2 + (cy - tdata["last_cy"]) ** 2)
                        max_match_dist = max(loc["width"], loc["height"], 60) * 1.2
                        if dist < max_match_dist and dist < best_dist:
                            best_dist = dist
                            matched_tid = tid

            # 3. If new or uninitialized, create track entry
            if matched_tid is None:
                self._counter += 1
                matched_tid = f"obj_#{self._counter}"

            if matched_tid not in self._tracks:
                self._tracks[matched_tid] = {
                    "label": label,
                    "first_seen": now,
                    "last_seen": now,
                    "last_cx": cx,
                    "last_cy": cy,
                    "history": deque(maxlen=24),
                    "velocities": deque(maxlen=10)
                }

            track = self._tracks[matched_tid]
            dt = max(0.01, now - track["last_seen"]) if len(track["history"]) > 0 else 0.05
            dx = cx - track["last_cx"]
            dy = cy - track["last_cy"]
            speed = np.sqrt(dx ** 2 + dy ** 2) / dt  # pixels per second

            track["last_seen"] = now
            track["last_cx"] = cx
            track["last_cy"] = cy
            track["history"].append((cx, cy))
            track["velocities"].append(speed)

            # Determine movement status
            avg_speed = float(np.mean(track["velocities"])) if track["velocities"] else 0.0
            if avg_speed < 25.0:
                movement_status = "STATIONARY"
            elif abs(dx) > abs(dy):
                movement_status = "MOVING_RIGHT" if dx > 0 else "MOVING_LEFT"
            else:
                movement_status = "MOVING_DOWN" if dy > 0 else "MOVING_UP"

            dwell_sec = round(now - track["first_seen"], 1)

            # Trajectory tail formatted for UI HUD
            trajectory = [{"x": p[0], "y": p[1]} for p in list(track["history"])]

            # Area relative to frame (depth estimation)
            box_area = loc["width"] * loc["height"]
            frame_area = max(1, w * h)
            area_ratio = box_area / frame_area
            if area_ratio > 0.18:
                proximity = "CLOSE"
            elif area_ratio > 0.04:
                proximity = "DESK_RANGE"
            else:
                proximity = "DISTANT"

            enriched = dict(det)
            enriched["track_id"] = matched_tid
            enriched["dwell_time_sec"] = dwell_sec
            enriched["movement"] = {
                "status": movement_status,
                "speed_px_s": round(avg_speed, 1),
                "dx": round(dx, 1),
                "dy": round(dy, 1)
            }
            enriched["proximity"] = proximity
            enriched["trajectory"] = trajectory
            enriched["state"] = "ACTIVE"
            enriched["interaction"] = None

            updated.append(enriched)

        return updated


class ObjectDetector:
    """
    Advanced real-time local object detector.
    Detects objects with persistent tracking (MOT), velocities, dwell time,
    and spatial subject interaction reasoning.
    """

    CONFIDENCE_THRESHOLD = 0.35
    IOU_THRESHOLD = 0.45

    CATEGORY_ALIASES = {
        "cell phone": "phone",
        "smartphone": "phone",
        "coffee mug": "mug",
        "water bottle": "bottle",
        "computer mouse": "mouse",
        "dining table": "table",
        "potted plant": "plant",
        "hair drier": "hairdryer",
        "wine glass": "glass",
        "drinking glass": "glass",
        "sports ball": "ball",
        "baseball bat": "bat",
        "tennis racket": "racket",
        "couch": "sofa",
        "tv": "monitor / display",
        "remote": "remote control",
        "wristwatch": "watch"
    }

    # Objects that humans commonly hold or interact with on a desk or in hand
    HOLDABLE_LABELS = {
        "phone", "cell phone", "smartphone", "cup", "mug", "coffee mug", "bottle",
        "water bottle", "book", "notebook", "mouse", "computer mouse", "pen", "pencil",
        "apple", "banana", "sandwich", "fork", "knife", "spoon", "remote control",
        "remote", "toothbrush", "keys", "keychain", "wallet", "smartwatch", "watch",
        "scissors", "screwdriver", "pill bottle", "flashlight", "headphones", "earbuds",
        "credit card", "passport", "glass"
    }

    def __init__(self, confidence_threshold: float = 0.35):
        self.confidence_threshold = confidence_threshold
        self._model_mgr = model_manager
        self._tracker = ObjectTrackerState()
        self._hog = cv2.HOGDescriptor()
        self._hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect_objects(self, frame: np.ndarray, faces: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Detect and track objects in frame with persistent track IDs, kinematics,
        and spatial interaction reasoning.
        """
        if frame is None or frame.size == 0:
            return []

        detector_info = self._model_mgr.load_object_detector()
        dtype = detector_info.get("type")

        if dtype in ("ultralytics_yolo", "ultralytics_yolo_world"):
            raw_results = self._detect_yolo(frame, detector_info)
        elif dtype == "torchvision_ssdlite":
            raw_results = self._detect_torchvision(frame, detector_info)
        else:
            raw_results = self._detect_opencv_fallback(frame)

        # 1. Apply NMS
        nms_results = self._apply_nms(raw_results)

        # 2. Multi-Object Tracking & Kinematics
        tracked = self._tracker.update_tracks(nms_results, frame.shape)

        # 3. Spatial Interaction Reasoner (correlate with faces & person postures)
        if faces is not None:
            tracked = self.correlate_interactions(tracked, faces, frame.shape)

        return tracked

    def _detect_yolo(self, frame: np.ndarray, detector_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run Ultralytics YOLO with tracking enabled."""
        try:
            model = detector_info["model"]
            device = detector_info.get("device", "cpu")
            h, w = frame.shape[:2]

            try:
                # Run YOLO tracking with persistent state at 320px high-speed resolution
                preds = model.track(
                    frame,
                    conf=self.confidence_threshold,
                    iou=self.IOU_THRESHOLD,
                    imgsz=320,
                    persist=True,
                    verbose=False,
                    device=device
                )[0]
            except Exception as track_err:
                logger.debug(f"YOLO track fallback to standard predict: {track_err}")
                preds = model(
                    frame,
                    conf=self.confidence_threshold,
                    iou=self.IOU_THRESHOLD,
                    imgsz=320,
                    verbose=False,
                    device=device
                )[0]

            results = []
            if preds.boxes is not None and len(preds.boxes) > 0:
                boxes = preds.boxes.xyxy.cpu().numpy()
                scores = preds.boxes.conf.cpu().numpy()
                classes = preds.boxes.cls.cpu().numpy().astype(int)
                names = model.names
                track_ids = preds.boxes.id.cpu().numpy().astype(int) if preds.boxes.id is not None else [None] * len(boxes)

                for box, score, cls_id, raw_tid in zip(boxes, scores, classes, track_ids):
                    x1, y1, x2, y2 = box
                    x1, y1 = max(0, int(round(x1))), max(0, int(round(y1)))
                    x2, y2 = min(w, int(round(x2))), min(h, int(round(y2)))
                    bw, bh = max(0, x2 - x1), max(0, y2 - y1)

                    if bw < 12 or bh < 12:
                        continue

                    if isinstance(names, dict):
                        raw_name = names.get(cls_id, "object")
                    elif isinstance(names, list) and cls_id < len(names):
                        raw_name = names[cls_id]
                    else:
                        raw_name = "object"

                    category_name = self.CATEGORY_ALIASES.get(raw_name, raw_name)
                    results.append({
                        "label": category_name,
                        "confidence": round(float(score), 2),
                        "location": {
                            "x": x1,
                            "y": y1,
                            "width": bw,
                            "height": bh
                        },
                        "raw_track_id": int(raw_tid) if raw_tid is not None else None
                    })

            return results
        except Exception as e:
            logger.warning(f"YOLO inference error ({e}), falling back to TorchVision/OpenCV.")
            if "transforms" in detector_info:
                return self._detect_torchvision(frame, detector_info)
            return self._detect_opencv_fallback(frame)

    def _apply_nms(self, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out redundant overlapping bounding boxes for the same label."""
        if not detections or len(detections) <= 1:
            return detections

        boxes = []
        scores = []
        for d in detections:
            loc = d["location"]
            boxes.append([loc["x"], loc["y"], loc["width"], loc["height"]])
            scores.append(float(d.get("confidence", 0.5)))

        indices = cv2.dnn.NMSBoxes(boxes, scores, self.confidence_threshold, self.IOU_THRESHOLD)
        if len(indices) == 0:
            return detections

        indices = [i[0] if isinstance(i, (list, tuple, np.ndarray)) else i for i in indices]
        return [detections[idx] for idx in indices if idx < len(detections)]

    def _detect_torchvision(self, frame: np.ndarray, detector_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Run TorchVision SSDLite neural detector on CUDA / CPU."""
        model = detector_info["model"]
        transforms = detector_info["transforms"]
        categories = detector_info["categories"]
        device = self._model_mgr.device

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        tensor_img = transforms(torch.from_numpy(rgb_frame).permute(2, 0, 1)).to(device)

        with torch.no_grad():
            predictions = model([tensor_img])[0]

        boxes = predictions["boxes"].cpu().numpy()
        scores = predictions["scores"].cpu().numpy()
        labels = predictions["labels"].cpu().numpy()

        results = []
        for box, score, label_id in zip(boxes, scores, labels):
            if score < self.confidence_threshold:
                continue

            x1, y1, x2, y2 = box
            x1 = max(0, int(x1))
            y1 = max(0, int(y1))
            x2 = min(w, int(x2))
            y2 = min(h, int(y2))
            bw = max(0, x2 - x1)
            bh = max(0, y2 - y1)

            if bw < 12 or bh < 12:
                continue

            raw_name = categories[label_id] if label_id < len(categories) else "object"
            category_name = self.CATEGORY_ALIASES.get(raw_name, raw_name)

            results.append({
                "label": category_name,
                "confidence": round(float(score), 2),
                "location": {
                    "x": x1,
                    "y": y1,
                    "width": bw,
                    "height": bh
                },
                "raw_track_id": None
            })

        return results

    def _detect_opencv_fallback(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """Fallback detection using OpenCV HOG detector for people and geometric heuristics."""
        results = []
        h, w = frame.shape[:2]
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        boxes, weights = self._hog.detectMultiScale(gray, winStride=(8, 8), padding=(8, 8), scale=1.05)
        for (x, y, bw, bh), weight in zip(boxes, weights):
            if weight > 0.15:
                results.append({
                    "label": "person",
                    "confidence": round(min(0.5 + float(weight) * 0.3, 0.95), 2),
                    "location": {
                        "x": int(x),
                        "y": int(y),
                        "width": int(bw),
                        "height": int(bh)
                    },
                    "raw_track_id": None
                })

        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blurred, 50, 150)
        contours, _ = cv2.findContours(edged, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for cnt in contours:
            area = cv2.contourArea(cnt)
            if 2500 < area < (h * w * 0.4):
                peri = cv2.arcLength(cnt, True)
                approx = cv2.approxPolyDP(cnt, 0.04 * peri, True)
                x, y, bw, bh = cv2.boundingRect(approx)
                aspect_ratio = float(bw) / float(bh) if bh > 0 else 0

                if len(approx) == 4 and 1.2 <= aspect_ratio <= 2.2:
                    results.append({
                        "label": "screen" if area > 10000 else "book",
                        "confidence": 0.45,
                        "location": {"x": int(x), "y": int(y), "width": int(bw), "height": int(bh)},
                        "raw_track_id": None
                    })
                elif 0.3 <= aspect_ratio <= 0.6 and area < 8000:
                    results.append({
                        "label": "bottle",
                        "confidence": 0.42,
                        "location": {"x": int(x), "y": int(y), "width": int(bw), "height": int(bh)},
                        "raw_track_id": None
                    })

        return results

    def correlate_interactions(
        self,
        objects: List[Dict[str, Any]],
        faces: List[Dict[str, Any]],
        frame_shape: Tuple[int, int]
    ) -> List[Dict[str, Any]]:
        """
        Spatial Subject-Object Interaction Engine:
        Analyzes geometric proximity and overlap between detected objects and subjects.
        Detects when a subject is actively holding, drinking from, or typing on an object.
        """
        if not faces or not objects:
            return objects

        for obj in objects:
            lbl = obj["label"].lower()
            if lbl not in self.HOLDABLE_LABELS and "phone" not in lbl and "cup" not in lbl and "bottle" not in lbl:
                continue

            oloc = obj["location"]
            ox = oloc["x"] + oloc["width"] // 2
            oy = oloc["y"] + oloc["height"] // 2

            for face in faces:
                floc = face["location"]
                fx = floc["x"] + floc["width"] // 2
                fy = floc["y"] + floc["height"] // 2
                fw = floc["width"]
                fh = floc["height"]
                subject_name = face.get("name", "Subject")

                # The torso/hands interaction region is typically within 2.5x face width horizontally
                # and extends 0.5x to 3.5x face height beneath the chin
                dx = abs(ox - fx)
                dy = oy - fy  # positive if object is below face

                if dx < (fw * 2.2) and (fh * 0.4) <= dy <= (fh * 3.8):
                    # Object is within personal hand/holding zone
                    if "phone" in lbl:
                        action = "Holding smartphone"
                    elif "cup" in lbl or "bottle" in lbl or "glass" in lbl:
                        action = "Drinking / holding beverage"
                    elif "book" in lbl:
                        action = "Reading document / book"
                    else:
                        action = f"Holding {obj['label']}"

                    obj["interaction"] = {
                        "subject_name": subject_name,
                        "action": action,
                        "confidence": 0.88,
                        "is_held": True
                    }
                    obj["is_held"] = True
                    obj["state"] = "HELD"
                    break

        return objects
