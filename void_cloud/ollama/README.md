# 🦙 V.O.I.D. Ollama Offline Model Engine

The **Ollama Offline Engine** provides V.O.I.D. with private, 100% local, high-speed LLM inference. It runs completely offline on your host machine without sending any data over the internet.

---

## ⚡ Quick Start

### 1. Install Ollama
If not already installed on your system:
- **Windows**: Run `winget install Ollama.Ollama` or download installer from [ollama.com/download](https://ollama.com/download)
- **Linux**: `curl -fsSL https://ollama.com/install.sh | sh`
- **macOS**: `brew install ollama`

### 2. Check Engine Status
```bash
python -m void_cloud.ollama.cli status
```

### 3. Pull an Offline Model
Download any top-tier open-source model:
```bash
# Ultra-fast lightweight model (3B parameters — runs on any PC/laptop):
python -m void_cloud.ollama.cli pull llama3.2

# Reasoning & Thinking model:
python -m void_cloud.ollama.cli pull deepseek-r1:8b

# Advanced coding model:
python -m void_cloud.ollama.cli pull qwen2.5-coder:7b
```

### 4. Test Live Streaming Inference
```bash
python -m void_cloud.ollama.cli run "Explain what an autonomous agent is in 2 sentences."
```

### 5. Launch Interactive Offline Chat
```bash
python -m void_cloud.ollama.cli chat
```

---

## 🎯 Recommended Offline Models by Hardware

| Hardware Tier | Recommended Model | Command |
|---|---|---|
| **Entry (4–8 GB RAM)** | LLaMA 3.2 (1B or 3B), Phi-3 | `python -m void_cloud.ollama.cli pull llama3.2` |
| **Mid-Tier (8–16 GB RAM / GPU)** | DeepSeek R1 8B, Qwen 2.5 7B, Mistral 7B | `python -m void_cloud.ollama.cli pull deepseek-r1:8b` |
| **High Performance (16 GB+ VRAM)** | DeepSeek R1 14B, Qwen 2.5 Coder 14B | `python -m void_cloud.ollama.cli pull qwen2.5-coder:14b` |

---

## 💻 Python API Usage in V.O.I.D.

```python
from void_cloud.ollama import ollama_manager

# 1. Check status
print(ollama_manager.get_status())

# 2. Real-time token streaming
for token in ollama_manager.stream_tokens("Analyze this telemetry reading"):
    print(token, end="", flush=True)

# 3. Complete non-streaming generation
response = ollama_manager.generate("Write a quick greeting")
print(response)

# 4. Switch active model dynamically
ollama_manager.set_model("deepseek-r1:8b")
```

---

## ⚙️ Configuration

Settings are saved in [`void_cloud/ollama/config.json`](file:///c:/Users/kbven/OneDrive/Documents/VOID/void_cloud/ollama/config.json):
- `host`: Ollama daemon endpoint (default `http://localhost:11434`, or env `OLLAMA_HOST`)
- `model`: Default active model tag
- `fallback_models`: List of fallback models attempted automatically if configured model is missing
- `num_ctx`: Context window size (default 4096 tokens)
- `temperature`: Creativity slider (default 0.7)
- `auto_discover`: Automatically detects installed local models
