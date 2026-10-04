# providers/local_gguf.py
import os
from typing import Generator, Dict, Any
from providers.base import BaseLLMProvider

class LocalGGUFProvider(BaseLLMProvider):
    """
    Local GGUF llama.cpp provider for V.O.I.D.
    Allows running local quantized GGUF models offline if llama-cpp-python is installed.
    """
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self.llm = None
        self.is_ready = False
        
        if model_path and os.path.exists(model_path):
            try:
                from llama_cpp import Llama
                self.llm = Llama(model_path=model_path, n_ctx=2048, verbose=False)
                self.is_ready = True
            except Exception as e:
                print(f"⚠️  LocalGGUFProvider load failed: {e}")

    def generate(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7, **kwargs) -> str:
        if not self.is_ready or not self.llm:
            return "[Local GGUF Model Unavailable]"
        response = self.llm(prompt, max_tokens=max_new_tokens, temperature=temperature)
        return response['choices'][0]['text'].strip()

    def generate_stream(self, prompt: str, max_new_tokens: int = 150, temperature: float = 0.7, **kwargs) -> Generator[str, None, None]:
        if not self.is_ready or not self.llm:
            yield "[Local GGUF Model Unavailable]"
            return
        stream = self.llm(prompt, max_tokens=max_new_tokens, temperature=temperature, stream=True)
        for output in stream:
            token = output['choices'][0]['text']
            yield token

    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": "LocalGGUF",
            "type": "Local llama.cpp GGUF Model",
            "offline": True,
            "path": self.model_path or "Not configured"
        }
