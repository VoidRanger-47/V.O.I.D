# core/world_model/relations.py
"""
Typed Semantic & Causal Relationships for the V.O.I.D. World Model.
Enables structured reasoning across engineering, scientific, and operational domains.
"""

from enum import Enum


class WorldRelationType(str, Enum):
    # Ontological & Structural
    IS_A = "IS_A"                            # e.g., Python IS_A Interpreted Language
    PART_OF = "PART_OF"                      # e.g., Transformer PART_OF Neural Network Architecture
    HAS_PROPERTY = "HAS_PROPERTY"            # e.g., SQLite HAS_PROPERTY Single-Writer-Lock
    USED_FOR = "USED_FOR"                    # e.g., Faster-Whisper USED_FOR Speech-To-Text

    # Dependencies & Prerequisites
    REQUIRES = "REQUIRES"                    # e.g., PyTorch-CUDA REQUIRES NVIDIA GPU Driver
    DEPENDS_ON = "DEPENDS_ON"                # e.g., Flutter App DEPENDS_ON Dart SDK

    # Causal & State Dynamics
    CAUSES = "CAUSES"                        # e.g., Unclosed DB Cursor CAUSES Memory Leak
    PREVENTS = "PREVENTS"                    # e.g., WAL Mode PREVENTS Concurrent Read Starvation

    # Compatibility & Conflict
    COMPATIBLE_WITH = "COMPATIBLE_WITH"      # e.g., Python 3.11 COMPATIBLE_WITH PyTorch 2.4
    INCOMPATIBLE_WITH = "INCOMPATIBLE_WITH"  # e.g., 32-bit OS INCOMPATIBLE_WITH 64-bit CUDA Toolkit
    CONTRADICTS = "CONTRADICTS"              # e.g., Claim B CONTRADICTS Claim A
    SUPERSEDES = "SUPERSEDES"                # e.g., Model V2 SUPERSEDES Model V1
