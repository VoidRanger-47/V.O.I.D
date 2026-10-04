# V.O.I.D. — Local Multi-Agent AI Operating Layer Architecture

## Core Architectural Principle
**V.O.I.D. is NOT an LLM chatbot application (`USER -> LLM -> TOOLS -> RESPONSE`).**

V.O.I.D. is a **Local Multi-Agent Artificial Intelligence System** composed of cooperating specialized agents orchestrated by an Executive Core over a typed Agent Message Protocol and Event Bus.

The Local LLM is only a replaceable cognitive component used where natural language synthesis or code reasoning is required. Deterministic agents operate with zero LLM overhead for maximum execution speed, deterministic reliability, and 4GB VRAM preservation.

```text
                    V.O.I.D. AI
                         │
                  EXECUTIVE CORE
                         │
        ┌────────────────┼────────────────┐
        │                │                │
   PERCEPTION         MEMORY          PLANNING
     AGENT             AGENT            AGENT
        │                │                │
        └────────────────┼────────────────┘
                         │
                  AGENT COORDINATOR
                         │
       ┌─────────────────┼──────────────────┐
       │                 │                  │
   CODING AGENT      SYSTEM AGENT      RESEARCH AGENT
       │                 │                  │
   COMPUTER AGENT     VISION AGENT      KNOWLEDGE AGENT
       │                 │                  │
   VOICE AGENT       AUTOMATION AGENT   VERIFICATION AGENT
       │                 │                  │
       └─────────────────┼──────────────────┘
                         │
                   VERIFICATION
                      AGENT
                         │
                         ▼
                   EXECUTIVE CORE
                         │
                         ▼
                      USER
```

---

## The 13 Specialized Cooperating Agents

### 1. Executive Agent (`executive`)
- **Role**: Central decision-making and user orchestration engine.
- **Responsibilities**: Understands high-level user intent, queries perception, requests plans from PlanningAgent, delegates tasks to the coordinator, evaluates independent verification results, and provides synthesized verified responses to the user.

### 2. Perception Agent (`perception_agent`)
- **Role**: Multimodal sensory and environmental observer.
- **Responsibilities**: Aggregates active application window, hardware telemetry, network connectivity, and sensory input into structured perception frames.

### 3. Memory Agent (`memory_agent`)
- **Role**: Sole gateway for multi-tiered memory.
- **Responsibilities**: Manages 6 memory tiers (Working, Episodic, Semantic, Preference, Project, Procedural) in local SQLite (`void_memory.db`) with vector embeddings (`all-MiniLM-L6-v2`) and explicit privacy deletion (`"VOID, forget that"`).

### 4. Planning Agent (`planning_agent`)
- **Role**: Goal decomposition and dynamic recovery planner.
- **Responsibilities**: Generates directed acyclic graphs (DAG) of agent execution steps. Dynamically computes alternative recovery strategies when a task fails verification.

### 5. Verification Agent (`verification_agent`)
- **Role**: Independent objective auditor.
- **Responsibilities**: Validates outputs against objective criteria (unit tests, output syntax validity, non-empty responses, file presence on disk, mathematical validity). Emits `PASS`, `FAIL`, or `REPLAN_REQUIRED`.

### 6. Coding Agent (`coding_agent`)
- **Role**: Software engineering, debugging, and sandboxed math evaluator.
- **Responsibilities**: Workspace inspection, AST-sandboxed Python execution, syntax debugging, and test running.

### 7. System Agent (`system_agent`)
- **Role**: Zero-LLM deterministic hardware guardian.
- **Responsibilities**: Monitors CPU %, RAM, GPU VRAM, storage, active processes, and Guardian health alerts.

### 8. Computer Agent (`computer_agent`)
- **Role**: Controlled desktop automation.
- **Responsibilities**: Launches desktop applications from a strict allowlist (VS Code, Notepad, Calc, Explorer, Terminal) with Level 4 permission verification.

### 9. Knowledge Agent (`knowledge_agent`)
- **Role**: Local offline documentation and RAG engine.
- **Responsibilities**: Extracts text and parses local PDF documents, workspace markdown, and codebase references.

### 10. Research Agent (`research_agent`)
- **Role**: Optional external web search plugin.
- **Responsibilities**: Gathers web facts when network is available; strictly isolated and fails gracefully with zero delay when offline.

### 11. Vision Agent (`vision_agent`)
- **Role**: Local visual perception.
- **Responsibilities**: Inspects local screenshots, images, and UI diagrams.

### 12. Voice Agent (`voice_agent`)
- **Role**: Offline voice interaction pipeline.
- **Responsibilities**: Coordinates `"Hey V.O.I.D."` acoustic wake word, Faster-Whisper STT, Piper TTS, and barge-in voice interruption.

### 13. Automation Agent (`automation_agent`)
- **Role**: Background task scheduler and maintainer.
- **Responsibilities**: Manages timers, reminders, scheduled background jobs, and periodic memory optimization sweeps.

---

## Agent Communication Protocol (`core/agents/protocol.py`)
All inter-agent communication is strictly structured:
```python
@dataclass
class AgentMessage:
    sender: str
    receiver: str
    message_type: AgentMessageType  # REQUEST, RESPONSE, EVENT, DELEGATE, VERIFY, STATUS_UPDATE
    priority: AgentPriority        # CRITICAL, HIGH, NORMAL, LOW, BACKGROUND
    goal: str
    task_id: str
    mission_id: Optional[str]
    context: Dict[str, Any]
    payload: Dict[str, Any]
    result: Optional[Any]
    status: str                    # PENDING, IN_PROGRESS, SUCCESS, FAILED, REPLAN_REQUIRED
    error: Optional[str]
    timestamp: float
```

---

## Persistent Mission System (`core/mission.py`)
Multi-step goals persist in SQLite (`void_memory/void_missions.db`) across computer reboots:
- **Mission tracking**: Title, Goal, Status (`IN_PROGRESS`, `COMPLETED`, `PAUSED`, `FAILED`), Progress %, Current Objective, Blockers, Steps list, Assigned Agents list.
- **API Endpoints**: `GET /api/missions`, `POST /api/missions`, `PUT /api/missions`.

---

## Hardware Optimization (RTX 3050 Laptop GPU, 4GB VRAM)
- Model lazy loading via `providers.manager.ModelManager`.
- Half-precision CUDA float16 STT / int8 CPU fallback.
- Deterministic agents operate with zero VRAM consumption.
