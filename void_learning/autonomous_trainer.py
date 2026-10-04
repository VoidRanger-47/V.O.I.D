# void_learning/autonomous_trainer.py
"""
V.O.I.D. Autonomous Self-Training Agent
=========================================
FULL AUTO MODE - V.O.I.D. independently:
  1. Scouts the internet for high-quality training datasets
  2. Evaluates each candidate for quality, size, and domain relevance
  3. PAUSES and requests explicit ADMIN AUTHORIZATION before any downloads or training
  4. Upon authorization: downloads, converts, and blends the datasets
  5. Launches the transformer training loop from the latest checkpoint
  6. Reports progress in real-time via SSE event stream

Authorization Gate (Critical Safety Mechanism):
  - V.O.I.D. will NEVER download or train without explicit admin approval.
  - State: IDLE -> SCOUTING -> AWAITING_AUTHORIZATION -> AUTHORIZED -> DOWNLOADING -> TRAINING -> COMPLETE
  - Admin can ABORT at any time.
"""

import os
import sys
import json
import time
import uuid
import threading
import subprocess
import requests
from typing import List, Dict, Any, Optional, Generator
from datetime import datetime
from dataclasses import dataclass, field, asdict
from enum import Enum


class AutoTrainState(Enum):
    IDLE                    = "IDLE"
    SCOUTING                = "SCOUTING"
    AWAITING_AUTHORIZATION  = "AWAITING_AUTHORIZATION"
    AUTHORIZED              = "AUTHORIZED"
    DOWNLOADING             = "DOWNLOADING"
    BUILDING_CORPUS         = "BUILDING_CORPUS"
    TRAINING                = "TRAINING"
    COMPLETE                = "COMPLETE"
    ABORTED                 = "ABORTED"
    ERROR                   = "ERROR"


@dataclass
class DatasetCandidate:
    name: str
    url: str
    description: str
    domain: str
    format: str
    estimated_mb: float
    quality_score: float
    source_tier: int
    reason: str
    selected: bool = True

    def to_dict(self):
        return asdict(self)


@dataclass
class AutoTrainSession:
    session_id: str
    state: AutoTrainState
    triggered_by: str
    trigger_reason: str
    candidates: List[DatasetCandidate] = field(default_factory=list)
    authorized_by: Optional[str] = None
    auth_timestamp: Optional[str] = None
    download_progress: Dict[str, Any] = field(default_factory=dict)
    training_step: int = 0
    training_loss: float = 0.0
    log_lines: List[str] = field(default_factory=list)
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    error: Optional[str] = None

    def log(self, msg: str):
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {msg}"
        self.log_lines.append(line)
        print(f"[AutonomousTrainer] {line}", flush=True)

    def to_dict(self):
        return {
            "session_id": self.session_id,
            "state": self.state.value,
            "triggered_by": self.triggered_by,
            "trigger_reason": self.trigger_reason,
            "candidates": [c.to_dict() for c in self.candidates],
            "authorized_by": self.authorized_by,
            "auth_timestamp": self.auth_timestamp,
            "download_progress": self.download_progress,
            "training_step": self.training_step,
            "training_loss": self.training_loss,
            "log_lines": self.log_lines[-100:],
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "error": self.error,
        }


VOID_CURATED_CATALOG = [
    {
        "name": "cybersecurity_trendyol",
        "url": "https://huggingface.co/datasets/ChavyvAkvar/Trendyol-Cybersecurity-Instruction-Tuning-Dataset-Converted/resolve/main/data/train-00000-of-00001.parquet",
        "description": "53,200 multi-turn cybersecurity instruction and defense dialogs",
        "domain": "cybersecurity",
        "format": "parquet_messages",
        "estimated_mb": 65.0,
        "quality_score": 0.94,
        "source_tier": 1,
        "reason": "Authoritative cybersecurity multi-turn instruction dataset covering MITRE ATT&CK, threat analysis, and defenses.",
    },
    {
        "name": "cybersecurity_alpaca",
        "url": "https://huggingface.co/datasets/ahmedds10/alpaca_Cybersecurity_json/resolve/main/alpaca_Cybersecurity.json",
        "description": "Alpaca-format cybersecurity prompts covering exploits, defense, CVE analysis",
        "domain": "cybersecurity",
        "format": "alpaca_json",
        "estimated_mb": 18.0,
        "quality_score": 0.88,
        "source_tier": 2,
        "reason": "Diverse pen-testing and vulnerability analysis prompts; complements Trendyol with CVE-specific examples.",
    },
    {
        "name": "code_alpaca_20k",
        "url": "https://raw.githubusercontent.com/sahil280114/codealpaca/master/data/code_alpaca_20k.json",
        "description": "20,000 clean algorithmic and practical code instructions",
        "domain": "coding",
        "format": "alpaca_json",
        "estimated_mb": 15.0,
        "quality_score": 0.92,
        "source_tier": 1,
        "reason": "Gold-standard small code corpus; high instruction-following signal across Python, JS, Bash.",
    },
    {
        "name": "code_instructions_122k",
        "url": "https://huggingface.co/datasets/TokenBender/code_instructions_122k_alpaca_style/resolve/main/code_instructions_120k.json",
        "description": "120,000 multi-language software engineering and systems coding pairs",
        "domain": "coding",
        "format": "alpaca_json",
        "estimated_mb": 95.0,
        "quality_score": 0.89,
        "source_tier": 1,
        "reason": "Large-scale multi-language coding corpus; significantly boosts algorithm and systems fluency.",
    },
    {
        "name": "python_code_18k",
        "url": "https://huggingface.co/datasets/iamtarun/python_code_instructions_18k_alpaca/resolve/main/data/train-00000-of-00001-4edd896bba6861e9.parquet",
        "description": "18,000 Python-specific instruction-code pairs from curated GitHub examples",
        "domain": "coding",
        "format": "parquet_messages",
        "estimated_mb": 22.0,
        "quality_score": 0.91,
        "source_tier": 1,
        "reason": "Pure Python focus; improves scripting, automation, and data structures competency.",
    },
    {
        "name": "ultrachat_200k_shard0",
        "url": "https://huggingface.co/datasets/HuggingFaceH4/ultrachat_200k/resolve/main/data/train_sft-00000-of-00003-a3ecf92756993583.parquet",
        "description": "69,000 rich multi-turn conversational fluency, reasoning, and instruction sessions",
        "domain": "language",
        "format": "parquet_messages",
        "estimated_mb": 120.0,
        "quality_score": 0.95,
        "source_tier": 1,
        "reason": "Highest quality multi-turn dialogue corpus; critical for natural language fluency and reasoning.",
    },
    {
        "name": "dolly_15k",
        "url": "https://huggingface.co/datasets/databricks/databricks-dolly-15k/resolve/main/databricks-dolly-15k.jsonl",
        "description": "15,000 human-written instruction-following samples by Databricks employees",
        "domain": "language",
        "format": "jsonl",
        "estimated_mb": 13.0,
        "quality_score": 0.93,
        "source_tier": 1,
        "reason": "Human-authored instruction quality; prevents model from over-relying on synthetic patterns.",
    },
]


class AutonomousTrainer:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.state = AutoTrainState.IDLE
        self.current_session: Optional[AutoTrainSession] = None
        self.session_history: List[Dict[str, Any]] = []
        self._training_thread: Optional[threading.Thread] = None
        self._abort_flag = threading.Event()
        self._sse_events: List[Dict[str, Any]] = []
        self._sse_lock = threading.Lock()
        self._state_file = os.path.join(
            os.path.dirname(__file__), "..", "training", ".auto_train_state.json"
        )
        self._load_state()

    def _load_state(self):
        try:
            if os.path.exists(self._state_file):
                with open(self._state_file, "r") as f:
                    data = json.load(f)
                    self.session_history = data.get("history", [])
        except Exception:
            pass

    def _save_state(self):
        try:
            os.makedirs(os.path.dirname(self._state_file), exist_ok=True)
            with open(self._state_file, "w") as f:
                json.dump({"last_updated": datetime.now().isoformat(),
                           "history": self.session_history[-20:]}, f, indent=2)
        except Exception:
            pass

    def _emit(self, event_type: str, data: Any):
        with self._sse_lock:
            self._sse_events.append({"type": event_type, "data": data, "ts": time.time()})

    def sse_stream(self):
        pointer = len(self._sse_events)
        yield f"data: {json.dumps({'type': 'connected', 'state': self.state.value})}\n\n"
        while True:
            with self._sse_lock:
                new_events = self._sse_events[pointer:]
                pointer = len(self._sse_events)
            for ev in new_events:
                yield f"data: {json.dumps(ev)}\n\n"
            if self.state in (AutoTrainState.COMPLETE, AutoTrainState.ABORTED, AutoTrainState.ERROR):
                break
            time.sleep(0.3)

    def get_status(self):
        return {
            "state": self.state.value,
            "session": self.current_session.to_dict() if self.current_session else None,
            "history_count": len(self.session_history),
            "catalog_size": len(VOID_CURATED_CATALOG),
            "history": self.session_history[-5:],
        }

    def request_full_auto(self, trigger_reason: str = "Scheduled self-improvement cycle"):
        with self._lock:
            if self.state not in (AutoTrainState.IDLE, AutoTrainState.COMPLETE,
                                   AutoTrainState.ABORTED, AutoTrainState.ERROR):
                return {"status": "error", "error": f"Cannot start. Current state: {self.state.value}"}
            self._abort_flag.clear()
            session_id = str(uuid.uuid4())[:8].upper()
            self.current_session = AutoTrainSession(
                session_id=session_id,
                state=AutoTrainState.SCOUTING,
                triggered_by="void_autonomous",
                trigger_reason=trigger_reason,
            )
            self.state = AutoTrainState.SCOUTING

        self._emit("state_change", {"state": "SCOUTING", "session_id": session_id})
        t = threading.Thread(target=self._scout_and_evaluate, daemon=True)
        t.start()
        return {
            "status": "started",
            "session_id": session_id,
            "message": "V.O.I.D. is scouting datasets. Will pause for admin authorization before any downloads.",
        }

    def authorize(self, admin_name: str = "Admin", selected_names: Optional[List[str]] = None):
        with self._lock:
            if self.state != AutoTrainState.AWAITING_AUTHORIZATION or not self.current_session:
                return {"status": "error", "error": "No pending authorization request."}
            if selected_names:
                for c in self.current_session.candidates:
                    c.selected = (c.name in selected_names)
            self.current_session.authorized_by = admin_name
            self.current_session.auth_timestamp = datetime.now().isoformat()
            self.current_session.state = AutoTrainState.AUTHORIZED
            self.state = AutoTrainState.AUTHORIZED
            self.current_session.log(f"AUTHORIZED by '{admin_name}'. Initiating download pipeline...")

        self._emit("authorized", {
            "admin": admin_name,
            "selected": [c.name for c in self.current_session.candidates if c.selected]
        })
        self._training_thread = threading.Thread(target=self._run_pipeline, daemon=True)
        self._training_thread.start()
        return {
            "status": "authorized",
            "message": "Authorization accepted. V.O.I.D. is now downloading and preparing training data.",
            "selected_datasets": [c.name for c in self.current_session.candidates if c.selected],
        }

    def abort(self):
        self._abort_flag.set()
        with self._lock:
            self.state = AutoTrainState.ABORTED
            if self.current_session:
                self.current_session.state = AutoTrainState.ABORTED
                self.current_session.log("ABORTED by admin.")
                self._archive_session()
        self._emit("aborted", {"reason": "Admin abort"})
        return {"status": "aborted"}

    def _scout_and_evaluate(self):
        session = self.current_session
        session.log("Scanning curated dataset catalog...")
        candidates = []
        for entry in VOID_CURATED_CATALOG:
            if self._abort_flag.is_set():
                break
            reachable = self._check_url_reachable(entry["url"])
            c = DatasetCandidate(**entry)
            c.selected = reachable
            candidates.append(c)
            status = "reachable" if reachable else "unreachable"
            session.log(f"  {'OK' if reachable else 'SKIP'} [{c.domain.upper()}] {c.name} ({status})")
            self._emit("scout_update", {"name": entry["name"], "reachable": reachable})

        if self._abort_flag.is_set():
            return

        selected = self._smart_select([c for c in candidates if c.selected], target_mb=1200.0)
        for c in candidates:
            if c.name not in {s.name for s in selected}:
                c.selected = False

        final = selected + [c for c in candidates if not c.selected]
        session.candidates = final

        total_mb = sum(c.estimated_mb for c in final if c.selected)
        session.log(f"Scouting complete. {len(selected)} datasets selected ({total_mb:.0f} MB estimated)")
        session.log("PAUSING - Awaiting admin authorization before any downloads begin.")

        with self._lock:
            self.state = AutoTrainState.AWAITING_AUTHORIZATION
            session.state = AutoTrainState.AWAITING_AUTHORIZATION

        self._emit("awaiting_authorization", {
            "session_id": session.session_id,
            "candidates": [c.to_dict() for c in final],
            "total_mb": total_mb,
            "message": "V.O.I.D. found high-quality datasets. Admin authorization required to proceed with downloads and training.",
        })

    def _check_url_reachable(self, url: str, timeout: float = 8.0) -> bool:
        try:
            r = requests.head(url, timeout=timeout, allow_redirects=True,
                              headers={"User-Agent": "Mozilla/5.0 (VOID/1.0)"})
            return r.status_code < 400
        except Exception:
            return True  # Optimistic: treat as reachable, fail at download

    def _smart_select(self, candidates: List[DatasetCandidate], target_mb: float) -> List[DatasetCandidate]:
        domain_pools: Dict[str, List[DatasetCandidate]] = {}
        for c in candidates:
            domain_pools.setdefault(c.domain, []).append(c)
        for d in domain_pools:
            domain_pools[d].sort(key=lambda x: x.quality_score, reverse=True)

        selected = []
        domains = list(domain_pools.keys())
        idx = 0
        cumulative_mb = 0.0
        while domains and cumulative_mb < target_mb:
            d = domains[idx % len(domains)]
            pool = domain_pools[d]
            if pool:
                pick = pool.pop(0)
                pick.selected = True
                selected.append(pick)
                cumulative_mb += pick.estimated_mb
            else:
                domains.remove(d)
                continue
            idx += 1
        return selected

    def _run_pipeline(self):
        session = self.current_session
        selected = [c for c in session.candidates if c.selected]

        with self._lock:
            self.state = AutoTrainState.DOWNLOADING
            session.state = AutoTrainState.DOWNLOADING
        session.log("Starting authorized downloads...")
        self._emit("state_change", {"state": "DOWNLOADING"})

        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        training_dir = os.path.join(project_root, "training")
        os.makedirs(training_dir, exist_ok=True)

        downloaded_files = []
        for c in selected:
            if self._abort_flag.is_set():
                break
            ext = "parquet" if "parquet" in c.format else ("jsonl" if c.format == "jsonl" else "json")
            dest = os.path.join(training_dir, f"auto_{c.name}.{ext}")
            success = self._download_file(c.url, dest, c.name, session)
            if success:
                downloaded_files.append((dest, c.format, c.name))

        if self._abort_flag.is_set():
            self._abort_pipeline()
            return

        if not downloaded_files:
            self._set_error("No datasets downloaded successfully.")
            return

        with self._lock:
            self.state = AutoTrainState.BUILDING_CORPUS
            session.state = AutoTrainState.BUILDING_CORPUS
        self._emit("state_change", {"state": "BUILDING_CORPUS"})
        corpus_path = os.path.join(training_dir, "train_void_auto.jsonl")
        written = self._build_corpus(downloaded_files, corpus_path, session)
        if written == 0:
            self._set_error("Corpus builder produced 0 entries.")
            return
        session.log(f"Corpus ready: {written:,} conversations -> {corpus_path}")

        if self._abort_flag.is_set():
            self._abort_pipeline()
            return

        with self._lock:
            self.state = AutoTrainState.TRAINING
            session.state = AutoTrainState.TRAINING
        self._emit("state_change", {"state": "TRAINING"})
        session.log("Launching transformer training...")

        checkpoint = os.path.join(project_root, "checkpoint.pt")
        script = os.path.join(project_root, "from_scratch_transformer.py")
        cmd = [sys.executable, script, "--data", corpus_path, "--epochs", "1",
               "--batch-size", "4", "--lr", "5e-5"]
        if os.path.exists(checkpoint):
            cmd.append("--resume")
        session.log(f"Command: {' '.join(cmd)}")

        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, cwd=project_root, encoding="utf-8", errors="replace")
            for line in proc.stdout:
                line = line.rstrip()
                if not line:
                    continue
                session.log(line)
                if "step" in line.lower() and "loss" in line.lower():
                    try:
                        parts = line.split()
                        for i, p in enumerate(parts):
                            if "step" in p.lower() and i + 1 < len(parts):
                                session.training_step = int(parts[i + 1].strip(","))
                            if "loss" in p.lower() and i + 1 < len(parts):
                                session.training_loss = float(parts[i + 1].strip(","))
                    except Exception:
                        pass
                    self._emit("training_progress", {
                        "step": session.training_step, "loss": session.training_loss, "log": line})
                if self._abort_flag.is_set():
                    proc.terminate()
                    self._abort_pipeline()
                    return
            proc.wait()
        except Exception as ex:
            self._set_error(f"Training subprocess error: {ex}")
            return

        with self._lock:
            self.state = AutoTrainState.COMPLETE
            session.state = AutoTrainState.COMPLETE
            session.completed_at = datetime.now().isoformat()
        session.log("Full Auto Training cycle complete!")
        self._archive_session()
        self._emit("complete", {"session_id": session.session_id})

    def _download_file(self, url: str, dest: str, name: str, session: AutoTrainSession) -> bool:
        if os.path.exists(dest):
            session.log(f"  {name}: Already cached, skipping download.")
            return True
        session.log(f"  {name}: Downloading...")
        self._emit("download_start", {"name": name})
        try:
            r = requests.get(url, stream=True, timeout=120,
                             headers={"User-Agent": "Mozilla/5.0 (VOID/1.0)"})
            r.raise_for_status()
            total = int(r.headers.get("content-length", 0))
            downloaded = 0
            with open(dest, "wb") as f:
                for chunk in r.iter_content(chunk_size=1024 * 256):
                    if self._abort_flag.is_set():
                        return False
                    f.write(chunk)
                    downloaded += len(chunk)
                    if total > 0:
                        pct = int(downloaded / total * 100)
                        session.download_progress[name] = pct
                        if pct % 10 == 0:
                            self._emit("download_progress", {"name": name, "pct": pct})
            session.log(f"  {name}: Done ({downloaded // 1024 // 1024} MB)")
            session.download_progress[name] = 100
            return True
        except Exception as ex:
            session.log(f"  {name}: FAILED - {ex}")
            return False

    def _build_corpus(self, files, output_path, session):
        count = 0
        try:
            import pandas as pd
            has_pd = True
        except ImportError:
            has_pd = False

        with open(output_path, "w", encoding="utf-8") as out:
            for (path, fmt, name) in files:
                if self._abort_flag.is_set():
                    break
                session.log(f"  Processing: {name} ({fmt})")
                try:
                    if fmt == "parquet_messages" and has_pd:
                        df = pd.read_parquet(path)
                        col = "messages" if "messages" in df.columns else ("conversations" if "conversations" in df.columns else None)
                        if col:
                            for msgs in df[col]:
                                if msgs is None:
                                    continue
                                valid = []
                                for m in msgs:
                                    if isinstance(m, dict) and m.get("content") and m.get("role"):
                                        role = "user" if m["role"] in ("user", "human") else "assistant"
                                        valid.append({"role": role, "content": str(m["content"]).strip()})
                                if len(valid) >= 2:
                                    out.write(json.dumps({"messages": valid}, ensure_ascii=False) + "\n")
                                    count += 1
                    elif fmt == "alpaca_json":
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            data = json.load(f)
                        for item in data:
                            instr = str(item.get("instruction", "")).strip()
                            inp = str(item.get("input", "")).strip()
                            resp = str(item.get("output", "")).strip()
                            if not instr or not resp:
                                continue
                            user_msg = f"{instr}\nContext: {inp}" if inp else instr
                            out.write(json.dumps({"messages": [
                                {"role": "user", "content": user_msg},
                                {"role": "assistant", "content": resp}
                            ]}, ensure_ascii=False) + "\n")
                            count += 1
                    elif fmt == "jsonl":
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            for line in f:
                                line = line.strip()
                                if not line:
                                    continue
                                obj = json.loads(line)
                                if "messages" in obj and len(obj["messages"]) >= 2:
                                    out.write(json.dumps(obj, ensure_ascii=False) + "\n")
                                    count += 1
                                elif "instruction" in obj and "output" in obj:
                                    instr = str(obj.get("instruction", "")).strip()
                                    resp = str(obj.get("output", "")).strip()
                                    if instr and resp:
                                        out.write(json.dumps({"messages": [
                                            {"role": "user", "content": instr},
                                            {"role": "assistant", "content": resp}
                                        ]}, ensure_ascii=False) + "\n")
                                        count += 1
                except Exception as ex:
                    session.log(f"  {name}: Build error - {ex}")
        return count

    def _abort_pipeline(self):
        with self._lock:
            self.state = AutoTrainState.ABORTED
            if self.current_session:
                self.current_session.state = AutoTrainState.ABORTED
                self.current_session.log("Pipeline aborted.")
                self._archive_session()
        self._emit("aborted", {"reason": "Abort flag"})

    def _set_error(self, msg: str):
        with self._lock:
            self.state = AutoTrainState.ERROR
            if self.current_session:
                self.current_session.state = AutoTrainState.ERROR
                self.current_session.error = msg
                self.current_session.log(f"ERROR: {msg}")
                self._archive_session()
        self._emit("error", {"error": msg})

    def _archive_session(self):
        if self.current_session:
            self.session_history.append(self.current_session.to_dict())
            self._save_state()


autonomous_trainer = AutonomousTrainer()
