# 🚀 V.O.I.D. Release Notes — v0.1.0 (Genesis)

**Release Date:** October 11, 2026  
**Codename:** *Local Neural Foundation*  
**Tag:** `v0.1.0`  

---

## 🌟 Executive Overview
We are thrilled to announce the inaugural public release of **V.O.I.D. (Virtual Operator of Information & Development) v0.1.0**. 

V.O.I.D. transforms how developers and AI power-users interact with autonomous systems. Rather than relying on cloud-dependent LLM wrappers with recurring token fees and data privacy compromises, V.O.I.D. delivers a **100% local multi-agent operating layer** engineered to run on consumer hardware (such as an NVIDIA RTX 3050 Laptop GPU with 4GB VRAM, or standard CPU).

---

## 🔑 Key Features in v0.1.0

### 1. 13-Agent Autonomous Cooperative Network
- **Executive Agent**: Orchestrates goal intake, plan validation, and user response synthesis.
- **Perception Agent**: Aggregates hardware telemetry, active window focus, and environmental status.
- **Memory Agent**: Gatekeeper for an 8-tier persistent memory engine in SQLite (`void_memory.db`) with vector search and privacy deletion (`"VOID, forget that"`).
- **Planning Agent**: Formulates Directed Acyclic Graphs (DAGs) and dynamic replanning triggers.
- **Verification Agent**: Objective auditor validating tests, output schemas, and mathematics.
- **Coding Agent**: Workspace code inspection, refactoring, and AST-sandboxed execution.
- **System Agent**: Zero-LLM hardware guardian monitoring CPU, RAM, and GPU VRAM with zero overhead.
- **Computer Agent**: Governed desktop application launcher with a strict allowlist.
- **Knowledge Agent**: Local document, Markdown, and PDF semantic extraction.
- **Research Agent**: Isolated, graceful external web retrieval when network is available.
- **Vision Agent**: Local optical perception, face exposure, spatial geometry, and object tracking.
- **Voice Agent**: Offline wake-word detection (`"Hey V.O.I.D."`), Faster-Whisper STT, and Piper TTS.
- **Automation Agent**: Background cron scheduler, periodic timers, and memory sweeps.

### 2. Live Optical Perception & Telemetry Cockpit
- Real-time optical viewport operating at 30 FPS.
- Zero-shot neural object classification powered by YOLOv8s-World (Open-Vocabulary).
- Comprehensive Subject Dossier: Distance estimation, spatial geometry, head pose, 3D liveness, attention index, and clothing color sampling.
- Standalone privacy controls with explicit one-click camera hardware disconnect.

### 3. AST Sandboxed Execution & Granular Security
- Python AST static analysis blocking dangerous functions (`os.system`, `subprocess.Popen`, arbitrary file deletion).
- 7-tier granular permission hierarchy (Level 0 Conversation through Level 6 Network).
- Instant Emergency Stop circuit breaker via API and UI.

### 4. Custom Byte-Level Transformer
- Trainable from-scratch GPT-style transformer model with byte-level tokenizer (`from_scratch_transformer.py`).
- Automatic VRAM estimation, gradient clipping, learning rate clamping, and fp16 mixed-precision acceleration.

### 5. Native Frameless Desktop Launcher
- Launch standalone desktop application via `python desktop_app.py` or `launch_void_app.bat`.
- Zero Electron bloat: Leverages local Chromium/Edge runtime in dedicated `--app` mode with auto-managed backend lifecycle.

---

## 📦 Quick Installation
```bash
git clone https://github.com/VoidRanger-47/V.O.I.D.git
cd V.O.I.D
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
python desktop_app.py
```

---

## 🧪 Automated Testing & Quality
- Automated test coverage across Multi-Agent routing, Security AST sandboxing, and Verification Agent.
- Verified test suite: 16 core tests passing in < 11 seconds.
- Continuous Integration workflow established via GitHub Actions.
