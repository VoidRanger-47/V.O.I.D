"""
vision/recognition/subject_analyzer.py
Comprehensive real-time subject telemetry and perception engine for V.O.I.D.
Analyzes identity, physical proximity, head pose, cognitive expression/mood,
gaze status, dominant clothing color & hex swatch, hand gestures, and held objects.
"""

import cv2
import time
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("void.vision.subject_analyzer")


class SubjectAnalyzer:
    """
    Real-time analyzer extracting comprehensive metadata about the primary subject in frame.
    Strictly local, offline, and optimized for low-latency streaming.
    """

    COLOR_PALETTE = [
        ("Black", (20, 20, 25)),
        ("Charcoal", (45, 52, 60)),
        ("Slate Gray", (90, 100, 115)),
        ("Light Gray", (180, 185, 195)),
        ("White", (240, 242, 245)),
        ("Navy Blue", (25, 45, 90)),
        ("Cobalt Blue", (30, 95, 200)),
        ("Sky Blue", (100, 180, 240)),
        ("Deep Teal", (20, 100, 110)),
        ("Forest Green", (35, 90, 50)),
        ("Olive Green", (85, 100, 45)),
        ("Emerald", (40, 160, 90)),
        ("Burgundy", (100, 25, 40)),
        ("Crimson Red", (190, 35, 45)),
        ("Coral / Peach", (230, 110, 90)),
        ("Amber / Orange", (220, 120, 30)),
        ("Golden Yellow", (220, 180, 40)),
        ("Deep Purple", (75, 30, 95)),
        ("Violet", (130, 60, 180)),
        ("Warm Brown", (110, 65, 35)),
        ("Beige / Tan", (195, 175, 140)),
    ]

    def __init__(self):
        self._eye_cascade: Optional[cv2.CascadeClassifier] = None
        self._smile_cascade: Optional[cv2.CascadeClassifier] = None
        self._load_aux_cascades()

        # Dwell time tracking
        self._last_seen_time = 0.0
        self._dwell_start_time = 0.0
        self._primary_subject_name = ""

    def _load_aux_cascades(self):
        """Lazily load eye and smile cascades for subtle facial state classification."""
        try:
            eye_path = cv2.data.haarcascades + "haarcascade_eye.xml"
            smile_path = cv2.data.haarcascades + "haarcascade_smile.xml"
            self._eye_cascade = cv2.CascadeClassifier(eye_path)
            self._smile_cascade = cv2.CascadeClassifier(smile_path)
        except Exception as e:
            logger.warning(f"Could not initialize eye/smile cascades: {e}")

    def _estimate_distance(self, face_width_px: int, frame_width: int) -> Tuple[float, str]:
        """
        Estimate distance to subject in meters using pinhole camera geometry.
        Assumes average adult face breadth ~ 14 cm and typical 60 deg webcam FOV (focal length ~ 550px).
        """
        if face_width_px <= 0:
            return 0.0, "Unknown"

        focal_length = frame_width * 0.86  # approximate focal length in pixels
        face_real_width_m = 0.14
        dist_m = (face_real_width_m * focal_length) / max(face_width_px, 1)
        dist_m = round(max(0.2, min(dist_m, 4.0)), 2)

        if dist_m < 0.40:
            label = f"{dist_m}m (Close-Up / Intimate)"
        elif dist_m <= 0.85:
            label = f"{dist_m}m (Optimal Desk Range)"
        elif dist_m <= 1.60:
            label = f"{dist_m}m (Medium Distance)"
        else:
            label = f"{dist_m}m (Distant / Ambient)"

        return dist_m, label

    def _extract_clothing_color(self, frame: np.ndarray, face_loc: Dict[str, int]) -> Dict[str, Any]:
        """
        Sample the subject's upper chest / torso area beneath the face
        to extract dominant clothing color, hex code, and human-readable label.
        """
        h, w = frame.shape[:2]
        fx = face_loc.get("x", 0)
        fy = face_loc.get("y", 0)
        fw = face_loc.get("width", 0)
        fh = face_loc.get("height", 0)

        # Region of interest: directly under face, slightly broader than face width
        torso_y1 = min(h - 1, fy + fh)
        torso_y2 = min(h, fy + int(fh * 2.0))
        torso_x1 = max(0, fx - int(fw * 0.25))
        torso_x2 = min(w, fx + int(fw * 1.25))

        if torso_y2 - torso_y1 < 10 or torso_x2 - torso_x1 < 10:
            return {"name": "Unknown", "hex": "#334155", "rgb": [51, 65, 85]}

        torso_crop = frame[torso_y1:torso_y2, torso_x1:torso_x2]
        if torso_crop.size == 0:
            return {"name": "Unknown", "hex": "#334155", "rgb": [51, 65, 85]}

        # Downsample for noise reduction and speed
        small = cv2.resize(torso_crop, (24, 24), interpolation=cv2.INTER_AREA)
        # Median color across patch in BGR
        median_bgr = np.median(small.reshape(-1, 3), axis=0).astype(int)
        b, g, r = int(median_bgr[0]), int(median_bgr[1]), int(median_bgr[2])

        hex_code = f"#{r:02x}{g:02x}{b:02x}"
        curr_rgb = (r, g, b)

        # Find closest match in palette using Euclidean distance in RGB
        best_name = "Slate"
        min_dist = float("inf")
        for name, pal_rgb in self.COLOR_PALETTE:
            dist = (r - pal_rgb[0]) ** 2 + (g - pal_rgb[1]) ** 2 + (b - pal_rgb[2]) ** 2
            if dist < min_dist:
                min_dist = dist
                best_name = name

        return {
            "name": best_name,
            "hex": hex_code,
            "rgb": [r, g, b]
        }

    def _analyze_face_expression_and_gaze(
        self,
        frame: np.ndarray,
        face_loc: Dict[str, int],
        primary_face: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Estimate head pose, mood/expression, and gaze directness from face crop.
        """
        h, w = frame.shape[:2]
        fx, fy = face_loc.get("x", 0), face_loc.get("y", 0)
        fw, fh = face_loc.get("width", 0), face_loc.get("height", 0)

        face_crop = frame[fy:fy+fh, fx:fx+fw]
        if face_crop.size == 0:
            return {
                "head_pose": "Frontal (Facing Camera)",
                "mood": "Neutral",
                "gaze": "Attentive",
                "eyes_open": True,
                "exposure": "Optimal"
            }

        # Fast neural path: Bypass Haar cascades if 3D neural telemetry is already available (<0.02ms)
        if primary_face and (primary_face.get("blendshapes") or primary_face.get("head_pose") or primary_face.get("gaze")):
            bs = primary_face.get("blendshapes", {})
            hp = primary_face.get("head_pose", {})
            gz = primary_face.get("gaze", {})
            bio = primary_face.get("biometrics", {})

            small_crop = face_crop[::4, ::4]
            lum = float(np.mean(small_crop) / 255.0) if small_crop.size > 0 else 0.5
            exposure_label = f"Low Light ({int(lum*100)}%)" if lum < 0.25 else f"Bright / Glare ({int(lum*100)}%)" if lum > 0.78 else f"Optimal ({int(lum*100)}%)"

            smile_score = (bs.get("mouthSmileLeft", 0.0) + bs.get("mouthSmileRight", 0.0)) / 2.0
            brow_up = (bs.get("browInnerUp", 0.0) + bs.get("browOuterUpLeft", 0.0)) / 2.0
            brow_down = (bs.get("browDownLeft", 0.0) + bs.get("browDownRight", 0.0)) / 2.0
            jaw_open = bs.get("jawOpen", 0.0)
            if smile_score > 0.40:
                mood_state = "Smiling / Pleased"
            elif brow_up > 0.45:
                mood_state = "Inquiring / Curious"
            elif brow_down > 0.45:
                mood_state = "Deeply Focused / Concentrated"
            elif jaw_open > 0.35:
                mood_state = "Speaking / Articulating"
            else:
                mood_state = "Neutral / Focused"

            pitch = hp.get("pitch", 0.0)
            yaw = hp.get("yaw", 0.0)
            roll = hp.get("roll", 0.0)
            head_pose_str = f"Pitch: {pitch}°, Yaw: {yaw}°, Roll: {roll}°" if (pitch != 0.0 or yaw != 0.0 or roll != 0.0) else "Frontal (Facing Camera direct)"

            gaze_dir = gz.get("direction", "CENTER")
            gaze_str = f"Gaze: {gaze_dir}"
            eyes_open = bio.get("ear", 0.30) >= 0.20

            return {
                "head_pose": head_pose_str,
                "euler_angles": {"pitch": pitch, "yaw": yaw, "roll": roll},
                "mood": mood_state,
                "gaze": gaze_str,
                "eyes_open": eyes_open,
                "exposure": exposure_label,
                "luminance_pct": int(lum * 100)
            }

        gray_face = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
        gray_face = cv2.equalizeHist(gray_face)

        # 1. Luminance & Lighting Quality
        lum = float(np.mean(gray_face) / 255.0)
        if lum < 0.25:
            exposure_label = f"Low Light ({int(lum*100)}%)"
        elif lum > 0.78:
            exposure_label = f"Bright / Glare ({int(lum*100)}%)"
        else:
            exposure_label = f"Optimal ({int(lum*100)}%)"

        # 2. Eye Detection / Gaze Direction
        eyes_count = 0
        gaze_state = "Direct Camera Focus"
        eyes_open = True
        if self._eye_cascade and not self._eye_cascade.empty():
            # Search only upper 60% of face
            upper_face = gray_face[:int(fh * 0.6), :]
            eyes = self._eye_cascade.detectMultiScale(
                upper_face, scaleFactor=1.12, minNeighbors=4, minSize=(15, 15)
            )
            eyes_count = len(eyes)
            if eyes_count >= 2:
                gaze_state = "Direct Camera Focus"
                eyes_open = True
            elif eyes_count == 1:
                gaze_state = "Angled Gaze / Screen View"
                eyes_open = True
            else:
                gaze_state = "Eyes Cast Downward / Blinking"
                eyes_open = False

        # 3. Smile / Mood Detection
        mood_state = "Attentive & Focused"
        if self._smile_cascade and not self._smile_cascade.empty():
            # Search lower 50% of face
            lower_face = gray_face[int(fh * 0.5):, :]
            smiles = self._smile_cascade.detectMultiScale(
                lower_face, scaleFactor=1.25, minNeighbors=8, minSize=(20, 15)
            )
            if len(smiles) > 0:
                mood_state = "Smiling / Expressive"
            else:
                # Check variance for active mouth (talking vs neutral)
                mouth_var = float(np.var(lower_face))
                if mouth_var > 1400:
                    mood_state = "Speaking / Active"
                else:
                    mood_state = "Attentive & Neutral"

        # 4. Head Pose / Orientation
        aspect = float(fw) / max(fh, 1)
        if aspect > 1.15:
            head_pose = "Angled / Lateral Tilt"
        elif aspect < 0.85:
            head_pose = "Vertical / Elongated"
        else:
            head_pose = "Frontal (Facing Camera direct)"

        return {
            "head_pose": head_pose,
            "mood": mood_state,
            "gaze": gaze_state,
            "eyes_open": eyes_open,
            "exposure": exposure_label,
            "luminance_pct": int(lum * 100)
        }

    def analyze_primary_subject(
        self,
        frame: Optional[np.ndarray],
        faces: List[Dict[str, Any]],
        objects: List[Dict[str, Any]],
        gestures: List[Dict[str, Any]],
        motion_score: float = 0.0
    ) -> Dict[str, Any]:
        """
        Construct a full real-time telemetry dossier for the primary subject in view.
        """
        now = time.time()
        if frame is None or frame.size == 0:
            return {
                "detected": False,
                "status": "NO_CAMERA_FRAME",
                "message": "Camera is offline or feed is suspended."
            }

        h, w = frame.shape[:2]

        # 1. Identify Primary Face or Person
        primary_face = None
        if faces:
            # Prioritize recognized owner, then enrolled person, then largest face bounding box
            owners = [f for f in faces if f.get("identity") == "owner"]
            if owners:
                primary_face = owners[0]
            else:
                enrolled = [f for f in faces if f.get("identity") == "enrolled"]
                if enrolled:
                    primary_face = enrolled[0]
                else:
                    # Pick largest face
                    primary_face = max(faces, key=lambda f: f.get("location", {}).get("width", 0) * f.get("location", {}).get("height", 0))

        # If no face is detected, check if a "person" object was detected
        person_obj = None
        if not primary_face:
            person_objs = [o for o in objects if o.get("label") == "person"]
            if person_objs:
                person_obj = max(person_objs, key=lambda o: o.get("location", {}).get("width", 0) * o.get("location", {}).get("height", 0))

        if not primary_face and not person_obj:
            # Reset dwell tracking
            self._dwell_start_time = 0.0
            self._primary_subject_name = ""
            return {
                "detected": False,
                "status": "STANDBY_NO_SUBJECT",
                "message": "No human subject currently detected in camera view.",
                "total_people_in_view": 0,
                "dwell_time_formatted": "00:00",
                "dwell_seconds": 0
            }

        # Subject Bounding Box
        if primary_face:
            loc = primary_face.get("location", {})
            identity = primary_face.get("identity", "unknown")
            name = primary_face.get("name", "Unknown Person")
            conf = primary_face.get("confidence", 0.85)
            is_owner = (identity == "owner")
            is_enrolled = (identity in ["owner", "enrolled"])
            subject_type = "Human Face & Person"
        else:
            loc = person_obj.get("location", {})
            identity = "unidentified_body"
            name = "Subject (Body Detected)"
            conf = person_obj.get("confidence", 0.70)
            is_owner = False
            is_enrolled = False
            subject_type = "Human Silhouette"

        bx, by = loc.get("x", 0), loc.get("y", 0)
        bw, bh = loc.get("width", 0), loc.get("height", 0)

        # 2. Dwell Time Tracking
        if self._dwell_start_time == 0.0 or (now - self._last_seen_time > 4.0):
            self._dwell_start_time = now
            self._primary_subject_name = name
        self._last_seen_time = now
        dwell_seconds = int(now - self._dwell_start_time)
        dwell_min = dwell_seconds // 60
        dwell_sec = dwell_seconds % 60
        dwell_formatted = f"{dwell_min:02d}:{dwell_sec:02d}"

        # 3. Spatial & Proximity Metrics
        dist_m, dist_label = self._estimate_distance(bw if primary_face else bw // 2, w)
        cx, cy = bx + bw // 2, by + bh // 2
        dx_px = cx - (w // 2)
        dy_px = cy - (h // 2)
        dx_pct = round((dx_px / (w // 2)) * 100, 1)

        if abs(dx_pct) < 12:
            alignment = "Centered"
        elif dx_pct > 0:
            alignment = f"Offset Right (+{abs(dx_pct)}%)"
        else:
            alignment = f"Offset Left (-{abs(dx_pct)}%)"

        coverage_pct = round(((bw * bh) / (w * h)) * 100, 1)

        # 4. Facial State / Expression / Pose (Enriched with 3D Mesh & Blendshapes if available)
        face_state = self._analyze_face_expression_and_gaze(frame, loc, primary_face=primary_face)
        
        # Override with 3D neural telemetry if present on primary face
        liveness_info = {"status": "VERIFYING", "score": 0.85, "reason": "Evaluating biological markers"}
        attention_score = 85
        fatigue_status = "ATTENTIVE"
        
        if primary_face:
            # 3D Head Pose
            hp = primary_face.get("head_pose")
            if hp and (hp.get("pitch") != 0.0 or hp.get("yaw") != 0.0 or hp.get("roll") != 0.0):
                pitch = hp.get("pitch", 0.0)
                yaw = hp.get("yaw", 0.0)
                roll = hp.get("roll", 0.0)
                face_state["head_pose"] = f"Pitch: {pitch}°, Yaw: {yaw}°, Roll: {roll}°"
                face_state["euler_angles"] = {"pitch": pitch, "yaw": yaw, "roll": roll}

            # Iris Gaze
            gz = primary_face.get("gaze")
            if gz and gz.get("direction"):
                face_state["gaze"] = f"Gaze: {gz['direction']}"
                gaze_dir = gz["direction"]
            else:
                gaze_dir = "CENTER"

            # 52 Action Unit Blendshapes for nuanced mood
            bs = primary_face.get("blendshapes", {})
            if bs:
                smile_score = (bs.get("mouthSmileLeft", 0.0) + bs.get("mouthSmileRight", 0.0)) / 2.0
                brow_up = (bs.get("browInnerUp", 0.0) + bs.get("browOuterUpLeft", 0.0)) / 2.0
                brow_down = (bs.get("browDownLeft", 0.0) + bs.get("browDownRight", 0.0)) / 2.0
                jaw_open = bs.get("jawOpen", 0.0)
                
                if smile_score > 0.40:
                    face_state["mood"] = "Smiling / Pleased"
                elif brow_up > 0.45:
                    face_state["mood"] = "Inquiring / Curious"
                elif brow_down > 0.45:
                    face_state["mood"] = "Deeply Focused / Concentrated"
                elif jaw_open > 0.35:
                    face_state["mood"] = "Speaking / Articulating"
                else:
                    face_state["mood"] = "Neutral / Focused"

            # Biometrics & Attention
            biometrics = primary_face.get("biometrics", {})
            ear = biometrics.get("ear", 0.30)
            if ear < 0.20:
                fatigue_status = "DROWSY / FATIGUED (Low Eye Aspect Ratio)"
            else:
                fatigue_status = "ALERT / ATTENTIVE"

            # Attention Index (0 - 100%)
            yaw_deg = abs(primary_face.get("head_pose", {}).get("yaw", 0.0))
            pitch_deg = abs(primary_face.get("head_pose", {}).get("pitch", 0.0))
            if gaze_dir == "CENTER" and yaw_deg < 16.0 and pitch_deg < 18.0:
                attention_score = int(min(98, 90 + (16.0 - yaw_deg)))
            elif gaze_dir in ["LOOKING_LEFT", "LOOKING_RIGHT", "LOOKING_DOWN"]:
                attention_score = max(40, int(75 - yaw_deg * 1.2))
            else:
                attention_score = 35

            if primary_face.get("liveness"):
                liveness_info = primary_face["liveness"]

        # 5. Attire & Clothing Color
        attire = self._extract_clothing_color(frame, loc)

        # 6. Motion Activity Level
        if motion_score < 0.012:
            motion_desc = "Stationary / Seated"
        elif motion_score < 0.06:
            motion_desc = "Subtle Micro-Movements"
        elif motion_score < 0.18:
            motion_desc = "Active Motion"
        else:
            motion_desc = "Rapid Motion / Repositioning"

        # 7. Hand Gestures
        subject_gestures = []
        for g in gestures:
            g_name = g.get("gesture", "hand_present") if isinstance(g, dict) else str(g)
            if g_name == "open_palm":
                subject_gestures.append("Open Palm (Greeting)")
            elif g_name == "pointing":
                subject_gestures.append("Pointing Action")
            elif g_name in ["resting", "None (Hands Resting)"]:
                subject_gestures.append("None (Hands Resting)")
            else:
                subject_gestures.append(f"Hand Active ({g_name})")
        if not subject_gestures:
            subject_gestures = ["None (Hands Resting)"]

        # 8. Vicinity & Held Objects (Correlated with active interactions)
        held_objects = []
        for obj in objects:
            olabel = obj.get("label", "")
            if olabel == "person":
                continue
            oloc = obj.get("location", {})
            ox, oy = oloc.get("x", 0), oloc.get("y", 0)
            ow, oh = oloc.get("width", 0), oloc.get("height", 0)
            
            obj_cx, obj_cy = ox + ow // 2, oy + oh // 2
            dist_to_subj = np.sqrt((obj_cx - cx) ** 2 + (obj_cy - cy) ** 2)
            is_held = (obj.get("state") == "HELD") or (dist_to_subj < max(bw, bh) * 1.2)
            
            if dist_to_subj < max(bw, bh) * 2.2 or is_held:
                held_objects.append({
                    "label": olabel.capitalize(),
                    "confidence": round(float(obj.get("confidence", 0.5)) * 100, 0),
                    "track_id": obj.get("track_id", "obj_#"),
                    "is_held": is_held,
                    "action": obj.get("interaction", {}).get("action") if obj.get("interaction") else ("Holding" if is_held else "Nearby on Desk")
                })

        # Role string
        if is_owner:
            role_label = "AUTHORIZED OWNER"
            role_badge = "owner"
        elif is_enrolled:
            role_label = "KNOWN MEMBER"
            role_badge = "enrolled"
        else:
            role_label = "UNREGISTERED SUBJECT"
            role_badge = "guest"

        # Synthesize natural language dossier summary
        owner_part = f"The primary subject is identified as {name} ({role_label})."
        dist_part = f"Positioned at {dist_label}, {alignment}."
        attire_part = f"Attire appears {attire['name']} ({attire['hex']}), with {face_state['exposure']} lighting."
        mood_part = f"Expression is {face_state['mood']} with {face_state['gaze'].lower()}, attention index {attention_score}%."
        held_names = [o["label"] for o in held_objects if o.get("is_held")]
        obj_names = [o["label"] for o in held_objects]
        if held_names:
            obj_part = f" Actively holding: {', '.join(held_names)}."
        elif obj_names:
            obj_part = f" Detected items nearby: {', '.join(obj_names)}."
        else:
            obj_part = " No items detected in close vicinity."

        natural_summary = f"{owner_part} {dist_part} {attire_part} {mood_part}{obj_part} Anti-spoofing verification: {liveness_info.get('status', 'VERIFIED')}."

        return {
            "detected": True,
            "status": "SUBJECT_IN_VIEW",
            "subject_type": subject_type,
            "identity": {
                "name": name,
                "role": role_label,
                "role_badge": role_badge,
                "is_owner": is_owner,
                "is_enrolled": is_enrolled,
                "confidence_pct": int(conf * 100) if conf else 85,
                "liveness": liveness_info,
                "track_id": primary_face.get("track_id") if primary_face else None
            },
            "spatial": {
                "bounding_box": {"x": bx, "y": by, "width": bw, "height": bh},
                "distance_meters": dist_m,
                "distance_label": dist_label,
                "alignment": alignment,
                "coverage_pct": coverage_pct,
                "centroid": {"x": cx, "y": cy}
            },
            "cognitive_and_pose": {
                "head_pose": face_state["head_pose"],
                "euler_angles": face_state.get("euler_angles", {"pitch": 0.0, "yaw": 0.0, "roll": 0.0}),
                "mood": face_state["mood"],
                "gaze": face_state["gaze"],
                "attention_score": attention_score,
                "fatigue_status": fatigue_status,
                "eyes_open": face_state["eyes_open"],
                "exposure": face_state["exposure"],
                "luminance_pct": face_state["luminance_pct"]
            },
            "attire": attire,
            "activity": {
                "motion": motion_desc,
                "motion_score": round(motion_score, 4),
                "gestures": subject_gestures,
                "dwell_seconds": dwell_seconds,
                "dwell_formatted": dwell_formatted
            },
            "vicinity_objects": held_objects,
            "total_subjects_in_view": len(faces) if faces else (1 if person_obj else 0),
            "natural_summary": natural_summary,
            "timestamp": now
        }


subject_analyzer = SubjectAnalyzer()
