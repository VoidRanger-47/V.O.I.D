# core/audit_logger.py
import json
import os
import time
from datetime import datetime
from typing import Dict, Any, Optional

class AuditLogger:
    """
    Structured security and operational audit logger for V.O.I.D.
    Records timestamp, task_id, event, tool, status, duration, error, and result summary.
    Never logs credentials or private data.
    """
    _instance: Optional['AuditLogger'] = None

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = log_dir
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_file = os.path.join(self.log_dir, "void_audit.jsonl")

    @classmethod
    def get_instance(cls) -> 'AuditLogger':
        if cls._instance is None:
            cls._instance = AuditLogger()
        return cls._instance

    def log(
        self,
        event: str,
        tool: Optional[str] = None,
        status: str = "SUCCESS",
        task_id: Optional[str] = None,
        duration: Optional[float] = None,
        error: Optional[str] = None,
        result_summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "time_epoch": time.time(),
            "event": event,
            "tool": tool,
            "status": status,
            "task_id": task_id,
            "duration_s": duration,
            "error": error,
            "result_summary": result_summary[:200] if result_summary else None,
            "metadata": metadata or {}
        }

        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception as e:
            print(f"⚠️ AuditLog write failed: {e}")

audit_logger = AuditLogger.get_instance()
