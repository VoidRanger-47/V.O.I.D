"""
vision/camera/frame_processor.py
Frame preprocessing, aspect ratio adjustment, adaptive illumination (CLAHE),
temporal bounding box smoothing, and futuristic HUD annotation.
"""

import cv2
import numpy as np
import base64
import time
from typing import Tuple, List, Dict, Any, Optional


class BoundingBoxSmoother:
    """
    Temporal bounding box smoothing and tracking filter.
    Eliminates detection flicker and box jittering across webcam frames using Exponential Moving Average (EMA).
    """

    def __init__(self, alpha: float = 0.65, max_missed: int = 4, iou_thresh: float = 0.3):
        self.alpha = alpha
        self.max_missed = max_missed
        self.iou_thresh = iou_thresh
        self.tracks: List[Dict[str, Any]] = []
        self._next_id = 1

    @staticmethod
    def _box_iou(b1: List[float], b2: List[float]) -> float:
        x1, y1, w1, h1 = b1
        x2, y2, w2, h2 = b2
        xi1 = max(x1, x2)
        yi1 = max(y1, y2)
        xi2 = min(x1 + w1, x2 + w2)
        yi2 = min(y1 + h1, y2 + h2)
        inter = max(0, xi2 - xi1) * max(0, yi2 - yi1)
        union = (w1 * h1) + (w2 * h2) - inter
        return inter / union if union > 0 else 0.0

    def smooth(self, raw_detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Match incoming raw detections to active tracks and smooth bounding box coordinates.
        Returns stabilized detection list.
        """
        if not raw_detections and not self.tracks:
            return []

        matched_tracks = set()
        smoothed_results = []

        for d in raw_detections:
            loc = d.get("location", {})
            cur_box = [float(loc.get("x", 0)), float(loc.get("y", 0)), float(loc.get("width", 0)), float(loc.get("height", 0))]
            label = d.get("label") or d.get("name") or "object"

            best_iou = 0.0
            best_t_idx = -1
            for idx, track in enumerate(self.tracks):
                if idx in matched_tracks:
                    continue
                # Prefer same category / label
                track_label = track.get("label")
                if track_label and track_label != label:
                    continue
                iou = self._box_iou(cur_box, track["box"])
                if iou > best_iou:
                    best_iou = iou
                    best_t_idx = idx

            if best_iou >= self.iou_thresh and best_t_idx >= 0:
                # Update existing track with EMA
                track = self.tracks[best_t_idx]
                matched_tracks.add(best_t_idx)
                old_box = track["box"]
                new_box = [
                    self.alpha * cur_box[0] + (1 - self.alpha) * old_box[0],
                    self.alpha * cur_box[1] + (1 - self.alpha) * old_box[1],
                    self.alpha * cur_box[2] + (1 - self.alpha) * old_box[2],
                    self.alpha * cur_box[3] + (1 - self.alpha) * old_box[3],
                ]
                track["box"] = new_box
                track["missed"] = 0
                track["hits"] += 1
                track["confidence"] = self.alpha * float(d.get("confidence", 0.5)) + (1 - self.alpha) * track.get("confidence", 0.5)
                track["raw_data"] = d

                det_copy = dict(d)
                det_copy["location"] = {
                    "x": int(round(new_box[0])),
                    "y": int(round(new_box[1])),
                    "width": int(round(new_box[2])),
                    "height": int(round(new_box[3]))
                }
                smoothed_results.append(det_copy)
            else:
                # New track
                self.tracks.append({
                    "id": self._next_id,
                    "box": cur_box,
                    "label": label,
                    "missed": 0,
                    "hits": 1,
                    "confidence": float(d.get("confidence", 0.5)),
                    "raw_data": d
                })
                self._next_id += 1
                det_copy = dict(d)
                smoothed_results.append(det_copy)

        # Age unmatched tracks
        surviving_tracks = []
        for idx, track in enumerate(self.tracks):
            if idx not in matched_tracks:
                track["missed"] += 1
            if track["missed"] <= self.max_missed:
                surviving_tracks.append(track)
        self.tracks = surviving_tracks

        return smoothed_results


class FrameProcessor:
    """
    High-performance image and video frame processor for V.O.I.D. Vision.
    Features adaptive illumination (CLAHE), gamma compensation, and cyber-HUD rendering.
    """
    _box_smoother: Optional[BoundingBoxSmoother] = None

    @classmethod
    def get_smoother(cls) -> BoundingBoxSmoother:
        if cls._box_smoother is None:
            cls._box_smoother = BoundingBoxSmoother()
        return cls._box_smoother

    @staticmethod
    def resize_with_aspect(frame: np.ndarray, target_width: int = 640, target_height: int = 480) -> np.ndarray:
        """Resize frame while preserving aspect ratio with clean letterboxing if needed."""
        h, w = frame.shape[:2]
        scale = min(target_width / w, target_height / h)
        nw, nh = int(w * scale), int(h * scale)
        resized = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
        
        # If perfect match
        if nw == target_width and nh == target_height:
            return resized
        
        # Pad with black border
        canvas = np.zeros((target_height, target_width, 3), dtype=np.uint8)
        top = (target_height - nh) // 2
        left = (target_width - nw) // 2
        canvas[top:top+nh, left:left+nw] = resized
        return canvas

    @staticmethod
    def calculate_brightness(frame: np.ndarray) -> float:
        """Calculate average perceived luminance of frame (0.0 to 1.0)."""
        if frame is None or frame.size == 0:
            return 0.0
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray) / 255.0)

    @staticmethod
    def apply_clahe_enhancement(frame: np.ndarray, clip_limit: float = 2.0, tile_grid_size: Tuple[int, int] = (8, 8)) -> np.ndarray:
        """
        Apply Contrast Limited Adaptive Histogram Equalization (CLAHE) on the L channel of LAB color space.
        Dramatically improves visibility in back-lit, shadowy, or low-light webcam frames.
        """
        if frame is None or frame.size == 0:
            return frame
        try:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
            l_eq = clahe.apply(l)
            enhanced_lab = cv2.merge((l_eq, a, b))
            return cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
        except Exception:
            return frame

    @staticmethod
    def auto_gamma_correction(frame: np.ndarray, target_brightness: float = 0.48) -> np.ndarray:
        """
        Automatically correct gamma curve based on perceived frame luminance.
        Brightens underexposed shadows without blowing out already well-lit regions.
        """
        if frame is None or frame.size == 0:
            return frame
        current_b = FrameProcessor.calculate_brightness(frame)
        if current_b < 0.02 or current_b > 0.95:
            return frame

        # Calculate exponent such that (current_b ** exp) ≈ target_brightness
        exp = np.log(target_brightness) / np.log(max(1e-4, current_b))
        exp = float(np.clip(exp, 0.35, 2.5))
        
        # Build LUT directly with exp
        table = np.array([((i / 255.0) ** exp) * 255 for i in range(256)]).astype("uint8")
        return cv2.LUT(frame, table)


    @staticmethod
    def compute_motion(prev_gray: Optional[np.ndarray], current_gray: np.ndarray, threshold: int = 25) -> Tuple[float, np.ndarray]:
        """Compute pixel motion delta between two consecutive grayscale frames."""
        if prev_gray is None or prev_gray.shape != current_gray.shape:
            return 0.0, current_gray
        
        diff = cv2.absdiff(prev_gray, current_gray)
        _, thresh = cv2.threshold(diff, threshold, 255, cv2.THRESH_BINARY)
        motion_score = float(np.sum(thresh > 0) / thresh.size)
        return motion_score, current_gray

    @classmethod
    def smooth_bounding_boxes(cls, detections: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convenience method to smooth detection bounding boxes temporally."""
        smoother = cls.get_smoother()
        return smoother.smooth(detections)

    @staticmethod
    def draw_hud_overlay(
        frame: np.ndarray,
        objects: List[Dict[str, Any]] = None,
        faces: List[Dict[str, Any]] = None,
        scene_info: Dict[str, Any] = None,
        fps: float = 0.0,
        mode: str = "BALANCED",
        hardware_info: Dict[str, Any] = None,
        gestures: List[Dict[str, Any]] = None,
        detection_fps: float = 0.0
    ) -> np.ndarray:
        """
        Draw a futuristic cyber-HUD on the camera frame (bounding boxes, target markers, telemetry).
        """
        if frame is None:
            return frame
        
        annotated = frame.copy()
        h, w = annotated.shape[:2]
        objects = objects or []
        faces = faces or []
        gestures = gestures or []
        scene_info = scene_info or {}
        hardware_info = hardware_info or {}

        # Colors (BGR)
        CYAN = (245, 206, 0)       # V.O.I.D. Primary Neon Cyan
        GREEN = (74, 222, 128)     # Recognized Owner Green
        MAGENTA = (235, 77, 75)    # Danger / Unknown Red/Magenta
        AMBER = (0, 180, 255)      # Warning / Generic Box Amber
        PURPLE = (220, 100, 240)   # Hand gesture tracking
        TEXT_BG = (20, 20, 25)

        # 1. Top-Left Telemetry Header
        if detection_fps > 0:
            header_text = f"V.O.I.D. // {mode.upper()} // {fps:.0f} FPS (DET: {detection_fps:.0f})"
            box_width = 330
        else:
            header_text = f"V.O.I.D. VISION // {mode.upper()} // {fps:.1f} FPS"
            box_width = 320
        cv2.rectangle(annotated, (10, 10), (box_width, 36), (15, 15, 20), -1)
        cv2.rectangle(annotated, (10, 10), (box_width, 36), CYAN, 1)
        cv2.putText(annotated, header_text, (20, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.45, CYAN, 1, cv2.LINE_AA)

        # 2. Draw Corner Target Reticles on the frame perimeter
        corner_len = 20
        # Top-Left
        cv2.line(annotated, (5, 5), (5 + corner_len, 5), CYAN, 2)
        cv2.line(annotated, (5, 5), (5, 5 + corner_len), CYAN, 2)
        # Top-Right
        cv2.line(annotated, (w - 5, 5), (w - 5 - corner_len, 5), CYAN, 2)
        cv2.line(annotated, (w - 5, 5), (w - 5, 5 + corner_len), CYAN, 2)
        # Bottom-Left
        cv2.line(annotated, (5, h - 5), (5 + corner_len, h - 5), CYAN, 2)
        cv2.line(annotated, (5, h - 5), (5, h - 5 - corner_len), CYAN, 2)
        # Bottom-Right
        cv2.line(annotated, (w - 5, h - 5), (w - 5 - corner_len, h - 5), CYAN, 2)
        cv2.line(annotated, (w - 5, h - 5), (w - 5, h - 5 - corner_len), CYAN, 2)

        # 3. Draw Detected Objects with MOT Tracks, Trajectory Tails, and Interaction Links
        face_centers = []
        face_positions = []
        for f in faces:
            floc = f.get("location", {})
            fx, fy, fw, fh = floc.get("x", 0), floc.get("y", 0), floc.get("width", 0), floc.get("height", 0)
            if fw > 0 and fh > 0:
                fcx, fcy = fx + fw // 2, fy + fh // 2
                face_centers.append((fcx, fcy))
                face_positions.append({"center": (fcx, fcy), "name": f.get("name", "Subject")})

        for obj in objects:
            loc = obj.get("location", {})
            x = int(loc.get("x", 0))
            y = int(loc.get("y", 0))
            bw = int(loc.get("width", 0))
            bh = int(loc.get("height", 0))
            label = obj.get("label", "object").upper()
            conf = obj.get("confidence", 0.0)
            track_id = obj.get("track_id", "")
            interaction = obj.get("interaction")
            trajectory = obj.get("trajectory", [])

            # Suppress redundant generic person box when face identity reticle is active
            if label in ["PERSON", "HUMAN"] and len(face_centers) > 0:
                is_face_inside = any(x - 20 <= fcx <= x + bw + 20 and y - 20 <= fcy <= y + bh + 20 for fcx, fcy in face_centers)
                if is_face_inside:
                    continue

            if bw > 0 and bh > 0:
                # Color code: Cyan for held/interactive, Amber for normal
                color = (0, 220, 255) if interaction else AMBER
                c_len = min(15, max(4, bw // 3), max(4, bh // 3))
                cv2.rectangle(annotated, (x, y), (x + bw, y + bh), color, 1)
                
                # Corner accents
                cv2.line(annotated, (x, y), (x + c_len, y), color, 2)
                cv2.line(annotated, (x, y), (x, y + c_len), color, 2)
                cv2.line(annotated, (x + bw, y), (x + bw - c_len, y), color, 2)
                cv2.line(annotated, (x + bw, y), (x + bw, y + c_len), color, 2)
                cv2.line(annotated, (x, y + bh), (x + c_len, y + bh), color, 2)
                cv2.line(annotated, (x, y + bh), (x, y + bh - c_len), color, 2)
                cv2.line(annotated, (x + bw, y + bh), (x + bw - c_len, y + bh), color, 2)
                cv2.line(annotated, (x + bw, y + bh), (x + bw, y + bh - c_len), color, 2)

                # Draw trajectory trail
                if len(trajectory) >= 2:
                    for i in range(1, len(trajectory)):
                        p1 = (trajectory[i - 1]["x"], trajectory[i - 1]["y"])
                        p2 = (trajectory[i]["x"], trajectory[i]["y"])
                        alpha_line = int(100 + (i / len(trajectory)) * 155)
                        cv2.line(annotated, p1, p2, (0, min(255, alpha_line), 255), 1, cv2.LINE_AA)

                # Draw Interaction line to subject if held
                if interaction:
                    subj_name = interaction.get("subject_name", "")
                    target_fc = next((fp["center"] for fp in face_positions if fp["name"] == subj_name), face_centers[0] if face_centers else None)
                    if target_fc:
                        ocx, ocy = x + bw // 2, y + bh // 2
                        cv2.line(annotated, (ocx, ocy), target_fc, (0, 220, 255), 1, cv2.LINE_AA)
                        mid_x = (ocx + target_fc[0]) // 2
                        mid_y = (ocy + target_fc[1]) // 2
                        cv2.putText(annotated, interaction.get("action", "HELD"), (mid_x - 30, mid_y), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 240, 255), 1, cv2.LINE_AA)

                # Label tag with persistent Track ID
                tid_str = f"#{track_id.replace('obj_#', '')} " if track_id else ""
                tag = f"[{tid_str}{label}] {int(conf * 100)}%"
                (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
                cv2.rectangle(annotated, (x, max(0, y - 18)), (x + tw + 8, y), color, -1)
                cv2.putText(annotated, tag, (x + 4, max(12, y - 5)), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (10, 10, 15), 1, cv2.LINE_AA)

        # 4. Draw Detected Faces, 3D Mesh, Liveness Shield, & Identity
        for face in faces:
            loc = face.get("location", {})
            x = int(loc.get("x", 0))
            y = int(loc.get("y", 0))
            bw = int(loc.get("width", 0))
            bh = int(loc.get("height", 0))
            identity = face.get("identity", "unknown")
            name = face.get("name", "Unknown Person")
            conf = face.get("confidence", 0.0)
            liveness = face.get("liveness", {})
            mesh_3d = face.get("mesh_3d")
            gaze = face.get("gaze", {})
            track_id = face.get("track_id", "")

            if bw > 0 and bh > 0:
                is_owner = identity == "owner"
                is_enrolled = identity == "enrolled"

                if is_owner:
                    box_color = (74, 222, 128)   # Golden Emerald Green for Owner
                    badge_prefix = "[OWNER]"
                    bg_color = (10, 30, 15)
                elif is_enrolled:
                    box_color = (245, 206, 0)    # Neon Cyan for Enrolled
                    badge_prefix = "[KNOWN]"
                    bg_color = (25, 25, 10)
                else:
                    box_color = (80, 140, 255)   # Amber Coral for Guest
                    badge_prefix = "[GUEST]"
                    bg_color = (15, 15, 25)
                
                # Draw circular target reticle
                cx, cy = x + bw // 2, y + bh // 2
                radius = int(max(bw, bh) * 0.58)
                cv2.circle(annotated, (cx, cy), radius, box_color, 1, cv2.LINE_AA)
                cv2.circle(annotated, (cx, cy), 3, box_color, -1)

                # Crosshairs
                cv2.line(annotated, (cx - radius - 6, cy), (cx - radius + 4, cy), box_color, 1)
                cv2.line(annotated, (cx + radius - 4, cy), (cx + radius + 6, cy), box_color, 1)
                cv2.line(annotated, (cx, cy - radius - 6), (cx, cy - radius + 4), box_color, 1)
                cv2.line(annotated, (cx, cy + radius - 4), (cx, cy + radius + 6), box_color, 1)

                # Render 3D Dense Facial Mesh points
                if mesh_3d and isinstance(mesh_3d, list):
                    for pt in mesh_3d:
                        if isinstance(pt, dict):
                            px, py = int(pt.get("x", 0)), int(pt.get("y", 0))
                        elif isinstance(pt, (list, tuple)) and len(pt) >= 2:
                            px, py = int(pt[0]), int(pt[1])
                        else:
                            continue
                        if 0 <= px < w and 0 <= py < h:
                            cv2.circle(annotated, (px, py), 1, box_color, -1)

                # Liveness badge
                live_status = liveness.get("status", "REAL") if liveness else "REAL"
                if live_status == "REAL":
                    live_tag = "[REAL]"
                    live_color = (74, 222, 128)
                elif live_status == "SPOOF_SUSPECTED":
                    live_tag = "[SPOOF RISK]"
                    live_color = (235, 77, 75)
                else:
                    live_tag = "[VERIFY]"
                    live_color = AMBER

                # Face tag with persistent Track ID & Liveness
                conf_str = f" {int(conf * 100)}%" if conf else ""
                tid_prefix = f"#{track_id.replace('face_#', '')} " if track_id else ""
                face_tag = f"{badge_prefix} {tid_prefix}{name.upper()}{conf_str} {live_tag}"
                (tw, th), _ = cv2.getTextSize(face_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.40, 1)
                tag_y = max(20, y - 10)
                cv2.rectangle(annotated, (x, tag_y - 18), (x + tw + 10, tag_y + 2), bg_color, -1)
                cv2.rectangle(annotated, (x, tag_y - 18), (x + tw + 10, tag_y + 2), box_color, 1)
                cv2.putText(annotated, face_tag, (x + 5, tag_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.38, box_color, 1, cv2.LINE_AA)

                # Gaze direction pill beneath face
                gaze_dir = gaze.get("direction", "CENTER") if gaze else "CENTER"
                if gaze_dir != "CENTER":
                    gaze_tag = f"GAZE: {gaze_dir}"
                    (gw, gh), _ = cv2.getTextSize(gaze_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.32, 1)
                    cv2.rectangle(annotated, (x, y + bh + 4), (x + gw + 8, y + bh + 20), (20, 20, 30), -1)
                    cv2.putText(annotated, gaze_tag, (x + 4, y + bh + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.32, CYAN, 1, cv2.LINE_AA)

        # 5. Draw Hand Gestures & 21-Joint Skeletal Wireframe
        for g in gestures:
            g_loc = g.get("location", {})
            gx = int(g_loc.get("x", 0))
            gy = int(g_loc.get("y", 0))
            gw = int(g_loc.get("width", 0))
            gh = int(g_loc.get("height", 0))
            gesture_name = g.get("gesture", "hand").upper()
            g_conf = g.get("confidence", 0.0)
            handedness = g.get("handedness", "")

            # 5a. Draw 21-point skeletal wireframe if available
            landmarks = g.get("landmarks", [])
            if landmarks and len(landmarks) == 21:
                HAND_CONNECTIONS = [
                    (0, 1), (1, 2), (2, 3), (3, 4),        # Thumb
                    (0, 5), (5, 6), (6, 7), (7, 8),        # Index
                    (5, 9), (9, 10), (10, 11), (11, 12),   # Middle
                    (9, 13), (13, 14), (14, 15), (15, 16), # Ring
                    (13, 17), (17, 18), (18, 19), (19, 20),# Pinky
                    (0, 17)                                 # Palm base
                ]
                for p1_idx, p2_idx in HAND_CONNECTIONS:
                    pt1 = landmarks[p1_idx]
                    pt2 = landmarks[p2_idx]
                    p1 = (int(pt1["x"]), int(pt1["y"]))
                    p2 = (int(pt2["x"]), int(pt2["y"]))
                    if 0 <= p1[0] < w and 0 <= p1[1] < h and 0 <= p2[0] < w and 0 <= p2[1] < h:
                        cv2.line(annotated, p1, p2, (230, 120, 255), 1, cv2.LINE_AA)
                for pt in landmarks:
                    px, py = int(pt["x"]), int(pt["y"])
                    if 0 <= px < w and 0 <= py < h:
                        cv2.circle(annotated, (px, py), 2, (255, 200, 255), -1)

            # 5b. Draw Corner Bracket Reticle around hand
            if gw > 0 and gh > 0:
                c_len = min(15, max(4, gw // 4), max(4, gh // 4))
                # Top-left
                cv2.line(annotated, (gx, gy), (gx + c_len, gy), PURPLE, 2)
                cv2.line(annotated, (gx, gy), (gx, gy + c_len), PURPLE, 2)
                # Top-right
                cv2.line(annotated, (gx + gw, gy), (gx + gw - c_len, gy), PURPLE, 2)
                cv2.line(annotated, (gx + gw, gy), (gx + gw, gy + c_len), PURPLE, 2)
                # Bottom-left
                cv2.line(annotated, (gx, gy + gh), (gx + c_len, gy + gh), PURPLE, 2)
                cv2.line(annotated, (gx, gy + gh), (gx, gy + gh - c_len), PURPLE, 2)
                # Bottom-right
                cv2.line(annotated, (gx + gw, gy + gh), (gx + gw - c_len, gy + gh), PURPLE, 2)
                cv2.line(annotated, (gx + gw, gy + gh), (gx + gw, gy + gh - c_len), PURPLE, 2)

                hand_title = f"{handedness.upper()} " if handedness and handedness != "Hand" else ""
                g_tag = f"[{hand_title}{gesture_name}] {int(g_conf * 100)}%"
                (tw, th), _ = cv2.getTextSize(g_tag, cv2.FONT_HERSHEY_SIMPLEX, 0.36, 1)
                tag_y = max(18, gy - 6)
                cv2.rectangle(annotated, (gx, tag_y - 14), (gx + tw + 6, tag_y + 2), (35, 10, 40), -1)
                cv2.rectangle(annotated, (gx, tag_y - 14), (gx + tw + 6, tag_y + 2), PURPLE, 1)
                cv2.putText(annotated, g_tag, (gx + 3, tag_y - 3), cv2.FONT_HERSHEY_SIMPLEX, 0.33, PURPLE, 1, cv2.LINE_AA)

        # 6. Bottom Status Bar (Scene / Hardware telemetry)
        light = scene_info.get("lighting", "normal").upper()
        env = scene_info.get("environment", "indoor").upper()
        cpu = hardware_info.get("cpu_percent", 0.0)
        gpu_str = hardware_info.get("gpu_name", "CPU Mode")
        
        status_bar = f"SCENE: {env} // LIGHT: {light} // CPU: {cpu:.0f}% // {gpu_str}"
        cv2.rectangle(annotated, (10, h - 30), (w - 10, h - 8), (15, 15, 20), -1)
        cv2.rectangle(annotated, (10, h - 30), (w - 10, h - 8), (60, 60, 70), 1)
        cv2.putText(annotated, status_bar, (20, h - 16), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 200, 210), 1, cv2.LINE_AA)

        return annotated

    @staticmethod
    def to_jpeg_bytes(frame: np.ndarray, quality: int = 72) -> bytes:
        """Encode an OpenCV frame into JPEG bytes with optimized compression speed."""
        if frame is None:
            return b""
        ret, buf = cv2.imencode(".jpg", frame, [
            int(cv2.IMWRITE_JPEG_QUALITY), quality,
            int(cv2.IMWRITE_JPEG_OPTIMIZE), 0
        ])
        return buf.tobytes() if ret else b""

    @staticmethod
    def to_base64(frame: np.ndarray, quality: int = 80) -> str:
        """Encode frame into base64 data URI string."""
        jpeg_bytes = FrameProcessor.to_jpeg_bytes(frame, quality)
        if not jpeg_bytes:
            return ""
        return "data:image/jpeg;base64," + base64.b64encode(jpeg_bytes).decode("utf-8")
