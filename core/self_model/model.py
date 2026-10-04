# core/self_model/model.py
"""
Persistent Self Model for V.O.I.D.
Maintains introspective self-awareness:
- Available capabilities, installed tools, and registered agents
- Hardware bounds (RTX 3050 4GB VRAM, Ryzen 5 5600H, 16GB RAM)
- Domain-specific confidence scores and known weaknesses
- Success/failure rates per skill and active project objectives
"""

import json
import os
import time
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict

from core.vram_manager import vram_manager, VRAMThreshold


@dataclass
class CapabilityAssessment:
    can_perform: bool
    confidence: float
    limitations: List[str] = field(default_factory=list)
    hardware_cost: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    rationale: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SelfModel:
    """
    Introspective Self-Model for V.O.I.D.
    Answers: 'What can I do? What are my current limits? What are my weaknesses?'
    """
    _instance: Optional['SelfModel'] = None

    def __init__(self, state_file: str = "void_memory/system_identity.json"):
        self.state_file = state_file
        self.vram_mgr = vram_manager

        # Default hardware specification
        self.hardware_profile = {
            "gpu": "NVIDIA GeForce RTX 3050 Laptop GPU",
            "vram_total_mb": 4096.0,
            "vram_safe_limit_mb": 2867.0,
            "cpu": "AMD Ryzen 5 5600H (6 Cores, 12 Threads)",
            "ram_total_gb": 16.0,
            "os": "Windows 11"
        }

        # Domain confidence metrics (self-calibrating)
        self.domain_confidence: Dict[str, float] = {
            "python_development": 0.95,
            "mathematics_and_calculus": 0.92,
            "system_diagnostics": 0.96,
            "desktop_automation": 0.88,
            "phone_control_adb": 0.89,
            "offline_voice_piper_whisper": 0.86,
            "computer_vision": 0.78,
            "web_research_synthesis": 0.82,
            "robotics_and_sensors": 0.45,
            "cloud_infrastructure": 0.70
        }

        # Known weaknesses and constraints
        self.known_weaknesses: Dict[str, List[str]] = {
            "computer_vision": ["low_light_environments", "occluded_faces", "extreme_camera_angles"],
            "web_research": ["paywalled_sources", "javascript_heavy_spas", "offline_environments"],
            "coding": ["kernel_level_drivers", "legacy_fortran_cobol"],
            "hardware": ["concurrent_model_loading_oom", "long_context_4gb_vram_limit"]
        }

        # Operational skill success records
        self.skill_history: Dict[str, Dict[str, int]] = {
            "coding": {"success": 0, "fail": 0},
            "math": {"success": 0, "fail": 0},
            "system": {"success": 0, "fail": 0},
            "vision": {"success": 0, "fail": 0},
            "research": {"success": 0, "fail": 0}
        }

        self._load_state()

    @classmethod
    def get_instance(cls) -> 'SelfModel':
        if cls._instance is None:
            cls._instance = SelfModel()
        return cls._instance

    def _load_state(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, "r") as f:
                    data = json.load(f)
                    if "domain_confidence" in data:
                        self.domain_confidence.update(data["domain_confidence"])
                    if "skill_history" in data:
                        self.skill_history.update(data["skill_history"])
            except Exception as e:
                print(f"ℹ️ SelfModel state load notice: {e}")

    def save_state(self):
        try:
            os.makedirs(os.path.dirname(os.path.abspath(self.state_file)), exist_ok=True)
            with open(self.state_file, "w") as f:
                json.dump({
                    "hardware_profile": self.hardware_profile,
                    "domain_confidence": self.domain_confidence,
                    "known_weaknesses": self.known_weaknesses,
                    "skill_history": self.skill_history,
                    "updated_at": time.time()
                }, f, indent=2)
        except Exception as e:
            print(f"⚠️ SelfModel state save error: {e}")

    def assess_capability(self, domain_or_skill: str, environment_context: Optional[Dict[str, Any]] = None) -> CapabilityAssessment:
        """
        Introspectively assesses whether V.O.I.D. can reliably perform a task given environment constraints.
        Example: 'I can perform this task, but my current vision capability is unreliable in low light.'
        """
        key = domain_or_skill.lower().replace(" ", "_")
        ctx = environment_context or {}

        # 1. Base confidence
        conf = self.domain_confidence.get(key, 0.70)
        limitations = []

        # 2. Check environmental weaknesses
        if "vision" in key:
            if ctx.get("lighting") == "low" or ctx.get("is_dark", False):
                conf *= 0.5
                limitations.append("low_light_environment_degrades_detection")

        if "research" in key:
            if ctx.get("is_offline", False):
                conf = 0.0
                limitations.append("network_offline_external_research_unavailable")

        # 3. Hardware check
        telem = self.vram_mgr.get_telemetry()
        vram_status = telem.get("vram_status", "SAFE")
        hw_cost = "LOW"

        if "coding" in key or "inference" in key:
            hw_cost = "MEDIUM"
        if "vision" in key or "research" in key:
            hw_cost = "HIGH"

        if vram_status == VRAMThreshold.CRITICAL:
            limitations.append("gpu_vram_critical_limited_to_cpu")
            conf *= 0.8
            hw_cost = "CRITICAL"

        can_do = conf >= 0.40
        rationale = (
            f"Evaluated domain '{domain_or_skill}' with confidence {conf:.2f}. "
            + (f"Limitations detected: {', '.join(limitations)}." if limitations else "All operational criteria nominal.")
        )

        return CapabilityAssessment(
            can_perform=can_do,
            confidence=round(conf, 4),
            limitations=limitations,
            hardware_cost=hw_cost,
            rationale=rationale
        )

    def record_skill_outcome(self, skill_name: str, success: bool):
        """Updates internal skill history and dynamically adjusts confidence."""
        name = skill_name.lower().strip()
        if name not in self.skill_history:
            self.skill_history[name] = {"success": 0, "fail": 0}

        if success:
            self.skill_history[name]["success"] += 1
            if name in self.domain_confidence:
                self.domain_confidence[name] = min(0.99, self.domain_confidence[name] + 0.005)
        else:
            self.skill_history[name]["fail"] += 1
            if name in self.domain_confidence:
                self.domain_confidence[name] = max(0.20, self.domain_confidence[name] - 0.02)

        self.save_state()

    def get_self_summary(self) -> Dict[str, Any]:
        """Provides a complete introspective telemetry snapshot of V.O.I.D."""
        telem = self.vram_mgr.get_telemetry()
        return {
            "system_name": "V.O.I.D. (Virtual Operator of Information & Development)",
            "hardware": self.hardware_profile,
            "telemetry": telem,
            "domain_confidence": self.domain_confidence,
            "known_weaknesses": self.known_weaknesses,
            "skill_history": self.skill_history
        }


self_model = SelfModel.get_instance()
