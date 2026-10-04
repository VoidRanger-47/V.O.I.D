# void_memory/knowledge_graph.py
"""
Lightweight Local Semantic Knowledge Graph for V.O.I.D.
Models concepts, technologies, projects, problems, and solutions as nodes and typed relationships.
Enriches memory retrieval through bounded graph neighborhood expansion.
"""

import re
import time
from typing import List, Dict, Any, Optional, Set, Tuple

from void_memory.database.models import KnowledgeNode, MemoryRelationship, RelationshipType
from void_memory.database.repository import MemoryRepository


class KnowledgeGraph:
    """
    Local graph engine backed by SQLite tables `memory_knowledge_nodes` and `memory_relationships`.
    """

    def __init__(self, repo: MemoryRepository):
        self.repo = repo

    def add_concept(
        self,
        name: str,
        node_type: str = "concept",
        description: str = "",
        properties: Optional[Dict[str, Any]] = None
    ) -> KnowledgeNode:
        clean_name = name.strip()
        node = KnowledgeNode(
            node_type=node_type,
            name=clean_name,
            description=description,
            properties=properties or {},
            created_at=time.time()
        )
        return self.repo.save_knowledge_node(node)

    def link_entities(
        self,
        source_id_or_name: str,
        target_id_or_name: str,
        relationship: str = RelationshipType.RELATED_TO.value,
        weight: float = 1.0
    ) -> bool:
        rel = MemoryRelationship(
            source_id=source_id_or_name,
            target_id=target_id_or_name,
            relationship=relationship,
            weight=weight,
            created_at=time.time()
        )
        return self.repo.add_relationship(rel)

    def extract_and_link_entities(self, memory_id: str, content: str):
        """
        Extracts known entities (technologies, tools, languages) and links them to the memory node.
        """
        known_techs = [
            "Python", "PyTorch", "SQLite", "Flask", "FastAPI", "Electron", "JavaScript",
            "TypeScript", "HTML", "CSS", "Tailwind", "Whisper", "Piper", "ChromaDB",
            "FAISS", "ADB", "Android", "Windows", "Linux", "macOS", "Docker", "VS Code"
        ]
        for tech in known_techs:
            if re.search(rf'\b{re.escape(tech)}\b', content, re.IGNORECASE):
                # Ensure knowledge node exists
                self.add_concept(name=tech, node_type="technology", description=f"Core technology: {tech}")
                # Link memory node to technology
                self.link_entities(memory_id, tech, relationship=RelationshipType.USES.value)

    def get_neighborhood(self, node_id: str, max_depth: int = 1) -> List[Dict[str, Any]]:
        """
        Retrieves 1-hop or 2-hop neighbors connected to a memory or entity node.
        """
        visited_nodes: Set[str] = {node_id}
        frontier = [node_id]
        edges: List[Dict[str, Any]] = []

        for depth in range(max_depth):
            next_frontier = []
            for curr in frontier:
                related = self.repo.get_related_memories(curr)
                for node, rel, weight in related:
                    edge = {
                        "source": curr,
                        "target": node.id,
                        "target_content": node.content,
                        "target_type": node.memory_type,
                        "relationship": rel,
                        "weight": weight,
                        "depth": depth + 1
                    }
                    edges.append(edge)
                    if node.id not in visited_nodes:
                        visited_nodes.add(node.id)
                        next_frontier.append(node.id)
            frontier = next_frontier
            if not frontier:
                break

        return edges

    def get_graph_export(self) -> Dict[str, Any]:
        """Exports the entire graph topology for UI visualization."""
        knodes = self.repo.list_knowledge_nodes()
        memories = self.repo.list_memories(limit=200)

        nodes = []
        for kn in knodes:
            nodes.append({
                "id": kn.name,
                "label": kn.name,
                "type": kn.node_type,
                "category": "concept"
            })

        for m in memories:
            preview = m.content[:40] + ("..." if len(m.content) > 40 else "")
            nodes.append({
                "id": m.id,
                "label": preview,
                "type": m.memory_type,
                "category": "memory",
                "importance": m.importance
            })

        # Edges
        conn = self.repo._get_connection()
        c = conn.cursor()
        c.execute('SELECT source_id, target_id, relationship, weight FROM memory_relationships')
        edges = []
        for r in c.fetchall():
            edges.append({
                "source": r["source_id"],
                "target": r["target_id"],
                "relationship": r["relationship"],
                "weight": float(r["weight"])
            })
        conn.close()

        return {
            "nodes": nodes,
            "edges": edges,
            "node_count": len(nodes),
            "edge_count": len(edges)
        }
