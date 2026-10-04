# void_memory/memory_extractor.py
"""
Intelligent Memory Extractor for V.O.I.D.
Analyzes conversations to extract preferences, project facts, technical decisions,
and problem-solution pairs while discarding transient conversational noise.
"""

import re
from typing import List, Dict, Any, Optional

from void_memory.database.models import MemoryTier, MemoryNode
from void_memory.memory_ranker import MemoryRanker


class MemoryExtractor:
    """
    Heuristic, pattern-based, and semantic extractor for high-value memories.
    """

    def __init__(self, ranker: Optional[MemoryRanker] = None):
        self.ranker = ranker or MemoryRanker()

    def is_worth_remembering(self, text: str) -> bool:
        """Determines if a statement contains long-term valuable information."""
        clean = text.strip().lower()
        if len(clean) < 5 or len(clean.split()) < 2:
            return False

        # Exclude casual greetings and acknowledgments
        noise_phrases = [
            "hello", "hey", "hi", "good morning", "good evening", "how are you",
            "what's up", "thank you", "thanks", "ok", "okay", "bye", "see you",
            "cool", "awesome", "great", "yes", "no", "what time is it", "tell me a joke"
        ]
        if clean in noise_phrases or any(clean.startswith(f"{p} ") for p in ["hello", "hi", "hey", "thanks", "ok"]):
            # Unless there's a declarative fact attached
            if not any(k in clean for k in ["my name", "i prefer", "remember", "we use", "our project", "the bug was"]):
                return False

        # Exclude pure questions without declarative content
        if clean.endswith("?") and not any(k in clean for k in ["did you remember", "do you know my"]):
            return False

        return True

    def extract_from_interaction(
        self,
        user_message: str,
        assistant_response: str = "",
        project_id: Optional[str] = None
    ) -> List[MemoryNode]:
        """
        Extracts structured memory candidates from a user-assistant interaction turn.
        """
        extracted_nodes: List[MemoryNode] = []
        user_clean = user_message.strip()
        user_lower = user_clean.lower()

        if not self.is_worth_remembering(user_clean):
            return []

        # 1. Explicit Memory Commands ("Remember that...", "Note that...", "Keep in mind...")
        explicit_match = re.search(
            r'\b(?:remember(?:\s+that)?|note(?:\s+down)?(?:\s+that)?|keep in mind(?:\s+that)?|memorize(?:\s+that)?)\s+(.+)',
            user_clean, re.IGNORECASE
        )
        if explicit_match:
            fact = explicit_match.group(1).strip()
            # Determine category
            category = "explicit_user_fact"
            tier = MemoryTier.SEMANTIC.value
            if any(k in fact.lower() for k in ["prefer", "like", "my name", "call me", "i always"]):
                category = "user_preference"
                tier = MemoryTier.PREFERENCE.value
            elif any(k in fact.lower() for k in ["project", "code", "architecture", "database", "api", "port"]):
                category = "project_technical"
                tier = MemoryTier.PROJECT.value

            node = MemoryNode(
                content=fact,
                memory_type=tier,
                category=category,
                importance=0.95,
                confidence=0.98,
                source="explicit_command",
                pinned=True if "always" in fact.lower() or "preference" in category else False,
                project_id=project_id,
                tags=["explicit", category]
            )
            extracted_nodes.append(node)
            return extracted_nodes

        # 2. User Preferences & Identity
        # e.g., "My name is Venkat", "I prefer concise code", "I like dark mode", "Call me KB"
        name_match = re.search(r'\b(?:my name is|call me|i am|i\'m)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)?)\b', user_clean, re.IGNORECASE)
        if name_match:
            raw_name = name_match.group(1).strip()
            name_val = re.split(r'\b(?:and|who|please|i)\b', raw_name, flags=re.IGNORECASE)[0].strip()
            if name_val and len(name_val) >= 2 and not any(w in name_val.lower() for w in ["trying", "working", "building", "fixing", "happy", "here", "ready", "going"]):
                extracted_nodes.append(MemoryNode(
                    content=f"User's preferred name is {name_val}.",
                    memory_type=MemoryTier.PREFERENCE.value,
                    category="user_preference",
                    importance=0.95,
                    confidence=0.95,
                    source="conversation",
                    pinned=True,
                    tags=["identity", "name", "preference"]
                ))

        pref_match = re.search(r'\b(?:i prefer|i like|i always use|my favorite|i want you to always)\s+(.+)', user_clean, re.IGNORECASE)
        if pref_match:
            pref_val = pref_match.group(1).strip()
            pref_val = re.split(r'\b(?:and then|because|when)\b', pref_val)[0].strip()
            extracted_nodes.append(MemoryNode(
                content=f"User preference: {pref_val}",
                memory_type=MemoryTier.PREFERENCE.value,
                category="user_preference",
                importance=0.85,
                confidence=0.90,
                source="conversation",
                tags=["preference", "user_style"]
            ))

        # 3. Project Technical Facts & Architecture
        # e.g., "The project uses SQLite and PyTorch", "Our backend port is 5000"
        tech_patterns = [
            r'\b(?:we are using|project uses|backend uses|app uses|built with|stack is|database is|framework is)\s+(.+)',
            r'\b(?:the architecture is|we decided to use|we use)\s+(.+)'
        ]
        for pat in tech_patterns:
            m = re.search(pat, user_clean, re.IGNORECASE)
            if m:
                fact_val = m.group(1).strip()
                fact_val = re.split(r'\b(?:because|so that|for now)\b', fact_val)[0].strip()
                if len(fact_val) >= 4:
                    extracted_nodes.append(MemoryNode(
                        content=f"Project specification: {fact_val}",
                        memory_type=MemoryTier.PROJECT.value,
                        category="project_technical",
                        importance=0.85,
                        confidence=0.90,
                        source="conversation",
                        project_id=project_id,
                        tags=["project", "architecture", "tech_stack"]
                    ))

        # 4. Problem & Solution / Bug Fixes
        # e.g., "The bug was caused by missing model weights, fixed by caching offline"
        solution_patterns = [
            r'\b(?:the bug was|the error was|fixed by|the solution is|solved by|resolved by)\s+(.+)',
            r'\b(?:to fix this|the fix is)\s+(.+)'
        ]
        for pat in solution_patterns:
            m = re.search(pat, user_clean, re.IGNORECASE)
            if m:
                sol_val = m.group(1).strip()
                extracted_nodes.append(MemoryNode(
                    content=f"Problem / Solution: {sol_val}",
                    memory_type=MemoryTier.PROCEDURAL.value,
                    category="problem_solution",
                    importance=0.80,
                    confidence=0.85,
                    source="conversation",
                    project_id=project_id,
                    tags=["solution", "bug_fix", "troubleshooting"]
                ))

        # Deduplicate candidates within current turn
        unique_nodes: List[MemoryNode] = []
        seen = set()
        for node in extracted_nodes:
            norm = node.content.lower().strip()
            if norm not in seen:
                seen.add(norm)
                unique_nodes.append(node)

        return unique_nodes
