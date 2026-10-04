# core/router.py
"""
Executive Intent Router (Fast Path vs Deep Path) for V.O.I.D.
Provides ultra-low-latency deterministic routing before invoking the main model,
protecting 4 GB VRAM from being wasted on trivial calculations or system queries.
"""

import re
import time
import datetime
from enum import Enum
from typing import Dict, Any, Tuple, Optional

from core.tool_registry import tool_registry
from core.state_manager import state_manager
from skills.math import handle_math
from skills.computer_control import is_app_launch_request, extract_app_target, launch_application, get_local_system_stats
from void_memory.memory import void_memory


class ExecutionPath(str, Enum):
    FAST_PATH = "FAST_PATH"  # Deterministic tool execution (< 50ms, 0 VRAM waste)
    DEEP_PATH = "DEEP_PATH"  # Multi-Agent Planner -> DAG -> Workspace -> Verification


class IntentClass(str, Enum):
    CONVERSATION = "conversation"
    CODING = "coding"
    DEBUGGING = "debugging"
    MATH = "math"
    SYSTEM = "system"
    VISION = "vision"
    VOICE = "voice"
    PHONE = "phone"
    MEMORY = "memory"
    RESEARCH = "research"
    DOCUMENT = "document"
    AUTOMATION = "automation"
    MULTI_AGENT = "multi_agent"
    UNKNOWN = "unknown"


class ExecutiveRouter:
    """
    Intelligent front-door classifier for all V.O.I.D. user queries.
    Diverts deterministic operations into the Fast Path with ultra-low latency.
    """
    _instance: Optional['ExecutiveRouter'] = None

    def __init__(self):
        self.tools = tool_registry
        self.memory = void_memory

    @classmethod
    def get_instance(cls) -> 'ExecutiveRouter':
        if cls._instance is None:
            cls._instance = ExecutiveRouter()
        return cls._instance

    def classify_intent(self, query: str) -> Tuple[IntentClass, float]:
        """
        Classifies user query into one of the specialized intent classes with confidence score.
        """
        clean = (query or "").strip()
        low = clean.lower()

        if not clean:
            return IntentClass.UNKNOWN, 1.0

        # 1. Multi-Agent Complex Tasks (Diagnostics, Refactoring, Architecture, Multi-step)
        if any(k in low for k in ["diagnose my project", "why isn't my project", "analyze this project", "find bugs", "performance bottlenecks", "suggest improvements", "debug my code", "audit my repo", "build a plan", "multi-step"]):
            return IntentClass.MULTI_AGENT, 0.98

        # 2. Math Intent
        is_math = bool(
            re.search(r"^\s*(\d+[\d\s\+\-\*\/\^\(\)\.%,]*\d+)\s*$", clean) or
            ("=" in clean and any(c.isalpha() for c in clean)) or
            re.search(r"\b(solve|calculate|evaluate|derivative|integral|sin|cos|tan|matrix|determinant|sqrt)\b", low) or
            re.search(r"\d+\s*[\+\-\*\/xX×÷\^]\s*\d+", clean)
        )
        if is_math and not any(k in low for k in ["how to code", "write a function", "explain", "project", "bugs", "bottleneck"]):
            return IntentClass.MATH, 0.95

        # 3. System Telemetry / OS Intent
        if any(k in low for k in ["system stats", "cpu usage", "ram usage", "vram usage", "gpu memory", "battery status", "hardware metrics", "what time is it", "current time", "what date", "today's date"]):
            return IntentClass.SYSTEM, 0.95

        # 4. Memory Direct Intent
        if any(k in low for k in ["forget that", "forget what i said", "delete memory", "clear memory"]) or \
           ("remember" in low and not any(k in low for k in ["do you remember", "can you remember", "remember when"])):
            return IntentClass.MEMORY, 0.95

        # 5. Computer Control Intent
        if is_app_launch_request(clean) or any(k in low for k in ["open vscode", "open vs code", "open notepad", "open calculator", "open terminal"]):
            return IntentClass.COMPUTER_CONTROL if hasattr(IntentClass, "COMPUTER_CONTROL") else IntentClass.SYSTEM, 0.92

        # 6. Phone / ADB Intent
        if any(k in low for k in ["unlock phone", "lock phone", "call ", "dial ", "send sms", "jiocinema", "whatsapp phone", "battery level on phone"]):
            return IntentClass.PHONE, 0.90

        # 7. Vision Intent
        if any(k in low for k in ["what do you see", "describe scene", "who is in front of camera", "turn on camera", "turn off camera", "take snapshot", "inspect this image"]):
            return IntentClass.VISION, 0.90

        # 8. Document Reading Intent
        if any(k in low for k in ["read pdf", "read document", "summarize document", "analyze pdf"]):
            return IntentClass.DOCUMENT, 0.88

        # 9. Web Research Intent
        if any(k in low for k in ["search web", "check online", "latest news", "search google"]):
            return IntentClass.RESEARCH, 0.88

        # 10. Coding & Engineering Intent
        if any(k in low for k in ["def ", "class ", "function", "write a script", "python code", "implement", "refactor", "unit test"]):
            return IntentClass.CODING, 0.85

        return IntentClass.CONVERSATION, 0.70

    def route(
        self,
        query: str,
        force_search: bool = False,
        thinking_mode: bool = False
    ) -> Tuple[ExecutionPath, Optional[str], IntentClass]:
        """
        Routes the request to FAST_PATH (direct deterministic response) or DEEP_PATH.
        Returns: (ExecutionPath, fast_path_response_or_none, IntentClass)
        """
        intent, confidence = self.classify_intent(query)
        clean = query.strip()
        low = clean.lower()

        # If user explicitly requested web search or thinking mode, use Deep Path
        if force_search or thinking_mode or intent == IntentClass.MULTI_AGENT:
            return ExecutionPath.DEEP_PATH, None, intent

        # ==========================================
        # FAST PATH CANDIDATES (Deterministic, 0 VRAM)
        # ==========================================

        # Fast Math
        if intent == IntentClass.MATH:
            try:
                ans = handle_math(clean)
                return ExecutionPath.FAST_PATH, str(ans), intent
            except Exception:
                return ExecutionPath.DEEP_PATH, None, intent

        # Fast System Time
        if any(k in low for k in ["what time", "current time", "what date", "today's date", "system time"]):
            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S (%A)")
            return ExecutionPath.FAST_PATH, f"The current system time is {now_str}.", IntentClass.SYSTEM

        # Fast Hardware Status
        if any(k in low for k in ["system stats", "cpu usage", "ram usage", "vram usage", "hardware status", "system metrics"]):
            stats_str = get_local_system_stats()
            return ExecutionPath.FAST_PATH, stats_str, IntentClass.SYSTEM

        # Fast App Launch
        if is_app_launch_request(clean):
            app_target = extract_app_target(clean)
            launch_res = launch_application(app_target)
            return ExecutionPath.FAST_PATH, launch_res, IntentClass.SYSTEM

        # Fast Memory Forget
        if any(k in low for k in ["forget that", "forget what i said", "delete memory", "clear memory"]):
            count = self.memory.forget_memory(clean)
            return ExecutionPath.FAST_PATH, f"Memory updated: removed {count} associated record(s).", IntentClass.MEMORY

        # Fast Memory Direct Fact Retention
        if "remember that" in low or "remember this:" in low:
            fact = clean.replace("remember that", "").replace("remember this:", "").strip()
            self.memory.store_memory(fact, tier="semantic", importance=0.8)
            return ExecutionPath.FAST_PATH, f"Confirmed. Stored to semantic long-term memory: '{fact}'", IntentClass.MEMORY

        # Everything else routes to Deep Path
        return ExecutionPath.DEEP_PATH, None, intent


executive_router = ExecutiveRouter.get_instance()
