"""
skills/router.py
Comprehensive Intelligent Skill Router for V.O.I.D.
Deterministically and heuristically decides whether to route incoming prompts to:
- Coding (AST check, Python execution, algorithmic synthesis)
- Math (arithmetic, linear algebra, calculus, equations)
- Web Search (facts, live documentation, internet queries)
- Memory (facts, user preferences, project knowledge, conversation recall)
- Computer Control (desktop application launcher, desktop management)
- Phone Control (Android ADB device actions)
- System Monitor (CPU, GPU, RAM, VRAM, storage, thermals)
- Project Awareness (codebase structure, file tree, symbol index)
- Multi-Agent Pipeline (complex multi-step planning, coding, execution, verification)
- General Neural Chat
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, Tuple


class SkillType(str, Enum):
    CODING = "coding"
    MATH = "math"
    WEB_SEARCH = "web_search"
    MEMORY = "memory"
    VISION = "vision"
    COMPUTER_CONTROL = "computer_control"
    PHONE_CONTROL = "phone_control"
    SYSTEM_MONITOR = "system_monitor"
    PROJECT_AWARENESS = "project_awareness"
    MULTI_AGENT = "multi_agent_pipeline"
    IMAGE_GENERATION = "image_generation"
    PLUGIN = "plugin"
    CHAT = "chat"


@dataclass
class SkillDecision:
    skill: SkillType
    confidence: float
    reason: str
    is_deterministic: bool = False
    parameters: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "skill": self.skill.value,
            "confidence": self.confidence,
            "reason": self.reason,
            "is_deterministic": self.is_deterministic,
            "parameters": self.parameters
        }


class SkillRouter:
    """
    Intelligent skill intent classifier.
    Directs queries to the optimal specialized engine or multi-agent pipeline.
    """
    _instance: Optional['SkillRouter'] = None

    def __init__(self):
        pass

    @classmethod
    def get_instance(cls) -> 'SkillRouter':
        if cls._instance is None:
            cls._instance = SkillRouter()
        return cls._instance

    def route(self, query: str, force_search: bool = False, thinking_mode: bool = False) -> SkillDecision:
        text = (query or "").strip()
        low = text.lower()

        # 1. Multi-Agent Pipeline Triggers (Multi-step goals, "plan and build", "create and test")
        if any(trigger in low for trigger in [
            "agent pipeline", "run agent", "planner:", "multi-agent",
            "plan and build", "research and write", "build and test",
            "create a full pipeline", "execute complete workflow"
        ]):
            return SkillDecision(
                skill=SkillType.MULTI_AGENT,
                confidence=0.98,
                reason="Detected multi-stage objective requiring Planner -> Researcher -> Coder -> Executor -> Verifier pipeline.",
                is_deterministic=False,
                parameters={"goal": text}
            )

        # 2. Dedicated Phone ADB Actions
        phone_triggers = ["unlock phone", "lock phone", "call ", "dial ", "send sms", "volume up", "volume down", "mute phone", "phone battery", "phone status"]
        if any(k in low for k in phone_triggers) or (("phone" in low or "adb" in low) and not any(k in low for k in ["open", "launch"])):
            return SkillDecision(
                skill=SkillType.PHONE_CONTROL,
                confidence=0.95,
                reason="Detected Android phone automation intent.",
                is_deterministic=True,
                parameters={"action_text": text}
            )

        # 3. Computer Control & System Power Actions (Shutdown, Restart, Abort)
        if any(term in low for term in [
            "shutdown", "shut down", "turn off the laptop", "turn off the pc", "turn off computer",
            "restart the laptop", "restart the pc", "restart computer", "reboot", "cancel shutdown", "abort shutdown"
        ]):
            return SkillDecision(
                skill=SkillType.COMPUTER_CONTROL,
                confidence=0.98,
                reason="Operating system power management instruction.",
                is_deterministic=True,
                parameters={"action": "system_power", "raw_query": text}
            )

        if low.startswith("open ") or low.startswith("launch ") or "start app " in low:
            app_name = re.sub(r"^(open|launch|start app)\s+", "", text, flags=re.I).strip()
            return SkillDecision(
                skill=SkillType.COMPUTER_CONTROL,
                confidence=0.95,
                reason=f"Application launch request for '{app_name}'.",
                is_deterministic=True,
                parameters={"app_name": app_name}
            )

        # 4. Project Awareness & Codebase Architecture
        if any(term in low for term in [
            "codebase structure", "project structure", "architecture overview",
            "list files in project", "what modules exist", "project files",
            "codebase map", "file tree", "symbols in project"
        ]):
            return SkillDecision(
                skill=SkillType.PROJECT_AWARENESS,
                confidence=0.95,
                reason="Query concerns codebase file hierarchy and repository architecture.",
                is_deterministic=True,
                parameters={"scope": "workspace"}
            )

        # 5. Local Hardware & System Monitor
        if any(term in low for term in [
            "system stats", "cpu usage", "ram usage", "vram usage",
            "gpu stats", "disk space", "hardware status", "system metrics", "live telemetry"
        ]):
            return SkillDecision(
                skill=SkillType.SYSTEM_MONITOR,
                confidence=0.95,
                reason="Hardware and operating system telemetry query.",
                is_deterministic=True,
                parameters={}
            )

        # 6. Computer Vision & Webcam Perception
        vision_triggers = [
            "activate vision", "start vision", "turn on vision", "enable vision", "open vision",
            "deactivate vision", "disable vision", "stop vision", "turn off vision", "kill vision",
            "close vision", "shut vision", "shutdown vision", "halt vision",
            "turn on camera", "open camera", "start camera", "enable camera", "launch camera",
            "turn off camera", "close camera", "stop camera", "deactivate camera", "disable camera",
            "kill camera", "shut camera", "shutdown camera", "halt camera", "stop watching",
            "what do you see", "what am i holding", "look around", "scan this", "describe what you see",
            "who is here", "who do you see", "who is that", "learn my face", "enroll my face",
            "recognize my face", "vision status", "camera status", "did you see my", "what was on my desk"
        ]
        if any(t in low for t in vision_triggers) or (("camera" in low or "vision" in low) and any(w in low for w in ["activate", "deactivate", "on", "off", "stop", "close", "disable", "kill", "halt", "see", "show", "feed", "look", "status", "scan", "capture", "snapshot"])):
            return SkillDecision(
                skill=SkillType.VISION,
                confidence=0.95,
                reason="Computer vision perception, camera control, or visual reasoning query.",
                is_deterministic=True,
                parameters={"query": text}
            )

        # 7. Offline Image Generation
        image_triggers = [
            "generate image", "create image", "render image", "draw an image", "generate an image",
            "draw a picture", "create picture", "generate art", "create artwork", "paint an image",
            "generate photo", "make an image", "render art", "concept art of"
        ]
        if (
            any(t in low for t in image_triggers)
            or low.startswith("draw ")
            or low.startswith("paint ")
            or low.startswith("sketch ")
            or (("generate" in low or "draw" in low or "render" in low or "create" in low or "make" in low or "paint" in low) and any(w in low for w in ["image", "picture", "artwork", "painting", "photo", "illustration", "sketch"]))
        ):
            return SkillDecision(
                skill=SkillType.IMAGE_GENERATION,
                confidence=0.96,
                reason="Offline local image generation request.",
                is_deterministic=True,
                parameters={"prompt": text}
            )

        # 8. Memory & Knowledge Recall
        if any(term in low for term in [
            "what do you remember", "my preferences", "recall from memory",
            "what is my project", "check your memory", "list memories", "memory inspector"
        ]):
            return SkillDecision(
                skill=SkillType.MEMORY,
                confidence=0.92,
                reason="Explicit long-term memory query or preference recall.",
                is_deterministic=True,
                parameters={"query": text}
            )

        # 7. Math & Formula Engine
        has_math_pattern = bool(
            re.search(r"(\d+\s*[\+\-\*\/\^%]\s*\d+)", text) or
            ("=" in text and any(c.isalpha() for c in text) and not text.startswith("def ")) or
            re.search(r"\b(d/dx|integral|sin|cos|tan|matrix|determinant|sqrt|calculate|eval)\b", low)
        )
        if has_math_pattern and not force_search and not any(k in low for k in ["python", "def ", "class ", "http", "www"]):
            return SkillDecision(
                skill=SkillType.MATH,
                confidence=0.90,
                reason="Mathematical expression, calculus, or arithmetic query detected.",
                is_deterministic=True,
                parameters={"expression": text}
            )

        # 8. Direct Python Execution or Self-Healing Coding
        if low.startswith("run python:") or low.startswith("execute python:") or low.startswith("run code:") or "```python" in text:
            return SkillDecision(
                skill=SkillType.CODING,
                confidence=0.98,
                reason="Direct Python sandbox execution request.",
                is_deterministic=True,
                parameters={"mode": "sandbox_exec"}
            )

        # 9. General Coding / Engineering Query
        coding_terms = ["write a python", "write a function", "implement a class", "debug this", "refactor", "syntax error", "ast", "algorithm", "fix the bug"]
        if any(t in low for t in coding_terms) or (("function" in low or "class" in low or "def " in low) and "python" in low):
            return SkillDecision(
                skill=SkillType.CODING,
                confidence=0.88,
                reason="Software engineering, syntax implementation, or coding logic query.",
                is_deterministic=False,
                parameters={"mode": "coding_persona"}
            )

        # 10. Web Search (Explicit or Forced)
        if force_search or low.startswith("search ") or low.startswith("google ") or "search web" in low:
            return SkillDecision(
                skill=SkillType.WEB_SEARCH,
                confidence=0.92,
                reason="Explicit web search query.",
                is_deterministic=True,
                parameters={"query": text}
            )

        # 11. Modular Dynamic Plugins (e.g. Gmail Analyzer, custom user plugins)
        try:
            from core.plugin_manager import PluginManager
            plugin = PluginManager.get_instance().can_handle(text)
            if plugin:
                return SkillDecision(
                    skill=SkillType.PLUGIN,
                    confidence=0.96,
                    reason=f"Matched modular plugin '{plugin.metadata.name}' [{plugin.metadata.id}].",
                    is_deterministic=True,
                    parameters={"plugin_id": plugin.metadata.id}
                )
        except Exception:
            pass

        # 12. General Neural Chat / Multi-turn
        return SkillDecision(
            skill=SkillType.CHAT,
            confidence=0.75,
            reason="Natural conversation and reasoning.",
            is_deterministic=False,
            parameters={}
        )


skill_router = SkillRouter.get_instance()
