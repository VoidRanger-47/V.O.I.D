"""
void_cloud/ollama/manager.py
Lifecycle & Orchestration Manager for Offline Ollama LLM Engine in V.O.I.D.
Provides auto-discovery of local models, graceful fallback, and unified dispatch.
"""

import os
from typing import Dict, Any, Generator, List, Tuple, Optional

from void_cloud.ollama.config import OllamaConfig
from void_cloud.ollama.client import OllamaClient


class OllamaOfflineManager:
    _instance: Optional['OllamaOfflineManager'] = None

    def __init__(self, config_path: Optional[str] = None):
        self.config = OllamaConfig(config_path)
        self.client: OllamaClient = self._build_client()
        self._auto_discover_model()

    @classmethod
    def get_instance(cls) -> 'OllamaOfflineManager':
        if cls._instance is None:
            cls._instance = OllamaOfflineManager()
        return cls._instance

    def _build_client(self) -> OllamaClient:
        return OllamaClient(
            host=self.config.host,
            model=self.config.model,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.get("top_k", 40),
            num_ctx=self.config.num_ctx,
            keep_alive=self.config.keep_alive,
            timeout=self.config.timeout,
            system_prompt=self.config.system_prompt
        )

    def _auto_discover_model(self) -> None:
        """
        If auto-discovery is enabled and the configured model is missing,
        checks if any alternative model is already pulled locally.
        """
        if not self.config.get("auto_discover", True):
            return

        if not self.client.is_server_available():
            return

        installed = self.client.list_model_names()
        if not installed:
            return

        # If current model already present, we're good
        if self.client.has_model(self.config.model):
            return

        # Try fallback candidates first
        fallbacks = self.config.get("fallback_models", [])
        for candidate in fallbacks:
            if self.client.has_model(candidate):
                print(f"[OllamaManager] Configured model '{self.config.model}' not found. "
                      f"Auto-selected installed fallback: '{candidate}'")
                self.set_model(candidate)
                return

        # Pick first available model
        first_available = installed[0].split(":")[0]
        print(f"[OllamaManager] Auto-selected first available local model: '{first_available}'")
        self.set_model(first_available)

    def is_available(self) -> bool:
        """Returns True if the Ollama service is reachable and has the active model."""
        return (
            self.config.get("enabled", True) and
            self.client.is_server_available() and
            self.client.has_model()
        )

    def get_status(self) -> Dict[str, Any]:
        """Returns full diagnostic status for dashboard and CLI."""
        server_ok = self.client.is_server_available()
        models = self.client.list_model_names() if server_ok else []
        has_active = self.client.has_model() if server_ok else False

        return {
            "enabled": self.config.get("enabled", True),
            "is_available": self.is_available(),
            "server_running": server_ok,
            "host": self.config.host,
            "active_model": self.config.model,
            "has_active_model": has_active,
            "installed_models": models,
            "temperature": self.config.temperature,
            "top_p": self.config.top_p,
            "num_ctx": self.config.num_ctx,
            "keep_alive": self.config.keep_alive
        }

    def set_enabled(self, enabled: bool) -> bool:
        res = self.config.set("enabled", bool(enabled))
        self.client = self._build_client()
        return res

    def set_model(self, model_name: str) -> bool:
        clean = model_name.strip()
        res = self.config.set("model", clean)
        self.client = self._build_client()
        return res

    def set_host(self, host_url: str) -> bool:
        clean = host_url.strip()
        res = self.config.set("host", clean)
        self.client = self._build_client()
        return res

    def set_system_prompt(self, prompt: str) -> bool:
        res = self.config.set("system_prompt", prompt.strip())
        self.client = self._build_client()
        return res

    def test_connection(self) -> Tuple[bool, str]:
        return self.client.test_connection()

    def stream_tokens(
        self,
        prompt: str,
        system_prompt: Optional[str] = None
    ) -> Generator[str, None, None]:
        """
        Main entrypoint: Streams response tokens in real-time from the offline Ollama model.
        """
        if not self.config.get("enabled", True):
            raise RuntimeError("Ollama offline engine is disabled in configuration.")

        yield from self.client.stream_generate_tokens(prompt, system_prompt=system_prompt)

    def generate(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """Non-streaming complete generation."""
        return self.client.generate(prompt, system_prompt=system_prompt)

    def pull_model(self, model_name: str) -> Generator[Dict[str, Any], None, None]:
        """Pulls a new model to local storage."""
        yield from self.client.pull_model(model_name)


ollama_manager = OllamaOfflineManager.get_instance()
