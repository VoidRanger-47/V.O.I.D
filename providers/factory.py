# providers/factory.py
import os
from providers.base import BaseLLMProvider
from providers.local_transformer import LocalTransformerProvider
from providers.local_gguf import LocalGGUFProvider

class LLMFactory:
    """
    Factory for instantiating LOCAL, OFFLINE LLM Providers only.
    Cloud providers (Gemini, OpenAI, Anthropic) are strictly excluded from the core loop.
    """
    _instance: BaseLLMProvider = None

    @classmethod
    def get_provider(cls, provider_type: str = "local_transformer", gguf_path: str = None) -> BaseLLMProvider:
        if cls._instance is not None:
            return cls._instance

        if provider_type == "ollama":
            from providers.ollama_provider import OllamaProvider
            cls._instance = OllamaProvider()
        elif provider_type == "local_gguf" and gguf_path and os.path.exists(gguf_path):
            cls._instance = LocalGGUFProvider(gguf_path)
        else:
            # Default: Local PyTorch Transformer (checkpoint.pt)
            cls._instance = LocalTransformerProvider()

        return cls._instance
