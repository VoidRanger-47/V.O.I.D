# void_learning/__init__.py
"""
V.O.I.D. Internet Knowledge Acquisition & Continuous Learning System.
Acquires, cleans, verifies, structures, and remembers knowledge locally with source traceability.
"""

from void_learning.source_quality import SourceTier, evaluate_source_quality
from void_learning.content_cleaner import clean_web_content, fetch_and_clean_page
from void_learning.fact_extractor import FactExtractor, KnowledgeFact, KnowledgeTriple
from void_learning.conflict_detector import ConflictDetector, ConflictReport
from void_learning.research_agent import WebResearchAgent
from void_learning.knowledge_engine import KnowledgeEngine, knowledge_engine

__all__ = [
    "SourceTier",
    "evaluate_source_quality",
    "clean_web_content",
    "fetch_and_clean_page",
    "FactExtractor",
    "KnowledgeFact",
    "KnowledgeTriple",
    "ConflictDetector",
    "ConflictReport",
    "WebResearchAgent",
    "KnowledgeEngine",
    "knowledge_engine",
]
