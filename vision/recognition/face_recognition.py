"""
vision/recognition/face_recognition.py
Opt-in local identity recognition, facial profile management, and anti-spoofing verification.
Powered by ArcFace (512-d) and SFace (128-d) deep neural embeddings with canonical 5-point
similarity alignment, passive 3D liveness detection, multi-sample prototype matching,
and persistent temporal multi-face tracking.
Strictly local, offline, and privacy-first.
"""

import os
import json
import time
from collections import deque
import cv2
import numpy as np
import logging
from typing import List, Dict, Any, Optional, Tuple
from vision.recognition.face_detector import FaceDetector
from vision.models.model_manager import model_manager

logger = logging.getLogger("void.vision.face_recognition")


class LivenessAnalyzer:
    """
    Real-time passive 3D anti-spoofing and liveness engine.
    Analyzes temporal Eye Aspect Ratio (EAR) blink dynamics, 3D head pose micro-sway,
    and frequency-domain texture metrics to detect and reject 2D photos and screen presentation attacks.
    """
    def __init__(self):
        # Tracking history per face: {track_key: {"ear": deque, "pose": deque, "timestamps": deque, "blinks": int}}
        self._tracks: Dict[str, Dict[str, Any]] = {}

    def evaluate_liveness(
        self,
        track_key: str,
        face_crop: np.ndarray,
        biometrics: Dict[str, Any],
        head_pose: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Evaluate liveness for a face observation.
        Returns:
            {
                "score": float (0.0 to 1.0),
                "status": "REAL" | "VERIFYING" | "SPOOF_SUSPECTED",
                "blinks_detected": int,
                "motion_variance": float,
                "texture_score": float,
                "reason": str
            }
        """
        now = time.time()
        ear = float(biometrics.get("ear", 0.30)) if biometrics else 0.30
        pitch = float(head_pose.get("pitch", 0.0)) if head_pose else 0.0
        yaw = float(head_pose.get("yaw", 0.0)) if head_pose else 0.0
        roll = float(head_pose.get("roll", 0.0)) if head_pose else 0.0

        if track_key not in self._tracks or (now - self._tracks[track_key]["last_seen"]) > 3.0:
            self._tracks[track_key] = {
                "ear": deque(maxlen=40),
                "pose": deque(maxlen=40),
                "timestamps": deque(maxlen=40),
                "blinks": 0,
                "in_blink": False,
                "last_seen": now
            }

        track = self._tracks[track_key]
        track["last_seen"] = now
        track["ear"].append(ear)
        track["pose"].append((pitch, yaw, roll))
        track["timestamps"].append(now)

        # 1. Temporal Blink Detection
        # An eye blink is characterized by a quick dip below EAR 0.20 and return to > 0.26 within ~0.3s
        if ear < 0.20 and not track["in_blink"]:
            track["in_blink"] = True
        elif ear > 0.26 and track["in_blink"]:
            track["in_blink"] = False
            track["blinks"] += 1

        # 2. 3D Head Pose Micro-Sway (living humans naturally sway 0.3 - 4.0 degrees)
        motion_var = 0.0
        if len(track["pose"]) >= 8:
            poses = np.array(list(track["pose"]), dtype=np.float32)
            stds = np.std(poses, axis=0)
            motion_var = round(float(np.mean(stds)), 2)

        # 3. Frequency-Domain Texture Sharpness
        texture_score = 100.0
        if face_crop is not None and face_crop.size > 0:
            try:
                gray = cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY)
                texture_score = round(float(cv2.Laplacian(gray, cv2.CV_64F).var()), 1)
            except Exception:
                texture_score = 100.0

        num_frames = len(track["ear"])

        # Decision rules
        if track["blinks"] >= 1 or (motion_var >= 0.30 and 35.0 <= texture_score <= 1600.0 and num_frames >= 10):
            status = "REAL"
            liveness_score = min(0.99, round(0.85 + min(track["blinks"] * 0.05, 0.10) + min(motion_var * 0.02, 0.04), 2))
            reason = "Active biological micro-motion & natural eye blinks verified."
        elif num_frames >= 18 and track["blinks"] == 0 and motion_var < 0.10:
            status = "SPOOF_SUSPECTED"
            liveness_score = round(max(0.12, 0.30 - (motion_var * 0.1)), 2)
            reason = "Static 2D Presentation Attack suspected (No eye blinks or natural 3D head movement)."
        else:
            status = "VERIFYING"
            liveness_score = 0.72
            reason = f"Gathering temporal frames ({num_frames}/18) for liveness confirmation."

        return {
            "score": liveness_score,
            "status": status,
            "blinks_detected": track["blinks"],
            "motion_variance": motion_var,
            "texture_score": texture_score,
            "reason": reason
        }


class FaceRecognizer:
    """
    Opt-in high-accuracy identity recognition system.
    Extracts deep neural feature vectors using ArcFace (512-d) or SFace (128-d)
    with canonical 5-point affine alignment, passive anti-spoofing liveness verification,
    and multi-sample prototype matching.
    Strictly local, offline, and privacy-first.
    """

    # Similarity cutoffs calibrated on L2-normalized cosine distance
    ARCFACE_THRESHOLD = 0.42
    ARCFACE_OWNER_THRESHOLD = 0.38
    SFACE_THRESHOLD = 0.45
    SFACE_OWNER_THRESHOLD = 0.42

    # Embedding vector dimensionalities
    EMBEDDING_DIM = 512
    ARCFACE_DIM = 512
    SFACE_DIM = 128

    def __init__(self, profiles_path: Optional[str] = None):
        self.detector = FaceDetector()
        self._model_mgr = model_manager
        self.liveness_analyzer = LivenessAnalyzer()
        self._recent_tracking: Dict[str, Dict[str, Any]] = {}
        self._track_counter = 0

        if profiles_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.profiles_dir = os.path.join(base_dir, "data")
            os.makedirs(self.profiles_dir, exist_ok=True)
            self.profiles_path = os.path.join(self.profiles_dir, "profiles.json")
        else:
            self.profiles_path = profiles_path
            self.profiles_dir = os.path.dirname(profiles_path)
            os.makedirs(self.profiles_dir, exist_ok=True)

        self._profiles: Dict[str, Dict[str, Any]] = {}
        self._load_profiles()

    def _load_profiles(self):
        """Load enrolled identity profiles from local JSON file."""
        if os.path.exists(self.profiles_path):
            try:
                with open(self.profiles_path, "r", encoding="utf-8") as f:
                    self._profiles = json.load(f)
                logger.info(f"Loaded {len(self._profiles)} enrolled identity profile(s).")
            except Exception as e:
                logger.error(f"Failed to load identity profiles: {e}")
                self._profiles = {}
        else:
            self._profiles = {}

    def _save_profiles(self):
        """Save identity profiles to local storage securely."""
        try:
            with open(self.profiles_path, "w", encoding="utf-8") as f:
                json.dump(self._profiles, f, indent=2)
            logger.info("Enrolled profiles saved successfully.")
        except Exception as e:
            logger.error(f"Failed to save identity profiles: {e}")

    def compute_face_embedding(
        self,
        face_crop: np.ndarray,
        full_frame: Optional[np.ndarray] = None,
        raw_face: Optional[np.ndarray] = None,
        align_matrix: Optional[np.ndarray] = None
    ) -> np.ndarray:
        """
        Extract a normalized deep neural feature vector from a face.
        Priority:
        1. ArcFace 512-dimensional ONNX embeddings (highest accuracy).
        2. OpenCV SFace 128-dimensional deep embeddings.
        3. Gradient/texture descriptor fallback.
        """
        if face_crop is None or face_crop.size == 0:
            return np.zeros(128, dtype=np.float32)

        # 1. Primary: ArcFace 512-dimensional embedding
        arcface_emb = self._compute_arcface_embedding(face_crop, full_frame=full_frame, align_matrix=align_matrix)
        if arcface_emb is not None:
            return arcface_emb

        # 2. Secondary: SFace 128-dimensional embedding
        sface_emb = self._compute_sface_embedding(face_crop, full_frame=full_frame, raw_face=raw_face)
        if sface_emb is not None:
            return sface_emb

        # 3. Tertiary: Illumination-invariant HOG + LBP fallback
        return self._compute_fallback_descriptor(face_crop)

    def _compute_arcface_embedding(
        self,
        face_crop: np.ndarray,
        full_frame: Optional[np.ndarray],
        align_matrix: Optional[np.ndarray]
    ) -> Optional[np.ndarray]:
        """Compute 512-d normalized embedding via ArcFace ONNX Runtime session."""
        arc_data = self._model_mgr.load_arcface_recognizer()
        if arc_data is None:
            return None

        try:
            if full_frame is not None and align_matrix is not None:
                aligned = cv2.warpAffine(full_frame, align_matrix, (112, 112), borderValue=0.0)
            else:
                aligned = cv2.resize(face_crop, (112, 112), interpolation=cv2.INTER_AREA)

            # Preprocessing: BGR -> RGB, normalize to [-1, 1]
            rgb = cv2.cvtColor(aligned, cv2.COLOR_BGR2RGB).astype(np.float32)
            rgb = (rgb - 127.5) / 128.0

            session = arc_data["session"]
            input_meta = session.get_inputs()[0]
            input_name = input_meta.name
            output_name = arc_data["output_name"]

            # Adapt to either NCHW (1, 3, 112, 112) or NHWC (1, 112, 112, 3)
            in_shape = input_meta.shape
            if len(in_shape) == 4 and in_shape[1] == 3:
                blob = np.transpose(rgb, (2, 0, 1))[np.newaxis, :].astype(np.float32)
            else:
                blob = rgb[np.newaxis, :].astype(np.float32)

            raw_feat = session.run([output_name], {input_name: blob})[0].flatten()
            norm = np.linalg.norm(raw_feat)
            if norm > 1e-6:
                raw_feat = raw_feat / norm
            return raw_feat.astype(np.float32)
        except Exception as e:
            logger.warning(f"ArcFace feature extraction exception ({e}), fallback to SFace.")
            return None

    def _compute_sface_embedding(
        self,
        face_crop: np.ndarray,
        full_frame: Optional[np.ndarray],
        raw_face: Optional[np.ndarray]
    ) -> Optional[np.ndarray]:
        """Compute 128-d normalized embedding via OpenCV SFace."""
        sface = self._model_mgr.load_sface_recognizer()
        if sface is None:
            return None

        try:
            if full_frame is not None and raw_face is not None and len(raw_face) >= 15:
                aligned = sface.alignCrop(full_frame, raw_face)
                feat = sface.feature(aligned)[0]
            else:
                resized = cv2.resize(face_crop, (112, 112), interpolation=cv2.INTER_AREA)
                feat = sface.feature(resized)[0]

            norm = np.linalg.norm(feat)
            if norm > 1e-6:
                feat = feat / norm
            return feat.astype(np.float32)
        except Exception as e:
            logger.debug(f"SFace feature extraction exception: {e}")
            return None

    def _compute_fallback_descriptor(self, face_crop: np.ndarray) -> np.ndarray:
        """Lightweight fallback gradient + texture descriptor when ONNX models are unavailable."""
        target_size = (96, 96)
        resized = cv2.resize(face_crop, target_size, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        norm_gray = clahe.apply(gray)

        gx = cv2.Sobel(norm_gray, cv2.CV_32F, 1, 0, ksize=3)
        gy = cv2.Sobel(norm_gray, cv2.CV_32F, 0, 1, ksize=3)
        mag, ang = cv2.cartToPolar(gx, gy, angleInDegrees=True)

        block_size = 24
        grad_feats = []
        for r in range(0, 96, block_size):
            for c in range(0, 96, block_size):
                b_mag = mag[r:r+block_size, c:c+block_size]
                b_ang = ang[r:r+block_size, c:c+block_size]
                hist, _ = np.histogram(b_ang, bins=8, range=(0, 360), weights=b_mag)
                norm = np.linalg.norm(hist) + 1e-6
                grad_feats.extend(hist / norm)

        lbp = np.zeros_like(norm_gray)
        for i in range(1, 95):
            for j in range(1, 95):
                center = norm_gray[i, j]
                code = 0
                code |= (norm_gray[i-1, j-1] >= center) << 7
                code |= (norm_gray[i-1, j] >= center) << 6
                code |= (norm_gray[i-1, j+1] >= center) << 5
                code |= (norm_gray[i, j+1] >= center) << 4
                code |= (norm_gray[i+1, j+1] >= center) << 3
                code |= (norm_gray[i+1, j] >= center) << 2
                code |= (norm_gray[i+1, j-1] >= center) << 1
                code |= (norm_gray[i, j-1] >= center) << 0
                lbp[i, j] = code

        lbp_feats = []
        for r in range(0, 96, block_size):
            for c in range(0, 96, block_size):
                b_lbp = lbp[r:r+block_size, c:c+block_size]
                hist, _ = np.histogram(b_lbp, bins=8, range=(0, 256))
                norm = np.linalg.norm(hist) + 1e-6
                lbp_feats.extend(hist / norm)

        combined = np.array(grad_feats[:64] + lbp_feats[:64], dtype=np.float32)
        norm = np.linalg.norm(combined)
        return (combined / norm) if norm > 0 else combined

    @staticmethod
    def compute_similarity(emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two normalized embedding vectors."""
        if emb1 is None or emb2 is None or len(emb1) != len(emb2):
            return 0.0
        n1 = np.linalg.norm(emb1)
        n2 = np.linalg.norm(emb2)
        if n1 < 1e-6 or n2 < 1e-6:
            return 0.0
        return float(np.dot(emb1 / n1, emb2 / n2))

    _cosine_similarity = compute_similarity

    def enroll_profile(
        self,
        name: str,
        face_crops: List[np.ndarray],
        is_owner: bool = False,
        notes: str = "",
        full_frames: Optional[List[np.ndarray]] = None,
        raw_faces: Optional[List[np.ndarray]] = None,
        align_matrices: Optional[List[np.ndarray]] = None
    ) -> Dict[str, Any]:
        """
        Enroll a new person or update an existing profile locally.
        Computes deep neural embeddings with multi-exemplar clustering.
        """
        clean_name = name.strip()
        if not clean_name:
            return {"success": False, "error": "Person name cannot be empty."}

        if not face_crops:
            return {"success": False, "error": "No face samples provided for enrollment."}

        embeddings = []
        for idx, crop in enumerate(face_crops):
            if crop is not None and crop.size > 0:
                frame = full_frames[idx] if full_frames and idx < len(full_frames) else None
                raw = raw_faces[idx] if raw_faces and idx < len(raw_faces) else None
                align_m = align_matrices[idx] if align_matrices and idx < len(align_matrices) else None
                emb = self.compute_face_embedding(crop, full_frame=frame, raw_face=raw, align_matrix=align_m)
                if np.linalg.norm(emb) > 0.1:
                    embeddings.append(emb)

        if not embeddings:
            return {"success": False, "error": "Could not extract valid face features from samples."}

        profile_id = clean_name.lower().replace(" ", "_")

        if profile_id in self._profiles:
            existing = self._profiles[profile_id]
            prev_samples = existing.get("samples", [])
            if prev_samples and len(prev_samples[0]) != len(embeddings[0]):
                prev_samples = []

            all_samples = prev_samples + [e.tolist() for e in embeddings]
            if len(all_samples) > 20:
                all_samples = all_samples[:4] + all_samples[-16:]

            sample_arr = np.array(all_samples, dtype=np.float32)
            centroid = np.mean(sample_arr, axis=0)
            norm = np.linalg.norm(centroid) + 1e-6
            centroid = (centroid / norm).tolist()

            total_count = existing.get("sample_count", 0) + len(embeddings)
            self._profiles[profile_id]["embedding"] = centroid
            self._profiles[profile_id]["samples"] = all_samples
            self._profiles[profile_id]["sample_count"] = total_count
            self._profiles[profile_id]["is_owner"] = is_owner or existing.get("is_owner", False)
            if notes:
                self._profiles[profile_id]["notes"] = notes

            self._save_profiles()
            return {
                "success": True,
                "profile_id": profile_id,
                "name": clean_name,
                "is_owner": self._profiles[profile_id]["is_owner"],
                "total_samples": total_count,
                "dim": len(centroid),
                "message": f"Updated neural profile for '{clean_name}' with {len(embeddings)} new sample(s)."
            }

        # New profile creation
        sample_arr = np.array(embeddings, dtype=np.float32)
        centroid = np.mean(sample_arr, axis=0)
        norm = np.linalg.norm(centroid) + 1e-6
        centroid = (centroid / norm).tolist()
        sample_list = [e.tolist() for e in embeddings]

        self._profiles[profile_id] = {
            "name": clean_name,
            "is_owner": is_owner,
            "sample_count": len(embeddings),
            "notes": notes,
            "created_at": time.time(),
            "embedding": centroid,
            "samples": sample_list
        }
        self._save_profiles()

        role_str = "Owner" if is_owner else "Person"
        return {
            "success": True,
            "profile_id": profile_id,
            "name": clean_name,
            "is_owner": is_owner,
            "samples_processed": len(embeddings),
            "dim": len(centroid),
            "message": f"{role_str} '{clean_name}' successfully enrolled with neural face recognition."
        }

    def enroll_person(self, name: str, face_crops: List[np.ndarray], is_owner: bool = False) -> Dict[str, Any]:
        """Convenience wrapper for enrolling any individual by name."""
        return self.enroll_profile(name=name, face_crops=face_crops, is_owner=is_owner)

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve single profile metadata without embedding vector."""
        if profile_id in self._profiles:
            p = dict(self._profiles[profile_id])
            p.pop("embedding", None)
            p.pop("samples", None)
            p["id"] = profile_id
            return p
        return None

    def list_enrolled_profiles(self) -> List[Dict[str, Any]]:
        """Return list of all enrolled people."""
        return [
            {
                "id": pid,
                "name": p["name"],
                "is_owner": p.get("is_owner", False),
                "sample_count": p.get("sample_count", 0),
                "notes": p.get("notes", ""),
                "created_at": p.get("created_at"),
                "embedding_dim": len(p.get("embedding", []))
            }
            for pid, p in self._profiles.items()
        ]

    def rename_profile(self, profile_id: str, new_name: str) -> bool:
        """Rename an enrolled person profile."""
        if profile_id in self._profiles and new_name.strip():
            self._profiles[profile_id]["name"] = new_name.strip()
            self._save_profiles()
            return True
        return False

    def delete_profile(self, profile_id: str) -> bool:
        """Remove an enrolled profile completely."""
        if profile_id in self._profiles:
            del self._profiles[profile_id]
            self._save_profiles()
            logger.info(f"Deleted face profile: {profile_id}")
            return True
        return False

    def recognize_faces(self, frame: np.ndarray) -> List[Dict[str, Any]]:
        """
        Detect all faces in the frame, match against enrolled profiles using deep embeddings,
        evaluate passive anti-spoofing liveness, and maintain temporal tracking continuity.
        """
        detected = self.detector.detect_faces(frame)
        if not detected:
            return []

        results = []
        now = time.time()

        for face in detected:
            crop = face.get("crop")
            loc = face.get("location")
            raw_face = face.get("raw")
            landmarks = face.get("landmarks")
            align_m = face.get("align_matrix")
            mesh_3d = face.get("mesh_3d")
            blendshapes = face.get("blendshapes", {})
            head_pose = face.get("head_pose", {})
            gaze = face.get("gaze", {})
            biometrics = face.get("biometrics", {})

            # Spatial center for temporal tracking continuity
            lx, ly = loc.get("x", 0), loc.get("y", 0)
            lw, lh = loc.get("width", 0), loc.get("height", 0)
            cx, cy = lx + lw // 2, ly + lh // 2
            track_key = f"trk_{int(cx // 45)}_{int(cy // 45)}"

            # 1. Evaluate Anti-Spoofing / Liveness
            liveness = self.liveness_analyzer.evaluate_liveness(
                track_key=track_key,
                face_crop=crop,
                biometrics=biometrics,
                head_pose=head_pose
            )

            # 2. Check for active temporal tracking lock
            cached_lock = None
            for key, track in list(self._recent_tracking.items()):
                if now - track["time"] > 2.2:
                    self._recent_tracking.pop(key, None)
                    continue
                dist = np.sqrt((cx - track["cx"]) ** 2 + (cy - track["cy"]) ** 2)
                if dist < max(lw, lh) * 1.1:
                    cached_lock = track
                    break

            # 3. Fast-path: Reuse biometric identity if track is actively locked
            if cached_lock is not None and cached_lock.get("verify_counter", 0) % 25 != 0:
                cached_lock["cx"] = cx
                cached_lock["cy"] = cy
                cached_lock["time"] = now
                cached_lock["verify_counter"] = cached_lock.get("verify_counter", 0) + 1

                is_owner = cached_lock.get("is_owner", False)
                results.append({
                    "identity": "owner" if is_owner else "enrolled",
                    "name": cached_lock["name"],
                    "confidence": cached_lock.get("confidence", 0.95),
                    "recognized": True,
                    "location": loc,
                    "landmarks": landmarks,
                    "mesh_3d": mesh_3d,
                    "blendshapes": blendshapes,
                    "head_pose": head_pose,
                    "gaze": gaze,
                    "biometrics": biometrics,
                    "liveness": liveness,
                    "track_id": cached_lock.get("track_id", "face_#1")
                })
                continue

            # 4. Full Deep Neural Embedding Extraction (ArcFace 512-d / SFace 128-d)
            probe_emb = self.compute_face_embedding(crop, full_frame=frame, raw_face=raw_face, align_matrix=align_m)

            best_match = None
            best_sim = -1.0

            # Match probe against enrolled profiles
            for pid, profile in self._profiles.items():
                ref_emb = np.array(profile["embedding"], dtype=np.float32)
                if len(ref_emb) != len(probe_emb):
                    continue

                sim_centroid = float(np.dot(probe_emb, ref_emb))

                samples = profile.get("samples", [])
                sim_samples = -1.0
                if samples:
                    for s in samples:
                        if len(s) == len(probe_emb):
                            dot = float(np.dot(probe_emb, np.array(s, dtype=np.float32)))
                            if dot > sim_samples:
                                sim_samples = dot

                profile_sim = max(sim_centroid, sim_samples)
                if profile_sim > best_sim:
                    best_sim = profile_sim
                    best_match = profile

            # Threshold determination based on embedding dimensionality (512 vs 128)
            is_512 = len(probe_emb) == 512
            is_owner_candidate = best_match and best_match.get("is_owner", False)
            if is_512:
                cutoff = self.ARCFACE_OWNER_THRESHOLD if is_owner_candidate else self.ARCFACE_THRESHOLD
            else:
                cutoff = self.SFACE_OWNER_THRESHOLD if is_owner_candidate else self.SFACE_THRESHOLD

            if cached_lock is None:
                self._track_counter += 1
                assigned_track_id = f"face_#{self._track_counter}"
            else:
                assigned_track_id = cached_lock.get("track_id", f"face_#{self._track_counter}")

            if best_match and best_sim >= cutoff:
                is_owner = best_match.get("is_owner", False)
                rec_name = best_match["name"]
                conf = round(min(best_sim, 0.99), 2)

                self._recent_tracking[rec_name.lower()] = {
                    "name": rec_name,
                    "is_owner": is_owner,
                    "confidence": conf,
                    "cx": cx,
                    "cy": cy,
                    "time": now,
                    "track_id": assigned_track_id,
                    "verify_counter": 1
                }

                results.append({
                    "identity": "owner" if is_owner else "enrolled",
                    "name": rec_name,
                    "confidence": conf,
                    "recognized": True,
                    "location": loc,
                    "landmarks": landmarks,
                    "mesh_3d": mesh_3d,
                    "blendshapes": blendshapes,
                    "head_pose": head_pose,
                    "gaze": gaze,
                    "biometrics": biometrics,
                    "liveness": liveness,
                    "track_id": assigned_track_id
                })
            elif cached_lock and best_match and best_match["name"] == cached_lock["name"] and best_sim >= (cutoff - 0.08):
                results.append({
                    "identity": "owner" if cached_lock["is_owner"] else "enrolled",
                    "name": cached_lock["name"],
                    "confidence": cached_lock["confidence"],
                    "recognized": True,
                    "location": loc,
                    "landmarks": landmarks,
                    "mesh_3d": mesh_3d,
                    "blendshapes": blendshapes,
                    "head_pose": head_pose,
                    "gaze": gaze,
                    "biometrics": biometrics,
                    "liveness": liveness,
                    "track_id": assigned_track_id
                })
            else:
                # Unknown person
                results.append({
                    "identity": "unknown",
                    "name": "Unknown Person",
                    "confidence": round(float(best_sim), 2) if best_sim > 0 else None,
                    "recognized": False,
                    "location": loc,
                    "landmarks": landmarks,
                    "mesh_3d": mesh_3d,
                    "blendshapes": blendshapes,
                    "head_pose": head_pose,
                    "gaze": gaze,
                    "biometrics": biometrics,
                    "liveness": liveness,
                    "track_id": assigned_track_id
                })

        return results
