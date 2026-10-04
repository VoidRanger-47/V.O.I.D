# skills/library/base_skill.py
"""
Base Skill Specification for V.O.I.D.
Defines structured, verifiable, and composable skills.
"""

import time
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class SkillManifest:
    name: str
    domain: str
    purpose: str
    inputs: Dict[str, str] = field(default_factory=dict)
    outputs: Dict[str, str] = field(default_factory=dict)
    prerequisites: List[str] = field(default_factory=list)
    tools: List[str] = field(default_factory=list)
    procedure: List[str] = field(default_factory=list)
    verification: str = "output_non_empty"
    failure_modes: List[str] = field(default_factory=list)
    recovery_strategy: str = "fallback_to_safe_mode"
    success_count: int = 0
    fail_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class BaseSkill(ABC):
    """
    Abstract base class for all V.O.I.D. skills.
    Provides deterministic inputs/outputs, self-verification, and failure recovery.
    """
    def __init__(self, manifest: SkillManifest):
        self.manifest = manifest

    @abstractmethod
    def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Executes the skill procedure and returns structured output."""
        pass

    def verify(self, output: Dict[str, Any]) -> bool:
        """Audits skill output against manifest criteria."""
        if not output:
            return False
        if "error" in output and output["error"]:
            return False
        return True

    def record_outcome(self, success: bool):
        if success:
            self.manifest.success_count += 1
        else:
            self.manifest.fail_count += 1


class CompositeSkill(BaseSkill):
    """
    A skill composed dynamically from an ordered chain of sub-skills.
    Example: Vision (Capture) + Object Detection (Identify) + Memory (Lookup) + Speech (Vocalize).
    """
    def __init__(self, name: str, purpose: str, skills: List[BaseSkill]):
        manifest = SkillManifest(
            name=name,
            domain="composite",
            purpose=purpose,
            prerequisites=[s.manifest.name for s in skills],
            tools=[t for s in skills for t in s.manifest.tools],
            procedure=[f"Step {i+1}: Execute {s.manifest.name}" for i, s in enumerate(skills)],
            verification="all_subskills_pass",
            recovery_strategy="abort_on_subskill_failure"
        )
        super().__init__(manifest)
        self.skills = skills

    def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        current_data = dict(inputs)
        pipeline_results = []

        for skill in self.skills:
            res = skill.execute(current_data, context=context)
            if not skill.verify(res):
                skill.record_outcome(False)
                self.record_outcome(False)
                return {
                    "success": False,
                    "error": f"Composite skill failed at sub-skill '{skill.manifest.name}'",
                    "failed_subskill": skill.manifest.name,
                    "pipeline": pipeline_results
                }
            skill.record_outcome(True)
            pipeline_results.append({skill.manifest.name: res})
            # Merge outputs for next skill in pipeline
            current_data.update(res)

        self.record_outcome(True)
        return {
            "success": True,
            "result": current_data,
            "pipeline": pipeline_results
        }
