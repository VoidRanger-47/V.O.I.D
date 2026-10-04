# core/verification/empirical_engine.py
"""
Empirical Verification Engine for V.O.I.D.
Provides objective, sandbox-backed truth verification for code and technical claims:
  Source -> Extract Claim -> Attempt Empirical Test -> Compare Expected vs Actual -> Assign Confidence -> Store Provenance
Maintains complete audit trails.
"""

import hashlib
import time
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field, asdict

from core.security import security_manager
from core.audit_logger import audit_logger


@dataclass
class VerificationProof:
    proof_id: str
    target_type: str  # "code", "claim", "file", "computation"
    target_snippet: str
    status: str       # "PASS", "FAIL"
    confidence: float
    expected: str
    actual: str
    provenance_hash: str
    audit_trail: List[str] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class EmpiricalVerificationEngine:
    """
    Audits technical claims and generated code against empirical sandbox tests.
    """
    _instance: Optional['EmpiricalVerificationEngine'] = None

    def __init__(self):
        self.security = security_manager

    @classmethod
    def get_instance(cls) -> 'EmpiricalVerificationEngine':
        if cls._instance is None:
            cls._instance = EmpiricalVerificationEngine()
        return cls._instance

    @staticmethod
    def compute_provenance_hash(data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()[:16]

    def verify_code(
        self,
        code_str: str,
        test_assertions: Optional[str] = None
    ) -> VerificationProof:
        """
        Executes code inside the AST-verified sandbox, evaluates assertions, and logs audit proof.
        """
        start_t = time.time()
        audit = [f"Initiated sandbox verification at {start_t}"]

        # 1. AST Static Inspection
        is_safe, reason = self.security.scan_python_ast(code_str)
        if not is_safe:
            reject_reason = reason or "AST security violation"
            audit.append(f"AST verification rejected code: {reject_reason}")
            proof = VerificationProof(
                proof_id=f"proof_{str(int(time.time()*1000))[-6:]}",
                target_type="code",
                target_snippet=code_str[:80],
                status="FAIL",
                confidence=0.0,
                expected="AST-compliant safe code",
                actual=f"Rejected: {reject_reason}",
                provenance_hash=self.compute_provenance_hash(code_str),
                audit_trail=audit
            )
            audit_logger.log(event="EMPIRICAL_VERIFY_FAIL", tool="empirical_engine", status="FAIL", error=reject_reason)
            return proof

        audit.append("AST security inspection passed.")

        # 2. Combine with test assertions if provided
        full_exec_code = code_str
        if test_assertions:
            full_exec_code += f"\n\n# --- VERIFICATION TEST SUITE ---\n{test_assertions}"
            audit.append("Appended verification assertions into execution payload.")

        # 3. Sandbox Run
        res = self.security.execute_sandboxed_python(full_exec_code)
        actual_output = res.get("output", "")
        success = bool(res.get("success") or res.get("status") == "SUCCESS")

        status_str = "PASS" if success else "FAIL"
        confidence = 0.98 if success else 0.15
        if success:
            audit.append("Sandbox execution completed without exception.")
        else:
            audit.append(f"Execution raised error: {actual_output[:100]}")

        proof = VerificationProof(
            proof_id=f"proof_{str(int(time.time()*1000))[-6:]}",
            target_type="code",
            target_snippet=code_str[:80],
            status=status_str,
            confidence=confidence,
            expected="Exit code 0 and valid assertion passes",
            actual=actual_output[:200],
            provenance_hash=self.compute_provenance_hash(full_exec_code),
            audit_trail=audit
        )

        audit_logger.log(
            event=f"EMPIRICAL_VERIFY_{status_str}",
            tool="empirical_engine",
            status=status_str,
            duration=round(time.time() - start_t, 4),
            result_summary=actual_output[:120]
        )
        return proof

    def verify_empirical_claim(
        self,
        claim_description: str,
        empirical_test: Callable[[], bool],
        expected_outcome: str = "True"
    ) -> VerificationProof:
        """
        Executes a callable empirical test function to verify an empirical fact.
        """
        audit = [f"Auditing empirical claim: {claim_description[:60]}"]
        try:
            test_passed = bool(empirical_test())
            status = "PASS" if test_passed else "FAIL"
            conf = 0.95 if test_passed else 0.20
            actual = str(test_passed)
            audit.append(f"Empirical test evaluated to: {test_passed}")
        except Exception as e:
            status = "FAIL"
            conf = 0.05
            actual = f"Exception: {str(e)}"
            audit.append(f"Empirical test execution crashed: {e}")

        return VerificationProof(
            proof_id=f"proof_{str(int(time.time()*1000))[-6:]}",
            target_type="claim",
            target_snippet=claim_description[:80],
            status=status,
            confidence=conf,
            expected=expected_outcome,
            actual=actual,
            provenance_hash=self.compute_provenance_hash(claim_description),
            audit_trail=audit
        )


empirical_engine = EmpiricalVerificationEngine.get_instance()
