# V.O.I.D. — Offline-First Architecture

## Absolute Principle
**V.O.I.D.'s core operating layer functions with 100% independence from the internet.**
Disconnecting Wi-Fi, Ethernet, and cloud endpoints does NOT impair core operations.

---

## Offline Core Capabilities Matrix

| Subsystem | Local Implementation | Cloud Dependency? |
| :--- | :--- | :--- |
| **Language Model** | Custom 103M PyTorch GPT Transformer (`checkpoint.pt`) + GGUF loader | **NONE (100% Local)** |
| **Speech-to-Text (STT)** | Local `faster-whisper` (`small.en` on CUDA / CPU int8) | **NONE (100% Local)** |
| **Text-to-Speech (TTS)** | Local `piper` voice model + in-process Windows audio playback | **NONE (100% Local)** |
| **Wake Word** | Local acoustic energy & zero-crossing rate detector (`"Hey V.O.I.D."`) | **NONE (100% Local)** |
| **Memory & RAG** | Local SQLite (`void_memory.db`) + local `all-MiniLM-L6-v2` embeddings | **NONE (100% Local)** |
| **Math & Calculus** | Local SymPy parser and evaluator | **NONE (100% Local)** |
| **Document Processing** | Local `pdfplumber` / text analyzer | **NONE (100% Local)** |
| **Computer Control** | Local process launcher & system monitor (`psutil`) | **NONE (100% Local)** |
| **Security & Sandbox** | Local Python AST validator & restricted runtime | **NONE (100% Local)** |
| **Web Search** | DuckDuckGo search (isolated optional plugin) | **OPTIONAL (Fails gracefully when offline)** |

---

## Zero-Latency Connection Sensing
`lib.offline_manager.OfflineManager` caches connectivity checks with a non-blocking 0.5s timeout, guaranteeing that local queries never hang or delay when network access is unavailable.
