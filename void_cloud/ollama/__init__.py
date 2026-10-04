"""
void_cloud/ollama
Offline LLM Engine package for V.O.I.D. powered by Ollama.
Supports local streaming, multi-turn chat, model pull, and auto-discovery.
"""

from void_cloud.ollama.client import OllamaClient
from void_cloud.ollama.config import OllamaConfig
from void_cloud.ollama.manager import OllamaOfflineManager, ollama_manager

__all__ = [
    "OllamaClient",
    "OllamaConfig",
    "OllamaOfflineManager",
    "ollama_manager",
]
