from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Tuple

from skills.coding import is_coding_request
from skills.web_search import extract_search_query, is_search_request, perform_search
from void_learning.knowledge_engine import knowledge_engine


def build_agent_plan(user_input: str, force_search: bool = False, thinking_mode: bool = False) -> Dict[str, object]:
    """Create a lightweight agent plan with tool selection and intent flags."""
    text = (user_input or "").strip()
    lower = text.lower()

    # Intent detection for Learning Commands (Requirement 8, 11, 19)
    is_source_trace_command = any(p in lower for p in [
        "where did you learn this", "where did you get this", "where did you learn", "show sources for", "what are your sources", "show sources"
    ])
    is_forget_command = any(p in lower for p in [
        "forget what you learned about", "forget about", "forget knowledge"
    ])
    is_learn_command = (
        not is_source_trace_command 
        and not is_forget_command 
        and any(lower.startswith(p) or f" {p}" in lower for p in [
            "learn about", "void, learn", "void learn", "study ", "research modern", "research latest", "research "
        ]) 
        and not any(k in lower for k in ["how to learn", "i want to learn"])
    )

    needs_search = bool(force_search or is_search_request(text))
    needs_coding = bool(is_coding_request(text))
    needs_thinking = bool(thinking_mode or any(term in lower for term in ["think", "reason", "why", "how does", "explain step", "deeply", "step-by-step", "solve"]))
    needs_memory = any(term in lower for term in ["remember", "preference", "my name", "i live", "i work", "my project", "my goal", "my setup", "my notes"])
    needs_generation = needs_coding or any(term in lower for term in ["write", "create", "generate", "explain", "help me", "draft", "design"])
    
    # Knowledge retrieval should ONLY trigger for informational requests, NOT greetings or general chat
    is_greeting = lower in {"hi", "hello", "hey", "hola", "sup", "greetings", "good morning", "good evening", "good afternoon"} or lower.startswith(("hi ", "hello ", "hey "))
    knowledge_keywords = ["doc", "document", "manual", "guide", "spec", "knowledge", "file", "upload", "how do i", "read", "project", "source", "what is", "tell me about"]
    needs_knowledge_retrieval = (
        bool(text) 
        and not is_greeting 
        and not needs_search 
        and not needs_coding
        and any(k in lower for k in knowledge_keywords)
    )

    tool_names: List[str] = []
    if is_learn_command:
        tool_names.append("knowledge_learning")
    elif is_source_trace_command:
        tool_names.append("source_traceability")
    elif is_forget_command:
        tool_names.append("knowledge_forget")
    if needs_search and not is_learn_command:
        tool_names.append("web_search")
    if needs_coding:
        tool_names.append("coding")
    if needs_thinking:
        tool_names.append("reasoning_engine")
    if needs_memory and not is_greeting:
        tool_names.append("memory_rag")
    if needs_knowledge_retrieval:
        tool_names.append("knowledge_retrieval")
    if needs_generation:
        tool_names.append("generation")

    return {
        "user_input": text,
        "is_learn_command": is_learn_command,
        "is_source_trace_command": is_source_trace_command,
        "is_forget_command": is_forget_command,
        "needs_search": needs_search,
        "needs_coding": needs_coding,
        "needs_thinking": needs_thinking,
        "needs_memory": needs_memory and not is_greeting,
        "needs_generation": needs_generation,
        "needs_knowledge_retrieval": needs_knowledge_retrieval,
        "tool_names": tool_names,
        "reasoning": "Use tools when the request requires external facts, deep reasoning, persistent memory, or knowledge retrieval.",
    }


def get_agent_instruction(user_input: str, thinking_mode: bool = False, force_search: bool = False) -> str:
    """Return a small policy block that nudges the model toward tool-using behavior."""
    plan = build_agent_plan(user_input, force_search=force_search, thinking_mode=thinking_mode)
    instructions: List[str] = []

    if plan["needs_thinking"]:
        instructions.append("[Agent policy: FIRST write your step-by-step reasoning inside <thinking>...</thinking> tags before providing your final concise answer.]")
    if plan["needs_search"]:
        instructions.append("[Agent policy: synthesize live web search results accurately and cite sources clearly.]")
    if plan["needs_memory"]:
        instructions.append("[Agent policy: use relevant memory or prior context to personalize the answer without exposing private details.]")
    if plan["needs_knowledge_retrieval"]:
        instructions.append("[Agent policy: consult local knowledge when available and cite the most relevant passages.]")
    if plan["needs_coding"]:
        instructions.append("[Agent policy: for coding requests, reason step-by-step and provide practical, tested-style code guidance.]")

    return "\n".join(instructions)


def retrieve_local_knowledge(query: str, top_k: int = 3) -> List[str]:
    """Retrieve relevant passages from local docs using a lightweight fallback strategy."""
    text = (query or "").strip()
    if not text:
        return []

    project_root = Path(__file__).resolve().parents[1]
    # Restrict strictly to actual user documentation / upload directories (NEVER search training/)
    candidate_dirs = [project_root / "data" / "docs", project_root / "uploads"]

    try:
        import chromadb
        from chromadb.config import Settings

        persist_dir = project_root / "chroma_db"
        if persist_dir.exists():
            try:
                client = chromadb.Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=str(persist_dir)))
                if client:
                    try:
                        collections = [c.name for c in client.list_collections()]
                    except Exception:
                        collections = []
                    if "knowledge" in collections:
                        collection = client.get_collection("knowledge")
                        try:
                            from sentence_transformers import SentenceTransformer
                            embedder = SentenceTransformer("all-MiniLM-L6-v2")
                            results = collection.query(query_texts=[text], n_results=min(top_k, 5))
                            docs = results.get("documents", [])
                            if docs and docs[0]:
                                return [str(item).strip() for item in docs[0] if str(item).strip()]
                        except Exception:
                            pass
            except Exception:
                pass
    except Exception:
        pass

    # Stopwords to prevent spurious single-word matching
    STOPWORDS = {"the", "is", "at", "which", "on", "a", "an", "and", "or", "in", "for", "to", "what", "how", "why", "who", "hi", "hello", "hey", "it", "this", "that", "my", "your", "of", "with", "as", "are", "be"}
    words = set(w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 2 and w not in STOPWORDS)
    if not words:
        return []

    docs: List[Tuple[int, str]] = []
    for base in candidate_dirs:
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".txt", ".md", ".jsonl", ".json"}:
                continue
            try:
                content = path.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            if not content.strip():
                continue
            score = sum(1 for word in words if word in content.lower())
            if score > 0:
                docs.append((score, f"[{path.name}] {content[:400].strip()}"))

    docs.sort(key=lambda item: item[0], reverse=True)
    snippets = [snippet for _, snippet in docs[:top_k]]
    if snippets:
        return snippets
    return []


def collect_agent_context(user_input: str, void_mem=None, force_search: bool = False, thinking_mode: bool = False) -> Dict[str, object]:
    """Collect a unified set of context blocks from memory, knowledge, and web tools."""
    plan = build_agent_plan(user_input, force_search=force_search, thinking_mode=thinking_mode)
    context_blocks: List[str] = []
    tool_results: List[Tuple[str, str]] = []
    direct_response: Optional[str] = None

    # Handle Continuous Learning Command directly
    if plan.get("is_learn_command"):
        # Extract topic
        raw = user_input.strip()
        topic = re.sub(r"^(void,?\s*)?(please\s+)?(learn\s+about|learn|study|research\s+modern|research\s+latest|research)\s*", "", raw, flags=re.I).strip(" .?!:\"'")
        if topic:
            learn_report = knowledge_engine.learn(topic)
            direct_response = learn_report.get("summary_text") or learn_report.get("message")
            tool_results.append(("knowledge_learning", direct_response))
            context_blocks.append(f"[Knowledge Core Learned]\n{direct_response}")
            return {
                "plan": plan,
                "context_blocks": context_blocks,
                "tool_results": tool_results,
                "context_text": "\n\n".join(context_blocks),
                "direct_response": direct_response
            }

    # Handle Source Traceability Command directly ("Where did you learn this?")
    if plan.get("is_source_trace_command"):
        raw = user_input.strip()
        target = re.sub(r"^(void,?\s*)?(show\s+sources\s+for|what\s+are\s+your\s+sources\s+for|where\s+did\s+you\s+learn\s+about|where\s+did\s+you\s+learn\s+this\s+from|where\s+did\s+you\s+learn\s+this|where\s+did\s+you\s+get\s+this)\s*", "", raw, flags=re.I).strip(" .?!:\"'")
        trace = knowledge_engine.get_sources(target or "Vulkan")
        direct_response = trace.get("report_text") or trace.get("message")
        tool_results.append(("source_traceability", direct_response))
        context_blocks.append(f"[Source Traceability Report]\n{direct_response}")
        return {
            "plan": plan,
            "context_blocks": context_blocks,
            "tool_results": tool_results,
            "context_text": "\n\n".join(context_blocks),
            "direct_response": direct_response
        }

    # Handle Forget Command
    if plan.get("is_forget_command"):
        raw = user_input.strip()
        topic = re.sub(r"^(void,?\s*)?(forget\s+what\s+you\s+learned\s+about|forget\s+about)\s*", "", raw, flags=re.I).strip(" .?!:\"'")
        res = knowledge_engine.forget_knowledge(topic)
        direct_response = res.get("message")
        tool_results.append(("knowledge_forget", direct_response))
        context_blocks.append(f"[Knowledge Core Update]\n{direct_response}")
        return {
            "plan": plan,
            "context_blocks": context_blocks,
            "tool_results": tool_results,
            "context_text": "\n\n".join(context_blocks),
            "direct_response": direct_response
        }

    # 1. Check Local Learned Knowledge First (Requirement 7 Semantic Retrieval)
    learned_items = knowledge_engine.retrieve(user_input, limit=3)
    if learned_items:
        # Check if any matching knowledge is outdated
        has_outdated = any(item.get("is_outdated") for item in learned_items)
        if not has_outdated:
            k_lines = [f"- {item['fact']} (Verified from {item['source']})" for item in learned_items]
            joined_k = "\n".join(k_lines)
            context_blocks.append(f"[Local Learned Knowledge]\n{joined_k}")
            tool_results.append(("learned_knowledge", joined_k))

    if void_mem is not None and plan.get("needs_memory"):
        memory_context = void_mem.get_summary_context(user_input)
        if memory_context:
            context_blocks.append(f"[Memory Summary]\n{memory_context}")
            tool_results.append(("memory_rag", memory_context))

    if plan.get("needs_search") and not plan.get("is_learn_command"):
        search_query = extract_search_query(user_input)
        web_result = perform_search(search_query)
        context_blocks.append(f"[Web Search Results]\n{web_result}")
        tool_results.append(("web_search", web_result))

    if plan.get("needs_knowledge_retrieval") and not learned_items:
        knowledge_chunks = retrieve_local_knowledge(user_input)
        if knowledge_chunks:
            joined = "\n\n".join(knowledge_chunks)
            context_blocks.append(f"[Local Knowledge]\n{joined}")
            tool_results.append(("knowledge_retrieval", joined))

    return {
        "plan": plan,
        "context_blocks": context_blocks,
        "tool_results": tool_results,
        "context_text": "\n\n".join(context_blocks),
        "direct_response": None
    }

