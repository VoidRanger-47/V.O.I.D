# scripts/build_training_corpus.py
"""
V.O.I.D. Multi-Domain High-Quality Training Corpus Builder.
Downloads, converts, and blends curated internet datasets across 3 essential domains:
1. Cybersecurity: Threat analysis, penetration testing, MITRE ATT&CK, CVE analysis, C2 defenses.
2. Coding & Software: Algorithms, Python/C++/Rust, debugging, refactoring, systems programming.
3. Language & Conversational Fluency: Multi-turn reasoning, helpfulness, and technical dialogue.

Target Output: Formatted JSONL (`training/train_void_master.jsonl`) ready for direct ingestion
into `from_scratch_transformer.py`.
"""

import os
import sys
import json
import time
import requests
import pandas as pd
from typing import Generator, Dict, Any

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "..", "training", "train_void_master.jsonl")
PROGRESS_FILE = os.path.join(os.path.dirname(__file__), "..", "training", ".corpus_progress.json")

DATASET_SOURCES = {
    "cybersecurity_trendyol": {
        "url": "https://huggingface.co/datasets/ChavyvAkvar/Trendyol-Cybersecurity-Instruction-Tuning-Dataset-Converted/resolve/main/data/train-00000-of-00001.parquet",
        "type": "parquet_messages",
        "description": "53,200 multi-turn cybersecurity instruction & defense dialogs"
    },
    "cybersecurity_alpaca": {
        "url": "https://huggingface.co/datasets/ahmedds10/alpaca_Cybersecurity_json/resolve/main/alpaca_Cybersecurity.json",
        "type": "alpaca_json",
        "description": "Comprehensive cybersecurity prompts, exploits, defense strategies"
    },
    "code_alpaca_20k": {
        "url": "https://raw.githubusercontent.com/sahil280114/codealpaca/master/data/code_alpaca_20k.json",
        "type": "alpaca_json",
        "description": "20,000 clean algorithmic and practical code instructions"
    },
    "code_instructions_120k": {
        "url": "https://huggingface.co/datasets/TokenBender/code_instructions_122k_alpaca_style/resolve/main/code_instructions_120k.json",
        "type": "alpaca_json",
        "description": "120,000 multi-language software engineering and systems coding pairs"
    },
    "ultrachat_conversational": {
        "url": "https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k/resolve/main/data/train_sft-00000-of-00003-a3ecf92756993583.parquet",
        "type": "parquet_messages",
        "description": "69,000 rich multi-turn conversational fluency, reasoning, and instruction sessions"
    }
}


def format_conversation(user_prompt: str, assistant_response: str) -> Dict[str, Any]:
    return {
        "messages": [
            {"role": "user", "content": user_prompt.strip()},
            {"role": "assistant", "content": assistant_response.strip()}
        ]
    }


def stream_parquet_messages(url: str, max_samples: int = 50000) -> Generator[Dict[str, Any], None, None]:
    print(f"📥 Streaming parquet dataset: {url}")
    df = pd.read_parquet(url)
    count = 0
    for msgs in df['messages']:
        if msgs is None:
            continue
        valid_msgs = []
        for m in msgs:
            if isinstance(m, dict) and m.get('content') and m.get('role'):
                role = "user" if m['role'] in ("user", "human") else "assistant"
                valid_msgs.append({"role": role, "content": m['content'].strip()})
        if len(valid_msgs) >= 2:
            yield {"messages": valid_msgs}
            count += 1
            if count >= max_samples:
                break


def stream_alpaca_json(url: str, max_samples: int = 60000) -> Generator[Dict[str, Any], None, None]:
    print(f"📥 Streaming Alpaca JSON dataset: {url}")
    resp = requests.get(url, timeout=30)
    data = resp.json()
    count = 0
    for item in data:
        instr = item.get("instruction", "").strip()
        inp = item.get("input", "").strip()
        out = item.get("output", "").strip()
        if not instr or not out:
            continue
        user_prompt = f"{instr}\nContext: {inp}" if inp else instr
        yield format_conversation(user_prompt, out)
        count += 1
        if count >= max_samples:
            break


def build_corpus(max_mb: float = 1200.0):
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    total_written_bytes = 0
    total_conversations = 0

    print(f"🚀 Starting V.O.I.D. Master Corpus Construction (Target: ~{max_mb} MB)...")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out_f:
        # 1. Cybersecurity Datasets
        print("\n🔒 [Phase 1/3] Ingesting Cybersecurity Instruction Corpora...")
        try:
            for item in stream_parquet_messages(DATASET_SOURCES["cybersecurity_trendyol"]["url"], max_samples=40000):
                line = json.dumps(item, ensure_ascii=False) + "\n"
                out_f.write(line)
                total_written_bytes += len(line.encode("utf-8"))
                total_conversations += 1
        except Exception as e:
            print(f"⚠️ Error on Trendyol cyber dataset: {e}")

        try:
            for item in stream_alpaca_json(DATASET_SOURCES["cybersecurity_alpaca"]["url"], max_samples=30000):
                line = json.dumps(item, ensure_ascii=False) + "\n"
                out_f.write(line)
                total_written_bytes += len(line.encode("utf-8"))
                total_conversations += 1
        except Exception as e:
            print(f"⚠️ Error on Alpaca cyber dataset: {e}")

        print(f"  └─ Progress: {round(total_written_bytes / 1e6, 2)} MB ({total_conversations} items)")

        # 2. Coding & Software Architecture
        print("\n💻 [Phase 2/3] Ingesting Multi-Language Code Corpora...")
        try:
            for item in stream_alpaca_json(DATASET_SOURCES["code_alpaca_20k"]["url"], max_samples=20000):
                line = json.dumps(item, ensure_ascii=False) + "\n"
                out_f.write(line)
                total_written_bytes += len(line.encode("utf-8"))
                total_conversations += 1
        except Exception as e:
            print(f"⚠️ Error on CodeAlpaca: {e}")

        try:
            for item in stream_alpaca_json(DATASET_SOURCES["code_instructions_120k"]["url"], max_samples=45000):
                line = json.dumps(item, ensure_ascii=False) + "\n"
                out_f.write(line)
                total_written_bytes += len(line.encode("utf-8"))
                total_conversations += 1
                if total_written_bytes >= (max_mb * 1e6 * 0.7):
                    break
        except Exception as e:
            print(f"⚠️ Error on Code Instructions 120k: {e}")

        print(f"  └─ Progress: {round(total_written_bytes / 1e6, 2)} MB ({total_conversations} items)")

        # 3. High-Fluency Conversational & Reasoning (UltraChat)
        print("\n🗣️ [Phase 3/3] Ingesting Multi-Turn Language & Reasoning Corpora...")
        try:
            for item in stream_parquet_messages(DATASET_SOURCES["ultrachat_conversational"]["url"], max_samples=40000):
                line = json.dumps(item, ensure_ascii=False) + "\n"
                out_f.write(line)
                total_written_bytes += len(line.encode("utf-8"))
                total_conversations += 1
                if total_written_bytes >= (max_mb * 1e6):
                    break
        except Exception as e:
            print(f"⚠️ Error on UltraChat: {e}")

    final_mb = round(total_written_bytes / 1e6, 2)
    print(f"\n🎉 Master Training Corpus Ready!")
    print(f"📁 Output: {OUTPUT_FILE}")
    print(f"📊 Total Size: {final_mb} MB ({round(final_mb / 1024, 2)} GB)")
    print(f"💬 Total High-Quality Dialogues: {total_conversations:,}")


if __name__ == "__main__":
    build_corpus(max_mb=1200.0)
