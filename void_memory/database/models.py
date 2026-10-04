# void_memory/database/models.py
"""
Data models and enumerations for the V.O.I.D. Advanced Memory Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time
import uuid


class MemoryTier(str, Enum):
    WORKING = "working"          # Task scratchpad / active context
    EPISODIC = "episodic"        # Timeline of interactions and events
    SEMANTIC = "semantic"        # Persistent factual knowledge
    PREFERENCE = "preference"    # User preferences, style, identity
    PROJECT = "project"          # Project architecture, files, decisions
    PROCEDURAL = "procedural"    # Learned workflows, recipes, commands
    VISUAL = "visual"            # Camera observations, scene embeddings, detected people
    MISSION = "mission"          # Multi-step missions, milestones, goals


class MemoryStatus(str, Enum):
    ACTIVE = "active"
    LOW_PRIORITY = "low_priority"
    ARCHIVED = "archived"
    DELETED = "deleted"
    SUPERSEDED = "superseded"


class RelationshipType(str, Enum):
    USES = "uses"
    DEPENDS_ON = "depends_on"
    RELATED_TO = "related_to"
    CREATED = "created"
    SOLVED = "solved"
    UPDATED = "updated"
    SUPERSEDES = "supersedes"
    CONTRADICTS = "contradicts"
    SUPPORTS = "supports"
    BELONGS_TO = "belongs_to"


@dataclass
class MemoryNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: str = ""
    memory_type: str = MemoryTier.SEMANTIC.value
    category: str = "general"
    importance: float = 0.5
    confidence: float = 0.9
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 1
    source: str = "conversation"
    status: str = MemoryStatus.ACTIVE.value
    pinned: bool = False
    tags: List[str] = field(default_factory=list)
    project_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[bytes] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "category": self.category,
            "importance": round(self.importance, 4),
            "confidence": round(self.confidence, 4),
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "source": self.source,
            "status": self.status,
            "pinned": self.pinned,
            "tags": self.tags,
            "project_id": self.project_id,
            "metadata": self.metadata
        }


@dataclass
class MemoryRelationship:
    id: Optional[int] = None
    source_id: str = ""
    target_id: str = ""
    relationship: str = RelationshipType.RELATED_TO.value
    weight: float = 1.0
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relationship": self.relationship,
            "weight": self.weight,
            "created_at": self.created_at
        }


@dataclass
class KnowledgeNode:
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    node_type: str = "concept"   # concept, technology, project, file, person, tool, problem, solution
    name: str = ""
    description: str = ""
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "node_type": self.node_type,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "created_at": self.created_at
        }


@dataclass
class ProjectMemoryRecord:
    project_id: str = "default"
    name: str = "V.O.I.D."
    path: str = ""
    architecture: str = ""
    technologies: List[str] = field(default_factory=list)
    decisions: List[Dict[str, Any]] = field(default_factory=list)
    problems_and_solutions: List[Dict[str, Any]] = field(default_factory=list)
    todos: List[Dict[str, Any]] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "name": self.name,
            "path": self.path,
            "architecture": self.architecture,
            "technologies": self.technologies,
            "decisions": self.decisions,
            "problems_and_solutions": self.problems_and_solutions,
            "todos": self.todos,
            "updated_at": self.updated_at
        }
