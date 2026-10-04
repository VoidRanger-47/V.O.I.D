# core/agents/vision_agent.py
import os
from typing import Dict, Any
from core.agents.base import BaseAgent
from core.agents.protocol import AgentMessage, AgentMessageType
from core.security import PermissionLevel
from vision.vision_controller import vision_controller

class VisionAgent(BaseAgent):
    """
    Dedicated Vision Agent.
    Handles real-time webcam perception, object detection, face recognition,
    local image inspection, and visual reasoning.
    """
    def __init__(self):
        super().__init__(
            name="vision_agent",
            role="Perceives real-time visual environment, identifies objects, tracks owner identity, and inspects images",
            permission_level=PermissionLevel.LEVEL_2_READ_FILES,
            is_llm_assisted=False
        )
        self.vision = vision_controller

    def process(self, message: AgentMessage) -> AgentMessage:
        payload = message.payload or {}
        action = payload.get("action", "query").lower()
        query = payload.get("query", "")
        image_path = payload.get("image_path")

        # 1. Image file inspection
        if image_path and os.path.exists(image_path):
            file_size_kb = round(os.path.getsize(image_path) / 1024, 2)
            import cv2
            img = cv2.imread(image_path)
            if img is not None:
                objs = self.vision.detect_objects(img)
                faces = self.vision.detect_people(img)
                scene = self.vision.analyze_scene(img)
                res = f"Vision analysis: Image '{os.path.basename(image_path)}' ({file_size_kb} KB). Detected {len(objs)} objects, {len(faces)} faces. Scene: {scene.get('summary')}"
                return AgentMessage(
                    sender=self.name,
                    receiver=message.sender,
                    task_id=message.task_id,
                    mission_id=message.mission_id,
                    message_type=AgentMessageType.RESPONSE,
                    status="SUCCESS",
                    result=res,
                    payload={"image": image_path, "objects": objs, "faces": faces, "scene": scene}
                )

        # 2. Camera Controls & Enrollment Actions
        if action == "start":
            success = self.vision.start()
            res = "Camera online. Visual perception active." if success else "Failed to start camera."
            return self._create_response(message, res, {"active": success})

        elif action == "stop":
            self.vision.stop()
            return self._create_response(message, "Camera turned off and hardware released.", {"active": False})

        elif action == "scan" or action == "analyze":
            ctx = self.vision.get_current_context()
            res = self.vision.process_query(query or "Describe what you see.")
            return self._create_response(message, res.get("natural_response", ""), ctx)

        elif action in ("enroll", "enroll_person", "enroll_owner"):
            name = payload.get("name", "Owner")
            is_owner = payload.get("is_owner", action == "enroll_owner")
            samples = int(payload.get("samples", 6))
            notes = payload.get("notes", "")
            res = self.vision.enroll_person(name=name, is_owner=is_owner, samples_count=samples, notes=notes)
            return self._create_response(message, res.get("message", res.get("error", "")), res)

        elif action in ("list_people", "list_profiles", "get_profiles"):
            profiles = self.vision.list_people()
            names_str = ", ".join([f"{p['name']} ({'Owner' if p.get('is_owner') else 'Member'})" for p in profiles]) if profiles else "None"
            return self._create_response(message, f"Enrolled people in visual memory ({len(profiles)}): {names_str}", {"profiles": profiles})

        elif action in ("delete_person", "forget_person", "remove_profile"):
            profile_id = payload.get("profile_id") or payload.get("name", "").lower().replace(" ", "_")
            success = self.vision.delete_person(profile_id)
            msg = f"Profile '{profile_id}' removed from visual memory." if success else f"Profile '{profile_id}' not found."
            return self._create_response(message, msg, {"success": success, "profile_id": profile_id})

        elif action in ("people_seen_today", "visitors_today"):
            today_people = self.vision.get_people_seen_today()
            if today_people:
                summary = "People observed today:\n" + "\n".join([f"• {p['name']} (last seen at {p['last_seen_time']})" for p in today_people])
            else:
                summary = "No person sightings logged today yet."
            return self._create_response(message, summary, {"people_today": today_people})

        elif action in ("memories", "history", "recent_memories"):
            limit = int(payload.get("limit", 15))
            mems = self.vision.get_recent_memories(limit=limit)
            return self._create_response(message, f"Retrieved {len(mems)} recent visual observations.", {"memories": mems})

        # 3. Default Visual Query Processing & Memory Synthesis
        query_text = query or message.payload.get("prompt", "What do you see?")
        reasoning_res = self.vision.process_query(query_text)
        return self._create_response(
            message,
            reasoning_res.get("natural_response", "Visual processing complete."),
            reasoning_res
        )

    def _create_response(self, original_msg: AgentMessage, result_text: str, payload: Dict[str, Any]) -> AgentMessage:
        return AgentMessage(
            sender=self.name,
            receiver=original_msg.sender,
            task_id=original_msg.task_id,
            mission_id=original_msg.mission_id,
            message_type=AgentMessageType.RESPONSE,
            status="SUCCESS",
            result=result_text,
            payload=payload
        )
