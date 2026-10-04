# providers/base.py
from abc import ABC, abstractmethod
from typing import Generator, Dict, Any, Optional

class BaseLLMProvider(ABC):
    """
    Abstract interface for LOCAL language model providers in V.O.I.D.
    Strictly local, private execution without external network dependencies.
    """
    @abstractmethod
    def generate(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7, **kwargs) -> str:
        """Generate complete text response locally."""
        pass

    @abstractmethod
    def generate_stream(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7, **kwargs) -> Generator[str, None, None]:
        """Stream generated text tokens locally in real time."""
        pass

    @abstractmethod
    def get_info(self) -> Dict[str, Any]:
        """Return metadata about the local model."""
        pass

    def count_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        # Standard heuristic ~4 characters per token
        return max(1, len(text) // 4)

    def estimate_memory(self) -> float:
        """Estimate VRAM/RAM requirement in MB."""
        return 450.0

    def load(self) -> bool:
        """Explicitly load model into memory if lazy."""
        return True

    def unload(self) -> bool:
        """Explicitly unload model from memory to free VRAM."""
        return True

    def health_check(self) -> bool:
        """Check if model provider is ready for inference."""
        return True

# Canonical alias
ModelProvider = BaseLLMProvider
