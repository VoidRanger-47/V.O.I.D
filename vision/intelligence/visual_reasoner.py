"""
vision/intelligence/visual_reasoner.py
Cognitive reasoning engine for V.O.I.D. Vision.
Transforms raw visual detections, facial recognition, hand gestures, and scene geometry
into structured visual understanding, natural conversational dialogue, and hybrid multimodal reasoning.
"""

import re
import time
import logging
from typing import Dict, Any, List, Optional
import numpy as np
from vision.intelligence.visual_memory import VisualMemory

logger = logging.getLogger("void.vision.reasoner")

class VisualReasoner:
    """
    Synthesizes vision detections and visual memory into intelligent natural responses.
    Supports hybrid reasoning: online Google Gemini 2.0 / Flash multimodal analysis
    with 100% autonomous local offline cognitive reasoning fallback.
    """

    def __init__(self, visual_memory: Optional[VisualMemory] = None):
        self.memory = visual_memory or VisualMemory()

    def answer_visual_query(
        self,
        query: str,
        current_perception: Dict[str, Any],
        frame: Optional[np.ndarray] = None,
        image_base64: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a visual question/command against current camera perception, image frame, and visual memory.
        """
        # Unwrap if nested under 'perception' key
        if "perception" in current_perception and isinstance(current_perception["perception"], dict):
            current_perception = current_perception["perception"]

        q_low = query.lower().strip()
        objects = current_perception.get("objects", [])
        faces = current_perception.get("faces", [])
        scene = current_perception.get("scene", {})
        gestures = current_perception.get("gestures", [])
        active_camera = bool(current_perception.get("camera_active", False))

        # 1. Handle Memory Queries (e.g., "what was on my desk earlier?", "did you see my headphones?")
        if any(w in q_low for w in ["earlier", "yesterday", "today", "did you see", "where is my", "where did i leave", "what was on"]):
            return self._answer_from_memory(query, q_low)

        # 2. If camera is inactive and query needs live sight
        if not active_camera and not objects and not faces:
            return {
                "query": query,
                "natural_response": "Vision system is currently on standby. Say 'activate vision' or visit the [Vision HUD](/vision) to initiate optical sensors.",
                "interpretation": {"status": "standby"},
                "raw_data": current_perception
            }

        # 3. "What am I holding?" / "What is in my hand?"
        if any(w in q_low for w in ["holding", "in my hand", "showing you", "what is this", "identify this", "what do i have"]):
            return self._reason_holding_object(query, objects, gestures, current_perception)

        # 4. "Who is here?" / "Who do you see?" / "Who am I?" / "Identify me"
        people_triggers = [
            "who do you see", "who is that", "who is here", "recognize me", "do you know me",
            "who am i", "identify me", "who is in front", "can you see me", "do you see me",
            "look at me", "who are you looking at", "tell me who i am", "am i here",
            "who's there", "who is there", "anybody here", "anyone here", "recognize my face"
        ]
        if any(w in q_low for w in people_triggers):
            return self._reason_people(query, faces, current_perception)

        # 5. Hybrid Multimodal Vision check (if user asks complex / open-ended questions like "explain", "read text", "what is wrong")
        deep_triggers = ["explain", "read", "written", "text on", "solve", "how does", "what kind of", "analyze this", "inspect"]
        if any(t in q_low for t in deep_triggers) and (frame is not None or image_base64 is not None):
            cloud_resp = self._try_cloud_multimodal(query, frame, image_base64)
            if cloud_resp:
                return {
                    "query": query,
                    "natural_response": cloud_resp,
                    "interpretation": {"engine": "gemini_multimodal_vision", "status": "online_analysis"},
                    "raw_data": current_perception
                }

        # 6. "What do you see?" / "Look around" / "Describe the scene" / General Scene
        return self._reason_general_scene(query, objects, faces, scene, current_perception, gestures)

    def _try_cloud_multimodal(self, query: str, frame: Optional[np.ndarray], image_base64: Optional[str]) -> Optional[str]:
        """Attempt online Gemini 2.0 multimodal reasoning if configured; returns None if offline."""
        try:
            from void_cloud.cloud_manager import CloudManager
            cloud_mgr = CloudManager.get_instance()
            client = cloud_mgr.gemini_client
            if client and client.is_configured():
                img_data = image_base64
                if not img_data and frame is not None:
                    from vision.camera.frame_processor import FrameProcessor
                    img_data = FrameProcessor.to_jpeg_bytes(frame, quality=80)
                if img_data:
                    prompt = f"You are V.O.I.D. (Virtual Omnipresent Intelligent Device) Vision Intelligence. Answer this concise question about the camera frame: '{query}'"
                    return client.generate_vision_content(prompt, img_data)
        except Exception as e:
            logger.debug(f"Cloud multimodal reasoning skipped: {e}")
        return None

    def _reason_holding_object(
        self,
        query: str,
        objects: List[Dict[str, Any]],
        gestures: List[Dict[str, Any]],
        raw_perception: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Identify what the user is presenting or holding using spatial proximity."""
        # Non-person objects
        held_candidates = [o for o in objects if o.get("label") != "person"]

        if not held_candidates:
            resp = "I can see you, but I don't clearly detect an object being held in front of the camera right now."
            interp = {"held_object": None, "confidence": 0.0}
        else:
            # If a hand gesture is detected, find object closest to hand center
            best = None
            hand = gestures[0] if gestures else None
            if hand and hand.get("location"):
                h_loc = hand["location"]
                hx = h_loc.get("x", 0) + h_loc.get("width", 0) / 2.0
                hy = h_loc.get("y", 0) + h_loc.get("height", 0) / 2.0

                min_dist = float("inf")
                for cand in held_candidates:
                    loc = cand.get("location", {})
                    ox = loc.get("x", 0) + loc.get("width", 0) / 2.0
                    oy = loc.get("y", 0) + loc.get("height", 0) / 2.0
                    dist = ((hx - ox)**2 + (hy - oy)**2)**0.5
                    if dist < min_dist:
                        min_dist = dist
                        best = cand

            if best is None:
                # Default to highest confidence object
                best = max(held_candidates, key=lambda x: x.get("confidence", 0.0))

            label = best.get("label", "object")
            conf = best.get("confidence", 0.0)
            
            article = "an" if label[0] in "aeiou" else "a"
            resp = f"It appears to be {article} **{label}** (confidence: {int(conf*100)}%)."
            interp = {"held_object": label, "confidence": conf, "location": best.get("location")}

            # Record in visual memory
            self.memory.record_observation(
                event_type="OBJECT_INSPECTED",
                object_name=label,
                context="held_by_user",
                confidence=conf,
                importance=0.7
            )

        return {
            "query": query,
            "natural_response": resp,
            "interpretation": interp,
            "raw_data": raw_perception
        }

    def _reason_people(
        self,
        query: str,
        faces: List[Dict[str, Any]],
        raw_perception: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Synthesize who is visible in the frame."""
        subject = raw_perception.get("subject", {}) if isinstance(raw_perception.get("subject"), dict) else {}
        subj_ident = subject.get("identity", {}) if isinstance(subject.get("identity"), dict) else {}

        if not faces:
            if subj_ident.get("name") and subj_ident.get("name") != "Unidentified Subject":
                name = subj_ident.get("name")
                role = subj_ident.get("role", "Subject")
                conf = subj_ident.get("confidence_pct", 85)
                resp = f"Identity confirmed: **{name}** ({role}, ~{conf}% confidence)."
                interp = {"people_count": 1, "owner_recognized": subj_ident.get("is_owner", False), "owner_name": name, "enrolled_identities": [name]}
            elif subject.get("detected"):
                resp = "I detect a person in front of the camera, but facial features are not clearly aligned for positive identification yet. Please face the optical sensor directly."
                interp = {"people_count": 1, "enrolled_identities": []}
            else:
                resp = "I do not detect any human faces in the camera frame right now."
                interp = {"people_count": 0, "enrolled_identities": []}
        else:
            owner_face = next((f for f in faces if f.get("identity") == "owner"), None)
            unknown_count = sum(1 for f in faces if f.get("identity") == "unknown")
            enrolled_others = [f.get("name") for f in faces if f.get("identity") == "enrolled"]

            parts = []
            if owner_face:
                parts.append(f"Identity confirmed: **{owner_face.get('name', 'Owner')}** ({int(owner_face.get('confidence', 0.9)*100)}% confidence)")
            if enrolled_others:
                parts.append(f"Enrolled member(s): {', '.join(enrolled_others)}")
            if unknown_count > 0:
                parts.append(f"{unknown_count} unknown person{'s' if unknown_count > 1 else ''}")

            resp = ". ".join(parts) + "."
            interp = {
                "people_count": len(faces),
                "owner_recognized": owner_face is not None,
                "owner_name": owner_face.get("name") if owner_face else None,
                "unknown_count": unknown_count
            }

        return {
            "query": query,
            "natural_response": resp,
            "interpretation": interp,
            "raw_data": raw_perception
        }

    def _reason_general_scene(
        self,
        query: str,
        objects: List[Dict[str, Any]],
        faces: List[Dict[str, Any]],
        scene: Dict[str, Any],
        raw_perception: Dict[str, Any],
        gestures: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Describe the whole environment and surroundings."""
        lighting = scene.get("lighting", "normal")
        env = scene.get("environment", "indoor")
        gestures = gestures or []
        
        # Identity breakdown
        owner_face = next((f for f in faces if f.get("identity") == "owner"), None)
        other_people = sum(1 for f in faces if f.get("identity") != "owner")

        # Object listing
        obj_names = [o.get("label") for o in objects if o.get("label") and o.get("label") != "person"]
        unique_objs = list(dict.fromkeys(obj_names))

        sentences = []
        if lighting == "dark":
            sentences.append("The environment is currently dark or the camera is covered.")
        elif owner_face:
            sentences.append(f"I see you, {owner_face.get('name', 'User')}.")
        elif other_people > 0:
            sentences.append(f"I see {other_people} person{'s' if other_people > 1 else ''} in the room.")

        if gestures:
            g_names = [g.get("gesture") for g in gestures if g.get("gesture") and g.get("gesture") != "hand_present"]
            if g_names:
                sentences.append(f"Detected gesture: {g_names[0]}.")

        if unique_objs:
            items_str = ", ".join(unique_objs[:5])
            if len(unique_objs) > 5:
                items_str += f", and {len(unique_objs)-5} other items"
            sentences.append(f"On-screen objects detected: {items_str}.")
        elif not sentences:
            sentences.append("The camera view is clear, but no specific recognized objects are currently highlighted.")

        natural_resp = " ".join(sentences)

        return {
            "query": query,
            "natural_response": natural_resp,
            "interpretation": {
                "environment": env,
                "lighting": lighting,
                "objects_detected": unique_objs,
                "people_detected": len(faces)
            },
            "raw_data": raw_perception
        }

    def _answer_from_memory(self, query: str, q_low: str) -> Dict[str, Any]:
        """Answer questions by querying persistent visual memory for people and objects."""
        # 1. Check if user is asking about people seen today or earlier
        if any(w in q_low for w in ["who was here", "who was in", "who came by", "who visited", "who did you see", "who have you seen", "anyone in my room", "people seen today"]):
            today_people = self.memory.query_people_seen_today()
            if today_people:
                names = [f"• **{p['name']}** (last seen at {p['last_seen_time'].split(' ')[1]}, {p['sightings_count']} times)" for p in today_people]
                resp = "People recorded in visual memory today:\n" + "\n".join(names)
            else:
                resp = "I haven't recorded any person sightings in visual memory today yet."

            return {
                "query": query,
                "natural_response": resp,
                "interpretation": {"source": "visual_memory", "people_today": today_people},
                "raw_data": {"query": query}
            }

        # 2. Check if asking about a specific person (e.g. "did you see Alice?", "where is Bob?", "when was John here?")
        name_match = re.search(r"(?:see|seen|where is|is|about|know|find|was)\s+([a-zA-Z]+)", query, re.IGNORECASE)
        candidate_name = name_match.group(1).strip() if name_match else None
        
        stop_words = {"my", "the", "a", "an", "this", "that", "it", "any", "your", "today", "yesterday", "earlier", "here", "there", "what", "who", "where", "when"}
        if candidate_name and candidate_name.lower() not in stop_words:
            person_history = self.memory.query_person_history(candidate_name, limit=3)
            if person_history:
                latest = person_history[0]
                resp = f"Yes, I recorded **{latest.get('person', candidate_name)}** in {latest.get('context', 'camera view')} at **{latest.get('iso_time')}**."
                return {
                    "query": query,
                    "natural_response": resp,
                    "interpretation": {"source": "visual_memory", "person": latest},
                    "raw_data": {"query": query}
                }

        # 3. Check for specific objects (e.g., "where is my phone?", "did you see my keys?")
        obj_match = re.search(r"(?:see|find|where is|where are|where did i leave|did you spot)\s+(?:my\s+|the\s+)?([a-zA-Z0-9_\- ]+)", query, re.IGNORECASE)
        candidate_obj = obj_match.group(1).strip() if obj_match else None
        if candidate_obj:
            candidate_obj = re.sub(r"\b(earlier|today|yesterday|now|please)\b", "", candidate_obj, flags=re.IGNORECASE).strip()

        if candidate_obj and candidate_obj.lower() not in stop_words:
            records = self.memory.query_by_object(candidate_obj, limit=2)
            if records:
                latest = records[0]
                resp = f"I last saw your **{latest.get('object', candidate_obj)}** in **{latest.get('context', 'workspace')}** at {latest.get('iso_time')}."
                return {
                    "query": query,
                    "natural_response": resp,
                    "interpretation": {"source": "visual_memory", "object": latest},
                    "raw_data": {"query": query}
                }

        # Default fallback from memory
        recent = self.memory.query_recent(limit=3)
        if recent:
            items = [f"• {r.get('event_type')}: {r.get('object') or r.get('person')} ({r.get('context')})" for r in recent if r.get('object') or r.get('person')]
            resp = "Here are the most recent visual records in memory:\n" + "\n".join(items) if items else "Visual memory has no recent object sightings recorded."
        else:
            resp = "I couldn't locate any records matching that query in visual memory."

        return {
            "query": query,
            "natural_response": resp,
            "interpretation": {"source": "visual_memory"},
            "raw_data": {"query": query}
        }
