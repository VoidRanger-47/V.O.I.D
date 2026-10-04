# providers/ollama_provider.py
"""
Dedicated Offline Ollama Model Provider for V.O.I.D.
Provides seamless integration with local Ollama daemon (e.g. LLaMA 3.2, DeepSeek-R1, Mistral, Qwen).
Runs 100% locally and privately, exposed to Web and Android clients.
"""

from typing import Generator, Dict, Any, Optional
from providers.base import BaseLLMProvider
from void_cloud.ollama import ollama_manager


class OllamaProvider(BaseLLMProvider):
    """
    Offline Ollama Provider implementing the standard V.O.I.D. BaseLLMProvider interface.
    """
    def __init__(self, model_name: Optional[str] = None):
        self.manager = ollama_manager
        if model_name:
            self.manager.set_model(model_name)

    def generate(
        self,
        prompt: str,
        max_new_tokens: int = 250,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """Generates a complete response synchronously using the local Ollama daemon."""
        if not self.manager.is_available():
            # Graceful fallback or informational status
            status = self.manager.get_status()
            if not status.get("server_running"):
                return "[Ollama Offline: Local daemon is not running at localhost:11434. Please start Ollama.]"
            return f"[Ollama Offline: Configured model '{self.manager.config.model}' is not available.]"

        return self.manager.generate(prompt)

    def generate_stream(
        self,
        prompt: str,
        max_new_tokens: int = 250,
        temperature: float = 0.7,
        **kwargs
    ) -> Generator[str, None, None]:
        """Streams tokens in real time directly from local Ollama."""
        if not self.manager.is_available():
            status = self.manager.get_status()
            if not status.get("server_running"):
                yield "[Ollama Offline: Local daemon is not running at localhost:11434.]"
                return
            yield f"[Ollama Offline: Model '{self.manager.config.model}' is not downloaded.]"
            return

        yield from self.manager.stream_tokens(prompt)

    def get_info(self) -> Dict[str, Any]:
        st = self.manager.get_status()
        return {
            "provider": "Ollama",
            "type": "Offline Ollama LLM Engine",
            "offline": True,
            "host": st.get("host", "http://localhost:11434"),
            "model": st.get("active_model", "llama3.2"),
            "is_available": st.get("is_available", False),
            "server_running": st.get("server_running", False),
            "installed_models": st.get("installed_models", [])
        }

    def get_status(self) -> Dict[str, Any]:
        return self.get_info()

    def health_check(self) -> bool:
        return self.manager.is_available()

    def estimate_memory(self) -> float:
        # Ollama manages its own VRAM outside Python process
        return 0.0
