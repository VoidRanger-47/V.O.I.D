# skills/library/skill_registry.py
"""
Central Skill Registry and Dynamic Composition Engine for V.O.I.D.
Coordinates registration, discovery, and pipeline composition of skills.
"""

from typing import Dict, Any, List, Optional
from skills.library.base_skill import BaseSkill, SkillManifest, CompositeSkill
from core.security import security_manager


class CodingDebugSkill(BaseSkill):
    def __init__(self):
        super().__init__(SkillManifest(
            name="coding_debug",
            domain="programming",
            purpose="Execute code in AST sandbox, verify syntax, and catch runtime exceptions",
            inputs={"code": "Python code string to execute and verify"},
            outputs={"output": "Evaluation result or traceback"},
            tools=["ast_sandbox", "python_interpreter"],
            procedure=["1. Verify AST security", "2. Execute in sandbox", "3. Capture stdout/stderr"],
            verification="execution_no_syntax_error",
            failure_modes=["syntax_error", "timeout", "permission_denied"],
            recovery_strategy="Attempt AST automated repair or return error diagnosis"
        ))

    def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        code = inputs.get("code", "")
        if not code.strip():
            return {"success": False, "error": "Empty code body provided"}
        res = security_manager.execute_sandboxed_python(code)
        is_ok = (res.get("status") == "SUCCESS")
        return {
            "success": is_ok,
            "output": res.get("output", ""),
            "error": None if is_ok else res.get("output", "Execution error")
        }


class MathAnalysisSkill(BaseSkill):
    def __init__(self):
        super().__init__(SkillManifest(
            name="mathematics_solver",
            domain="mathematics",
            purpose="Compute mathematical expressions, linear algebra, calculus, and equation solutions",
            inputs={"expression": "Mathematical formula or problem statement"},
            outputs={"result": "Computed mathematical solution"},
            tools=["math_solver"],
            procedure=["1. Parse expression", "2. Evaluate symbolically or numerically", "3. Format output"],
            verification="numerical_or_symbolic_validity",
            failure_modes=["division_by_zero", "unsupported_operator", "parse_failure"],
            recovery_strategy="Fallback to safe math evaluator"
        ))

    def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        expr = inputs.get("expression", inputs.get("code", ""))
        from skills.math import handle_math
        ans = handle_math(expr)
        return {
            "success": True,
            "result": str(ans),
            "output": str(ans)
        }


class SystemDiagnosticSkill(BaseSkill):
    def __init__(self):
        super().__init__(SkillManifest(
            name="system_diagnostic",
            domain="system",
            purpose="Collect real-time CPU, RAM, VRAM, and storage hardware metrics",
            inputs={},
            outputs={"metrics": "Hardware telemetry summary"},
            tools=["vram_manager", "psutil"],
            procedure=["1. Query psutil for CPU/RAM", "2. Query GPU VRAM", "3. Format telemetry report"],
            verification="metrics_present",
            recovery_strategy="Return partial host metrics"
        ))

    def execute(self, inputs: Dict[str, Any], context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        from core.vram_manager import vram_manager
        telem = vram_manager.get_telemetry()
        return {
            "success": True,
            "metrics": telem,
            "output": f"CPU: {telem.get('cpu_percent', 0)}% | RAM: {telem.get('ram_used_mb', 0)}MB | VRAM: {telem.get('used_vram_mb', 0)}MB"
        }


class SkillRegistry:
    """
    Registry for managing and dynamically composing V.O.I.D. skills.
    """
    _instance: Optional['SkillRegistry'] = None

    def __init__(self):
        self.skills: Dict[str, BaseSkill] = {}
        self._register_default_skills()

    @classmethod
    def get_instance(cls) -> 'SkillRegistry':
        if cls._instance is None:
            cls._instance = SkillRegistry()
        return cls._instance

    def _register_default_skills(self):
        self.register(CodingDebugSkill())
        self.register(MathAnalysisSkill())
        self.register(SystemDiagnosticSkill())

    def register(self, skill: BaseSkill):
        self.skills[skill.manifest.name] = skill

    def get_skill(self, name: str) -> Optional[BaseSkill]:
        if name not in self.skills and name == "cad_manipulator":
            try:
                from skills.cad_engine import CADManipulationSkill
                self.register(CADManipulationSkill())
            except Exception:
                pass
        return self.skills.get(name)

    def list_skills(self) -> List[Dict[str, Any]]:
        return [s.manifest.to_dict() for s in self.skills.values()]

    def compose(self, skill_names: List[str], composite_name: str, purpose: str) -> CompositeSkill:
        """
        Dynamically chains multiple skills into a unified CompositeSkill.
        """
        selected_skills = []
        for name in skill_names:
            sk = self.get_skill(name)
            if not sk:
                raise ValueError(f"Cannot compose: skill '{name}' is not registered.")
            selected_skills.append(sk)

        comp = CompositeSkill(name=composite_name, purpose=purpose, skills=selected_skills)
        self.register(comp)
        return comp


skill_registry = SkillRegistry.get_instance()
