# tests/test_agi_cognitive_architecture.py
"""
Comprehensive 10-Phase AGI Cognitive Architecture Test Suite for V.O.I.D.
Verifies all 10 cognitive phases:
  Phase 1: Meta-Cognitive Supervisor & Structured State
  Phase 2: Persistent World Model, Self Model, and Experience Memory
  Phase 3: Hierarchical 4-Level Planning & Closed-Loop Execution
  Phase 4: Composable Skill Library & Pipeline Execution
  Phase 5: Empirical Sandbox Verification & Cognitive Contradiction Resolution
  Phase 6: Cross-Domain Knowledge Transfer Engine
  Phase 7: Autonomous Curiosity & Vetted Research Engine
  Phase 8: Sleep-Cycle Consolidation & General Procedural Induction
  Phase 9: Continual Learning & Non-Parametric Adaptation Guards
  Phase 10: Proactive Environmental Assistance & Safety Protocols
"""

import unittest
import sys
import os
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Phase 1 imports
from core.meta_cognition.state import (
    CognitiveState,
    TaskComplexity,
    CognitivePhase,
    VerificationVerdict
)
from core.meta_cognition.supervisor import MetaCognitiveSupervisor

# Phase 2 imports
from core.world_model.relations import WorldRelationType
from core.world_model.model import WorldModel
from core.self_model.model import SelfModel
from void_memory.experience_memory import ExperienceMemory

# Phase 3 imports
from core.planning.hierarchical_planner import (
    HierarchicalPlan,
    HierarchicalPlanner,
    PlanLevel,
    NodeStatus,
    ActionNode
)
from core.execution.closed_loop import ClosedLoopExecutor

# Phase 4 imports
from skills.library.base_skill import SkillManifest, BaseSkill
from skills.library.skill_registry import SkillRegistry, CodingDebugSkill, MathAnalysisSkill

# Phase 5 imports
from core.verification.empirical_engine import EmpiricalVerificationEngine
from core.verification.contradiction_resolver import ContradictionResolver, ConflictDecision

# Phase 6 imports
from core.cross_domain.transfer_engine import CrossDomainTransferEngine, DomainBridge

# Phase 7 imports
from core.curiosity.curiosity_engine import CuriosityEngine, GapStatus

# Phase 8 imports
from core.sleep.consolidation_daemon import SleepConsolidationDaemon

# Phase 9 imports
from core.adaptation.adaptation_guard import AdaptationGuard

# Phase 10 imports
from core.proactive.assistant import ProactiveAssistant

# End-to-end Agent
from core.agent import VoidAgent


class TestPhase1MetaCognition(unittest.TestCase):
    def setUp(self):
        self.supervisor = MetaCognitiveSupervisor()

    def test_goal_assessment_and_state(self):
        state = self.supervisor.initialize_state("hello void")
        self.assertEqual(state.complexity, TaskComplexity.TRIVIAL)
        self.assertFalse(self.supervisor.decide_memory_retrieval(state))

        code_state = self.supervisor.initialize_state("debug python function in memory")
        self.assertEqual(code_state.complexity, TaskComplexity.HIGH)
        self.assertTrue(self.supervisor.decide_memory_retrieval(code_state))

    def test_replanning_state_transition(self):
        state = self.supervisor.initialize_state("Execute script")
        state.transition_to(CognitivePhase.EXECUTING)
        verdict = self.supervisor.evaluate_intermediate_result(
            state, step_id=1, agent_name="coding_agent", output="❌ Syntax Error", status="FAILED"
        )
        self.assertEqual(verdict, VerificationVerdict.REPLAN_REQUIRED)
        self.assertEqual(state.current_state, CognitivePhase.REPLANNING)


class TestPhase2WorldSelfExperience(unittest.TestCase):
    def test_world_model_causal_path(self):
        test_db = "void_memory/test_wm.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        wm = WorldModel(db_path=test_db)
        wm.add_entity("ModuleA", domain="core")
        wm.add_entity("ModuleB", domain="core")
        wm.link_entities("ModuleA", "ModuleB", WorldRelationType.CAUSES)
        path = wm.find_causal_chain("ModuleA", "ModuleB")
        self.assertEqual(path, ["ModuleA", "ModuleB"])

    def test_self_model_introspective_assessment(self):
        sm = SelfModel.get_instance()
        normal = sm.assess_capability("python_development")
        self.assertTrue(normal.can_perform)
        self.assertGreater(normal.confidence, 0.80)

        degraded = sm.assess_capability("computer_vision", environment_context={"lighting": "low"})
        self.assertIn("low_light_environment_degrades_detection", degraded.limitations)

    def test_experience_memory_rule_derivation(self):
        test_db = "void_memory/test_em.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        em = ExperienceMemory(db_path=test_db)
        rec = em.record_experience(
            situation="Building package XYZ on Windows",
            action="pip install XYZ",
            expected_result="Wheel built",
            actual_result="Error: clang required",
            success=False,
            failure_cause="Clang compiler missing",
            better_strategy="Install LLVM toolchain before build",
            domain="python"
        )
        self.assertIn("LLVM", rec.learned_rule)
        rules = em.get_procedural_rules_for_situation("Building package XYZ on Windows")
        self.assertGreater(len(rules), 0)


class TestPhase3HierarchicalPlanningAndClosedLoop(unittest.TestCase):
    def setUp(self):
        self.planner = HierarchicalPlanner.get_instance()
        self.executor = ClosedLoopExecutor.get_instance()

    def test_hierarchical_4_level_decomposition(self):
        plan = self.planner.decompose("Build and test offline vision scanner")
        self.assertEqual(plan.objective, "Build and test offline vision scanner")
        self.assertGreaterEqual(len(plan.milestones), 2)
        total_actions = plan.total_actions_count()
        self.assertGreaterEqual(total_actions, 3)

    def test_closed_loop_replanning_on_failure(self):
        plan = self.planner.decompose("Calculate integral of x^2")
        failed_action = plan.milestones[0].tasks[0].actions[0]
        replan_ok = self.planner.replan_on_failure(plan, failed_action.id, "Calculation timeout")
        self.assertTrue(replan_ok)
        self.assertEqual(failed_action.status, NodeStatus.FAILED)


class TestPhase4SkillLibrary(unittest.TestCase):
    def setUp(self):
        self.registry = SkillRegistry.get_instance()

    def test_standalone_skill_execution(self):
        math_skill = self.registry.get_skill("mathematics_solver")
        self.assertIsNotNone(math_skill)
        res = math_skill.execute({"expression": "100 + 45 * 2"})
        self.assertTrue(res["success"])
        self.assertIn("190", res["result"])

    def test_dynamic_skill_composition(self):
        # Compose Math + System Diagnostic into a single pipeline
        composite = self.registry.compose(
            skill_names=["mathematics_solver", "system_diagnostic"],
            composite_name="math_and_system_health",
            purpose="Compute mathematical equation and verify hardware telemetry"
        )
        res = composite.execute({"expression": "50 * 2"})
        self.assertTrue(res["success"])
        self.assertIn("metrics", res["result"])


class TestPhase5EmpiricalVerificationAndContradiction(unittest.TestCase):
    def setUp(self):
        self.verifier = EmpiricalVerificationEngine.get_instance()
        test_db = "void_memory/test_conflicts.db"
        if os.path.exists(test_db):
            os.remove(test_db)
        self.resolver = ContradictionResolver(db_path=test_db)

    def test_empirical_sandbox_code_verification(self):
        # Valid code
        valid_proof = self.verifier.verify_code(
            code_str="def add(a, b): return a + b\nres = add(10, 20)",
            test_assertions="assert res == 30"
        )
        self.assertEqual(valid_proof.status, "PASS")
        self.assertGreater(valid_proof.confidence, 0.90)

        # Syntax error code
        invalid_proof = self.verifier.verify_code(code_str="def broken(: return")
        self.assertEqual(invalid_proof.status, "FAIL")

    def test_cognitive_conflict_arbitration(self):
        # Version variance -> Contextual coexistence
        conflict = self.resolver.arbitrate(
            old_claim="In Python 2 print is a statement",
            new_claim="In Python 3 print is a function",
            domain="python",
            old_confidence=0.80,
            new_confidence=0.95
        )
        self.assertEqual(conflict.decision, ConflictDecision.CONTEXTUAL_COEXISTENCE)


class TestPhase6CrossDomainTransfer(unittest.TestCase):
    def setUp(self):
        self.cd = CrossDomainTransferEngine.get_instance()

    def test_analogical_transfer_lookup(self):
        mapping = self.cd.transfer_concept("Vector_Mathematics", target_domain="vision")
        self.assertIsNotNone(mapping)
        self.assertIn("3D_Spatial_Coordinates", mapping["mapped_to"])
        self.assertGreater(mapping["confidence"], 0.80)


class TestPhase7AutonomousCuriosity(unittest.TestCase):
    def setUp(self):
        self.curiosity = CuriosityEngine.get_instance()

    def test_gap_registration_and_vetted_filtering(self):
        gap = self.curiosity.register_knowledge_gap("Quantum Computing Qiskit SDK", domain="physics", priority=0.85)
        self.assertEqual(gap.topic, "Quantum Computing Qiskit SDK")

        # Source filtering
        candidates = [
            "https://clickbait-slop-ai.com/quantum",
            "https://docs.python.org/3/library/math.html",
            "https://github.com/qiskit/qiskit"
        ]
        vetted = self.curiosity.filter_vetted_sources(candidates)
        self.assertIn("https://docs.python.org/3/library/math.html", vetted)
        self.assertIn("https://github.com/qiskit/qiskit", vetted)
        self.assertNotIn("https://clickbait-slop-ai.com/quantum", vetted)


class TestPhase8SleepConsolidation(unittest.TestCase):
    def setUp(self):
        self.daemon = SleepConsolidationDaemon.get_instance()

    def test_sleep_consolidation_rule_induction(self):
        # Populate two similar failures
        experience_memory = self.daemon.exp_mem
        experience_memory.record_experience(
            situation="File open path test 1",
            action="open_file",
            expected_result="File opened",
            actual_result="Error: bad path slash",
            success=False,
            failure_cause="Unnormalized Windows Path",
            better_strategy="Normalize path with os.path.normpath",
            domain="system"
        )
        experience_memory.record_experience(
            situation="File open path test 2",
            action="open_file",
            expected_result="File opened",
            actual_result="Error: bad path slash",
            success=False,
            failure_cause="Unnormalized Windows Path",
            better_strategy="Normalize path with os.path.normpath",
            domain="system"
        )

        res = self.daemon.consolidate(force=True)
        self.assertEqual(res["status"], "COMPLETED")
        self.assertGreaterEqual(res["rules_synthesized"], 1)


class TestPhase9AdaptationGuards(unittest.TestCase):
    def setUp(self):
        self.guard = AdaptationGuard.get_instance()

    def test_non_parametric_first_policy(self):
        # Low access count -> Must be rejected for weight distillation
        ok, reason = self.guard.consider_for_distillation(
            concept_or_rule="Temporary scratch rule",
            domain="general",
            access_count=2,
            confidence=0.99
        )
        self.assertFalse(ok)
        self.assertIn("Non-Parametric First", reason)

        # High stability and frequency -> Approved
        ok_stable, reason_stable = self.guard.consider_for_distillation(
            concept_or_rule="Frequent immutable math theorem",
            domain="math",
            access_count=15,
            confidence=0.98
        )
        self.assertTrue(ok_stable)
        self.assertIn("APPROVED", reason_stable)


class TestPhase10ProactiveAssistance(unittest.TestCase):
    def setUp(self):
        self.proactive = ProactiveAssistant.get_instance()

    def test_sensitive_action_safety_staging(self):
        proposal = self.proactive.stage_sensitive_action(
            title="Clean Windows Temp Folder",
            description="Remove stale cache files from C:\\Temp",
            dry_run_command="del /q /f C:\\Temp\\*.tmp"
        )
        self.assertTrue(proposal.is_sensitive)
        self.assertTrue(proposal.requires_approval)
        self.assertEqual(proposal.status, "PENDING")

        # Approve and execute
        exec_res = self.proactive.approve_and_execute(proposal.id)
        self.assertEqual(exec_res["status"], "SUCCESS")
        self.assertEqual(proposal.status, "EXECUTED")


class TestEndToEndCognitiveIntegration(unittest.TestCase):
    def test_void_agent_10_phase_cognitive_execution(self):
        agent = VoidAgent.get_instance()
        res = agent.run_task("calculate 80 * 2 + 40")

        self.assertEqual(res.status, "SUCCESS")
        self.assertIsNotNone(res.cognitive_state)
        self.assertIn("task_id", res.cognitive_state)
        self.assertIn("confidence", res.cognitive_state)
        self.assertIn("200", res.response)


if __name__ == "__main__":
    unittest.main()
