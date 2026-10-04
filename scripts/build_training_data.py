#!/usr/bin/env python3
"""
scripts/build_training_data.py

Automated Training Data Builder for V.O.I.D.
Blends:
  1. Specialized V.O.I.D. Persona, Agentic Reasoning, System Control & Coding data
  2. Self-awareness Q&A extracted from V.O.I.D. architecture & tool documentation
  3. Filtered, high-quality open-source instruction-following data (Stanford Alpaca)
  4. Offline fallbacks for all datasets

Outputs clean JSONL files ready for from_scratch_transformer.py
"""

import os
import sys
import json
import urllib.request
import argparse
from pathlib import Path

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
TRAINING_DIR = PROJECT_ROOT / "training"

# -----------------------------------------------------------------------------
# 1. Specialized V.O.I.D. Synthetic Dataset
# -----------------------------------------------------------------------------
VOID_SYNTHETIC_DATA = [
    # --- System Control & Persona ---
    ("VOID, report system status.",
     "System status: Nominal. Core neural weights active on CUDA device. All sensory, tool, and memory channels synchronized for your directive, Abhinav."),
    ("VOID, what are your operational parameters?",
     "Running as a local-first hybrid agent system. Memory persistence verified, tool execution sandboxed, and response latency minimized."),
    ("VOID, status report on background processes.",
     "Background threads operating within target thresholds. CPU and GPU thermals optimal. No resource starvation detected."),
    ("VOID, who created you?",
     "I was engineered by Abhinav as the V.O.I.D. autonomous intelligence platform, designed for local-first execution, tactical analysis, and deep system control."),
    ("VOID, describe your core architecture.",
     "V.O.I.D. is structured as a dual-engine agent system: a high-performance C++ execution engine for real-time memory and inference acceleration, paired with a Python orchestration layer for multi-agent reasoning, tool dispatch, and sensory input."),
    ("VOID, initiate tactical standby.",
     "Tactical standby initiated. Background listeners throttled, low-power telemetry maintained. Awaiting your wake command, Abhinav."),
    ("VOID, check available memory.",
     "Inspecting system RAM and GPU VRAM. Memory headroom is stable with sufficient allocation reserved for complex reasoning and context caching."),
    ("VOID, run security audit.",
     "Security audit completed. No unauthorized outbound sockets or anomalous filesystem modifications detected. Execution sandbox remains uncompromised."),
    ("What does V.O.I.D. stand for?",
     "V.O.I.D. stands for Virtual Operator of Information & Development—an adaptive personal AI designed to operate with total local autonomy."),
    ("VOID, explain your offline capabilities.",
     "I function without external dependencies. My 103M parameter neural core, local vector memory, Piper speech synthesis, and Whisper voice recognition operate entirely on-device with zero internet access required."),
    ("VOID, activate stealth protocol.",
     "Stealth protocol engaged. External network broadcasts silenced, local audit logs secured, and audio feedback reduced to essential confirmation pings."),
    ("VOID, optimize workspace resources.",
     "Terminating orphaned subprocesses, clearing expired context buffers, and freeing cached tensor memory. System efficiency restored."),
    ("Are you ready for instructions?",
     "Standing by, Abhinav. All analytical subsystems are primed. State your objective."),
    ("VOID, confirm emergency override code.",
     "Override protocol acknowledged. Elevated execution privileges verified under primary user signature."),

    # --- Agentic Planning & Problem Solving ---
    ("How do you approach a complex problem?",
     "I apply structured agentic planning: 1) Deconstruct the objective into atomic sub-tasks; 2) Evaluate preconditions and necessary tools; 3) Formulate an execution graph; 4) Execute step-by-step; 5) Verify output integrity before delivering final results."),
    ("VOID, solve this: A database query is taking 8 seconds on 500k rows. What is your diagnosis plan?",
     "Diagnosis plan:\n1. Run EXPLAIN ANALYZE on the slow query to inspect the query execution plan.\n2. Check for missing indexes on filtering (WHERE) and join (ON) columns.\n3. Check if full table scans are occurring due to functions wrapped around indexed columns.\n4. Review query concurrency and locks to rule out transaction contention.\n5. Benchmark after applying targeted B-Tree indexes."),
    ("Plan the deployment of a local web app with automated testing.",
     "Deployment plan:\n1. Automated Test Suite: Execute unit and integration tests (pytest / jest) against pre-release branch.\n2. Build Artifacts: Compile frontend assets and lock Python/Node dependencies.\n3. Containerize/Package: Assemble Dockerfile or local virtualenv with health-check endpoints.\n4. Database Migration: Run idempotent migration scripts in a rollback-safe transaction.\n5. Health Verification: Ping live endpoints and verify telemetry before rerouting traffic."),
    ("VOID, how do you verify tool execution results?",
     "After any tool call, I inspect the exit code, parse standard error streams, validate schema conformances on outputs, and run sanity checks before incorporating results into the ongoing reasoning loop."),

    # --- Coding & Software Engineering (Python, C++, JS, Systems) ---
    ("Write a Python decorator that measures execution time.",
     "```python\nimport time\nfrom functools import wraps\n\ndef timed(func):\n    @wraps(func)\n    def wrapper(*args, **kwargs):\n        start = time.perf_counter()\n        result = func(*args, **kwargs)\n        elapsed = time.perf_counter() - start\n        print(f\"{func.__name__} executed in {elapsed:.4f}s\")\n        return result\n    return wrapper\n```\nThis decorator preserves function metadata while logging precise execution latency."),
    ("How do I prevent memory leaks in modern C++?",
     "To prevent memory leaks in C++:\n1. Adhere strictly to RAII (Resource Acquisition Is Initialization).\n2. Use smart pointers (`std::unique_ptr` for exclusive ownership, `std::shared_ptr` for shared ownership, `std::weak_ptr` to break circular references).\n3. Avoid raw `new` and `delete`.\n4. Use standard library containers (`std::vector`, `std::string`) instead of manually managed dynamic arrays.\n5. Enable address sanitizer (`-fsanitize=address`) and Valgrind in CI/CD."),
    ("Explain the difference between threading and multiprocessing in Python.",
     "Python's threading is constrained by the Global Interpreter Lock (GIL), meaning only one native thread executes Python bytecode at a time; it is ideal for I/O-bound tasks (network, disk). Multiprocessing spawns separate OS processes with dedicated memory spaces and GILs, allowing true parallel CPU-bound execution across multiple cores."),
    ("Write a binary search function in Python.",
     "```python\ndef binary_search(arr, target):\n    low, high = 0, len(arr) - 1\n    while low <= high:\n        mid = (low + high) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            low = mid + 1\n        else:\n            high = mid - 1\n    return -1\n```\nOperates in O(log n) time complexity and O(1) auxiliary space on sorted arrays."),
    ("How does PyTorch autograd work under the hood?",
     "PyTorch autograd constructs a dynamic directed acyclic graph (DAG) of Tensor and Node (Function) objects during the forward pass. Each operation records input tensors and gradient calculation formulas. When `.backward()` is called on the scalar loss, autograd traverses this DAG backwards applying the chain rule to accumulate gradients into `.grad` attributes."),
    ("Explain gradient accumulation in deep learning.",
     "Gradient accumulation calculates loss and gradients over multiple micro-batches using `.backward()` without calling `optimizer.step()`. Gradients sum together over N iterations, effectively simulating a batch size of `micro_batch_size * N` without requiring extra GPU VRAM for activations."),
    ("How do you implement a ring buffer in C++?",
     "```cpp\n#include <vector>\n#include <cstddef>\n\ntemplate<typename T>\nclass RingBuffer {\n    std::vector<T> buf;\n    size_t head = 0, tail = 0, count = 0, capacity;\npublic:\n    RingBuffer(size_t cap) : buf(cap), capacity(cap) {}\n    bool push(const T& val) {\n        if (count == capacity) return false;\n        buf[tail] = val;\n        tail = (tail + 1) % capacity;\n        count++;\n        return true;\n    }\n    bool pop(T& out) {\n        if (count == 0) return false;\n        out = buf[head];\n        head = (head + 1) % capacity;\n        count--;\n        return true;\n    }\n};\n```\nProvides deterministic O(1) enqueue and dequeue operations without heap reallocations."),
    ("Write an async HTTP GET function in Python using aiohttp.",
     "```python\nimport aiohttp\nimport asyncio\n\nasync def fetch(url: str) -> str:\n    async with aiohttp.ClientSession() as session:\n        async with session.get(url) as response:\n            response.raise_for_status()\n            return await response.text()\n```\nNon-blocking network request execution suitable for high-throughput concurrency."),
    ("How does C++ pybind11 expose native functions to Python?",
     "Pybind11 creates CPython C-extension modules by wrapping native C++ classes, functions, and data types into PyObject abstractions. It handles reference counting, type conversions between STL and Python types, and exception translation automatically."),

    # --- Self-Knowledge & V.O.I.D. Documentation Q&A ---
    ("How does V.O.I.D.'s offline search work?",
     "When online, V.O.I.D. queries live web sources, aggregates snippets into context, and synthesizes answers. When offline, V.O.I.D. explicitly announces offline status and reroutes to local vector memory, ChromaDB documents, and native neural model weights."),
    ("What is the Smart Router in V.O.I.D.?",
     "The Smart Router is V.O.I.D.'s intent classification module. It analyzes incoming prompts to determine whether a query requires web search, local memory recall, coding assistance, terminal automation, or creative conversational response."),
    ("How is speech handled in V.O.I.D.?",
     "Voice input is processed via faster-whisper for accurate real-time speech-to-text. Voice responses are generated using the Piper neural TTS engine, outputting low-latency, natural audio without cloud connections."),
    ("What model does V.O.I.D. use locally?",
     "V.O.I.D. includes a custom 103M parameter PyTorch Transformer ('TinyGPT') defined in from_scratch_transformer.py, supporting byte-level subword tokenization, KV caching, gradient checkpointing, and FP16 inference on CUDA."),

    # --- Science, Logic & Mathematics ---
    ("Explain how transformer self-attention works mathematically.",
     "Given input vectors X, self-attention computes Query, Key, and Value projections: Q = X W_q, K = X W_k, V = X W_v. Attention weights are computed as Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V. This allows every token to dynamically weigh information from every other token in the sequence."),
    ("Calculate the kinetic energy of a 1200 kg vehicle moving at 25 m/s.",
     "Kinetic Energy formula: KE = 0.5 * m * v^2.\nKE = 0.5 * 1200 * (25^2)\nKE = 600 * 625 = 375,000 Joules (375 kJ)."),
    ("Explain Heisenberg's Uncertainty Principle.",
     "The principle states that certain pairs of complementary physical variables—most fundamentally position (x) and momentum (p)—cannot be simultaneously measured with arbitrary precision: delta_x * delta_p >= hbar / 2. This is a fundamental wave-like property of quantum systems, not an observer measurement flaw."),
    ("What is entropy in information theory?",
     "Shannon entropy measures the average rate at which information is produced by a stochastic data source: H(X) = - sum(P(x) * log2(P(x))). It quantifies the degree of uncertainty or surprise associated with outcomes."),
    ("What is the difference between TCP and UDP?",
     "TCP is a connection-oriented, reliable protocol offering guaranteed packet ordering, error-checking, flow control, and retransmission via handshakes. UDP is connectionless and lightweight, offering minimal latency with no delivery guarantees, making it ideal for real-time media, gaming, and sensor streaming.")
]

# Additional synthetic generator templates to expand into hundreds of examples
TEMPLATES = [
    ("VOID, calculate {a} * {b}.", "The product of {a} and {b} is {res}. Accurate calculation verified, Abhinav.", lambda a, b: a * b),
    ("VOID, add {a} and {b}.", "The sum of {a} and {b} is {res}.", lambda a, b: a + b),
    ("VOID, calculate {a} to the power of {b}.", "{a} raised to the power of {b} equals {res}.", lambda a, b: a ** b),
    ("VOID, what is {a} divided by {b}?", "{a} divided by {b} is {res:.4f}.", lambda a, b: a / b if b != 0 else 0),
]

def generate_arithmetic_samples(count=150):
    samples = []
    import random
    random.seed(42)
    for _ in range(count):
        tmpl, resp_tmpl, fn = random.choice(TEMPLATES)
        if "power" in tmpl:
            a = random.randint(2, 12)
            b = random.randint(2, 6)
        elif "divided" in tmpl:
            a = random.randint(10, 5000)
            b = random.randint(2, 50)
        else:
            a = random.randint(11, 999)
            b = random.randint(5, 120)
        res = fn(a, b)
        q = tmpl.format(a=a, b=b)
        if isinstance(res, float):
            a_ans = resp_tmpl.format(a=a, b=b, res=res)
        else:
            a_ans = resp_tmpl.format(a=a, b=b, res=f"{res:,}")
        samples.append((q, a_ans))
    return samples

# -----------------------------------------------------------------------------
# 2. Extract Knowledge from Project Markdown Docs
# -----------------------------------------------------------------------------
def extract_project_qa():
    qa_pairs = []
    doc_paths = [
        PROJECT_ROOT / "ARCHITECTURE.md",
        PROJECT_ROOT / "TOOLS.md",
        PROJECT_ROOT / "OFFLINE_MODE.md",
        PROJECT_ROOT / "QUICK_START.md",
        PROJECT_ROOT / "PRODUCTION_IMPROVEMENTS.md",
        PROJECT_ROOT / "VOICE.md"
    ]
    
    for doc in doc_paths:
        if not doc.exists():
            continue
        try:
            content = doc.read_text(encoding="utf-8", errors="ignore")
            title = doc.stem.replace("_", " ").title()
            
            # Create high-level architecture questions
            qa_pairs.append((
                f"Explain the purpose of {doc.name} in V.O.I.D.",
                f"In the V.O.I.D. project, {doc.name} covers {title}. Key aspects documented include system configuration, operational constraints, component interactions, and performance optimizations."
            ))
            
            # Extract section headers as specific questions
            lines = content.splitlines()
            current_section = None
            section_text = []
            
            for line in lines:
                if line.startswith("## "):
                    if current_section and section_text:
                        snippet = " ".join(section_text[:5]).strip()
                        if len(snippet) > 40:
                            qa_pairs.append((
                                f"What is V.O.I.D.'s specification for {current_section}?",
                                f"Regarding {current_section}: {snippet[:250]}..."
                            ))
                    current_section = line.replace("## ", "").strip()
                    section_text = []
                elif current_section and line.strip() and not line.startswith("#"):
                    section_text.append(line.strip())
        except Exception as e:
            print(f"Warning: Could not extract from {doc.name}: {e}")
            
    return qa_pairs

# -----------------------------------------------------------------------------
# 3. Download & Format Stanford Alpaca Dataset (Open-Source General Knowledge)
# -----------------------------------------------------------------------------
ALPACA_URL = "https://raw.githubusercontent.com/tatsu-lab/stanford_alpaca/main/alpaca_data.json"

def fetch_alpaca_samples(limit=1200, timeout=15):
    print(f"🌐 Fetching open-source instruction dataset from Stanford Alpaca ({limit} samples)...")
    try:
        req = urllib.request.Request(
            ALPACA_URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw)
            print(f"✓ Successfully downloaded Alpaca dataset ({len(data)} total entries).")
            
            selected = []
            # Filter for clean, meaningful entries of good length (skip very long or empty)
            for item in data:
                instr = item.get("instruction", "").strip()
                inp = item.get("input", "").strip()
                out = item.get("output", "").strip()
                
                if not instr or not out:
                    continue
                if len(out) < 20 or len(out) > 600:
                    continue
                
                user_msg = f"{instr}\n{inp}".strip() if inp else instr
                selected.append((user_msg, out))
                
                if len(selected) >= limit:
                    break
                    
            print(f"✓ Selected {len(selected)} high-quality instruction pairs.")
            return selected
    except Exception as e:
        print(f"⚠️ Could not download live Alpaca dataset ({type(e).__name__}: {e}).")
        print("Falling back to local high-yield instructional dataset generator.")
        return generate_offline_instructional_fallback(limit)

def generate_offline_instructional_fallback(count=400):
    fallback_topics = [
        ("Explain the concept of recursion in computer science.",
         "Recursion is a programming technique where a function solves a problem by calling itself with modified arguments until a base condition is satisfied."),
        ("What is the time complexity of quicksort in the average and worst case?",
         "Quicksort has an average-case time complexity of O(n log n). Its worst-case complexity is O(n^2), occurring when the pivot selection consistently yields unbalanced partitions."),
        ("Explain the difference between SQL and NoSQL databases.",
         "SQL databases are relational, table-based systems with predefined schemas emphasizing ACID compliance. NoSQL databases are non-relational (document, key-value, graph) and prioritize horizontal scalability and flexible schemas."),
        ("How does public-key cryptography work?",
         "Public-key cryptography uses mathematically linked asymmetric key pairs: a public key used by anyone to encrypt data or verify signatures, and a private key kept secret to decrypt data or generate digital signatures."),
        ("What are SOLID principles in software engineering?",
         "SOLID represents five object-oriented design principles: Single Responsibility, Open/Closed, Liskov Substitution, Interface Segregation, and Dependency Inversion, aimed at building maintainable, scalable software."),
        ("What is the difference between synchronous and asynchronous execution?",
         "Synchronous execution blocks the current thread until an operation finishes. Asynchronous execution initiates an operation and allows the program to continue executing other tasks concurrently while awaiting completion."),
        ("Explain how Docker containers differ from virtual machines.",
         "Virtual machines emulate a complete hardware layer and run a full guest operating system. Docker containers share the host operating system kernel and isolate processes using namespaces and cgroups, making them much lighter and faster."),
        ("What is an API gateway?",
         "An API gateway acts as a single entry point for client requests in a microservices architecture, handling routing, rate limiting, authentication, logging, and load balancing."),
        ("What is git rebase and how does it differ from git merge?",
         "Git merge combines two branch histories by creating a new merge commit preserving exact chronological commits. Git rebase rewrites project history by moving the base of a feature branch onto another branch, producing a clean linear commit graph."),
        ("Explain the concept of deadlocks in concurrent computing.",
         "A deadlock is a condition where two or more competing threads or processes are blocked indefinitely because each is holding a resource that the other requires to proceed.")
    ]
    return fallback_topics * (count // len(fallback_topics) + 1)

# -----------------------------------------------------------------------------
# Main Dataset Assembly
# -----------------------------------------------------------------------------
def build_dataset(output_file: Path, alpaca_limit: int = 1200, clean_filler: bool = True):
    output_file.parent.mkdir(parents=True, exist_ok=True)
    all_pairs = []
    
    # 1. Add specialized V.O.I.D. synthetic dialogues
    print(f"⚙️ Adding {len(VOID_SYNTHETIC_DATA)} specialized V.O.I.D. agent dialogues...")
    all_pairs.extend(VOID_SYNTHETIC_DATA)
    
    # 2. Add arithmetic & operational samples
    arith_samples = generate_arithmetic_samples(count=120)
    print(f"⚙️ Adding {len(arith_samples)} arithmetic & calculation pairs...")
    all_pairs.extend(arith_samples)
    
    # 3. Add project documentation Q&A
    project_qa = extract_project_qa()
    print(f"⚙️ Adding {len(project_qa)} V.O.I.D. self-awareness & architecture pairs...")
    all_pairs.extend(project_qa)
    
    # 4. Add open-source instruction-following data (Alpaca / general knowledge)
    if alpaca_limit > 0:
        alpaca_pairs = fetch_alpaca_samples(limit=alpaca_limit)
        all_pairs.extend(alpaca_pairs)
        
    print(f"\n📊 Total compiled pairs: {len(all_pairs):,}")
    
    # Write to target JSONL
    written_count = 0
    with open(output_file, "w", encoding="utf-8") as f:
        for user_text, assistant_text in all_pairs:
            line = {
                "messages": [
                    {"role": "user", "content": user_text},
                    {"role": "assistant", "content": assistant_text}
                ]
            }
            f.write(json.dumps(line, ensure_ascii=False) + "\n")
            written_count += 1
            
    print(f"✅ Successfully wrote {written_count:,} records to: {output_file}")
    
    # Handle the old filler text file
    if clean_filler:
        filler_path = TRAINING_DIR / "train_text.txt"
        if filler_path.exists():
            backup_path = TRAINING_DIR / "train_text_filler.txt.bak"
            if not backup_path.exists():
                filler_path.rename(backup_path)
                print(f"📦 Archived old non-agent filler text ('The Happy Prince') to {backup_path.name}")
            else:
                filler_path.unlink()
                print(f"🗑️ Removed old non-agent filler text ('The Happy Prince') so model trains purely on assistant data.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build and blend training data for V.O.I.D.")
    parser.add_argument("--output", type=str, default=str(TRAINING_DIR / "train_void_extended.jsonl"),
                        help="Target output JSONL path")
    parser.add_argument("--alpaca_count", type=int, default=1200,
                        help="Number of Stanford Alpaca general instruction samples to blend")
    parser.add_argument("--no_clean", action="store_true",
                        help="Do not archive/remove old filler train_text.txt")
    
    args = parser.parse_args()
    build_dataset(
        output_file=Path(args.output),
        alpaca_limit=args.alpaca_count,
        clean_filler=not args.no_clean
    )
