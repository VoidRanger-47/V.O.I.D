# core/verification/__init__.py
from core.verification.empirical_engine import (
    VerificationProof,
    EmpiricalVerificationEngine,
    empirical_engine
)
from core.verification.contradiction_resolver import (
    ConflictDecision,
    CognitiveConflict,
    ContradictionResolver,
    contradiction_resolver
)

__all__ = [
    "VerificationProof",
    "EmpiricalVerificationEngine",
    "empirical_engine",
    "ConflictDecision",
    "CognitiveConflict",
    "ContradictionResolver",
    "contradiction_resolver"
]
