"""
void_cloud/ollama/config.py
Configuration and settings persistence for V.O.I.D. Ollama Offline Engine.
"""

import os
import json
from typing import Dict, Any, Optional

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": True,
    "host": "http://localhost:11434",
    "model": "llama3.2",
    "fallback_models": ["llama3.2:1b", "mistral", "qwen2.5:7b", "deepseek-r1:8b", "phi3"],
    "temperature": 0.7,
    "top_p": 0.9,
    "top_k": 40,
    "num_ctx": 4096,
    "keep_alive": "5m",
    "timeout": 90,
    "system_prompt": (
        "You are V.O.I.D. (Virtual Operator of Information and Development), "
        "an autonomous, local-first cognitive AI assistant. "
        "You provide direct, highly capable, and accurate responses."
    ),
    "auto_discover": True,
    "auto_start_daemon": True
}


class OllamaConfig:
    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.config_path = config_path
        self._data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        config = dict(DEFAULT_CONFIG)
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        config.update(data)
            except Exception as e:
                print(f"[OllamaConfig] Warning: Failed to load config from {self.config_path}: {e}")
        return config

    def save(self) -> bool:
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
            return True
        except Exception as e:
            print(f"[OllamaConfig] Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        self._data[key] = value
        return self.save()

    def update(self, updates: Dict[str, Any]) -> bool:
        self._data.update(updates)
        return self.save()

    @property
    def host(self) -> str:
        # Check environment variable first (standard Ollama convention)
        return os.environ.get("OLLAMA_HOST") or self._data.get("host", "http://localhost:11434")

    @property
    def model(self) -> str:
        return self._data.get("model", "llama3.2")

    @property
    def temperature(self) -> float:
        return float(self._data.get("temperature", 0.7))

    @property
    def top_p(self) -> float:
        return float(self._data.get("top_p", 0.9))

    @property
    def num_ctx(self) -> int:
        return int(self._data.get("num_ctx", 4096))

    @property
    def keep_alive(self) -> str:
        return str(self._data.get("keep_alive", "5m"))

    @property
    def timeout(self) -> int:
        return int(self._data.get("timeout", 90))

    @property
    def system_prompt(self) -> str:
        return self._data.get("system_prompt", DEFAULT_CONFIG["system_prompt"])

    def to_dict(self) -> Dict[str, Any]:
        return dict(self._data)
