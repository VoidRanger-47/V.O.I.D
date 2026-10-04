"""
void_cloud/cloud_manager.py
Host-Only Cloud Model Bridge & Lifecycle Manager for V.O.I.D.
Manages configuration, active provider dispatch, and graceful fallback.
"""

import os
import json
from typing import Dict, Any, Generator, Tuple, Optional

from void_cloud.gemini_client import GeminiClient
from void_cloud.ollama import ollama_manager


class CloudManager:
    _instance: Optional['CloudManager'] = None

    def __init__(self, config_path: Optional[str] = None):
        if config_path is None:
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
        self._init_client()

    @classmethod
    def get_instance(cls) -> 'CloudManager':
        if cls._instance is None:
            cls._instance = CloudManager()
        return cls._instance

    def _load_config(self) -> Dict[str, Any]:
        default_config = {
            "cloud_mode_enabled": False,
            "active_provider": "gemini",
            "api_key": "",
            "model_name": "gemini-3.6-flash",
            "temperature": 0.7,
            "max_tokens": 2048,
            "top_p": 0.95,
            "auto_fallback_to_local": True
        }
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    default_config.update(data)
            except Exception as e:
                print(f"[CloudManager] Error reading config: {e}")
        return default_config

    def save_config(self) -> bool:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2)
            self._init_client()
            return True
        except Exception as e:
            print(f"[CloudManager] Error saving config: {e}")
            return False

    def _init_client(self):
        api_key = self.config.get("api_key", "").strip()
        model = self.config.get("model_name", "gemini-2.0-flash")
        temp = float(self.config.get("temperature", 0.7))
        max_tok = int(self.config.get("max_tokens", 2048))
        top_p = float(self.config.get("top_p", 0.95))
        self.gemini_client = GeminiClient(
            api_key=api_key,
            model_name=model,
            temperature=temp,
            max_tokens=max_tok,
            top_p=top_p
        )

    def is_cloud_active(self) -> bool:
        """Returns True when cloud/external engine is enabled and provider is configured."""
        if not self.config.get("cloud_mode_enabled", False):
            return False
        provider = self.config.get("active_provider", "gemini").lower()
        if provider == "ollama":
            return ollama_manager.is_available()
        return self.gemini_client.is_configured()

    def get_status(self) -> Dict[str, Any]:
        provider = self.config.get("active_provider", "gemini").lower()
        if provider == "ollama":
            ollama_st = ollama_manager.get_status()
            return {
                "enabled": self.config.get("cloud_mode_enabled", False),
                "is_active": self.is_cloud_active(),
                "provider": "ollama",
                "model_name": ollama_st["active_model"],
                "server_running": ollama_st["server_running"],
                "host": ollama_st["host"],
                "installed_models": ollama_st["installed_models"],
                "temperature": ollama_st["temperature"],
                "num_ctx": ollama_st["num_ctx"],
                "auto_fallback": self.config.get("auto_fallback_to_local", True)
            }

        return {
            "enabled": self.config.get("cloud_mode_enabled", False),
            "is_active": self.is_cloud_active(),
            "provider": "gemini",
            "model_name": self.config.get("model_name", "gemini-2.0-flash"),
            "api_key_configured": bool(self.config.get("api_key")),
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 2048),
            "auto_fallback": self.config.get("auto_fallback_to_local", True)
        }

    def set_enabled(self, enabled: bool) -> bool:
        self.config["cloud_mode_enabled"] = bool(enabled)
        return self.save_config()

    def set_provider(self, provider: str) -> bool:
        clean = provider.strip().lower()
        if clean not in ("gemini", "ollama"):
            raise ValueError(f"Unsupported provider '{clean}'. Must be 'gemini' or 'ollama'.")
        self.config["active_provider"] = clean
        return self.save_config()

    def set_api_key(self, key: str) -> bool:
        self.config["api_key"] = key.strip()
        return self.save_config()

    def set_model(self, model_name: str) -> bool:
        clean = model_name.strip()
        self.config["model_name"] = clean
        provider = self.config.get("active_provider", "gemini").lower()
        if provider == "ollama":
            ollama_manager.set_model(clean)
        return self.save_config()

    def test_connection(self) -> Tuple[bool, str]:
        provider = self.config.get("active_provider", "gemini").lower()
        if provider == "ollama":
            return ollama_manager.test_connection()
        return self.gemini_client.test_connection()

    def stream_tokens(self, prompt: str) -> Generator[str, None, None]:
        """Streams tokens from active model (Gemini or Ollama)."""
        provider = self.config.get("active_provider", "gemini").lower()
        if provider == "ollama":
            yield from ollama_manager.stream_tokens(prompt)
            return

        if not self.is_cloud_active():
            raise RuntimeError("Cloud mode is not active or API key is not configured.")
        yield from self.gemini_client.stream_generate_tokens(prompt)


cloud_manager = CloudManager.get_instance()
