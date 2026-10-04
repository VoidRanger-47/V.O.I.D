# providers/manager.py
import os
import gc
import psutil
from typing import Dict, Any, Optional, List
import threading

from providers.base import BaseLLMProvider, ModelProvider
from providers.local_transformer import LocalTransformerProvider
from providers.local_gguf import LocalGGUFProvider
from core.vram_manager import vram_manager, VRAMThreshold

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    torch = None
    CUDA_AVAILABLE = False


class ModelManager:
    """
    Manages local models under strict hardware constraints (4 GB VRAM RTX 3050 / 16 GB RAM).
    Coordinates lazy loading, memory estimation, model offloading, and shared model instances.
    """
    _instance: Optional['ModelManager'] = None
    _lock = threading.Lock()

    def __init__(self, models_root: str = "models"):
        self.models_root = models_root
        self.loaded_models: Dict[str, BaseLLMProvider] = {}
        self.active_provider: Optional[BaseLLMProvider] = None
        self.device = "cuda" if CUDA_AVAILABLE else "cpu"
        self.vram_mgr = vram_manager
        self._ensure_models_directories()

    @classmethod
    def get_instance(cls) -> 'ModelManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = ModelManager()
        return cls._instance

    def _ensure_models_directories(self):
        """Ensures organized local model storage folders exist."""
        subdirs = ["language", "embedding", "vision", "speech", "tts"]
        for sub in subdirs:
            p = os.path.join(self.models_root, sub)
            os.makedirs(p, exist_ok=True)

    def discover_local_models(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scans models/ directory to catalog available offline models with sizes and capabilities.
        """
        discovered: Dict[str, List[Dict[str, Any]]] = {
            "language": [],
            "embedding": [],
            "vision": [],
            "speech": [],
            "tts": []
        }

        # Check root checkpoint
        if os.path.exists("checkpoint.pt"):
            try:
                sz_mb = round(os.path.getsize("checkpoint.pt") / (1024 * 1024), 2)
                discovered["language"].append({
                    "name": "checkpoint.pt (V.O.I.D. Native Transformer)",
                    "path": "checkpoint.pt",
                    "type": "pytorch_decoder",
                    "size_mb": sz_mb,
                    "recommended_device": "cuda" if sz_mb < 2500 else "cpu",
                    "quantization": "fp16/fp32",
                    "context_window": 512
                })
            except Exception:
                pass

        # Scan subdirectories
        for cat in ["language", "embedding", "vision", "speech", "tts"]:
            cat_dir = os.path.join(self.models_root, cat)
            if not os.path.exists(cat_dir):
                continue
            for root, _, files in os.walk(cat_dir):
                for f in files:
                    ext = os.path.splitext(f)[1].lower()
                    if ext in [".pt", ".bin", ".gguf", ".onnx", ".safetensors"]:
                        full_p = os.path.join(root, f)
                        try:
                            sz = round(os.path.getsize(full_p) / (1024 * 1024), 2)
                            discovered[cat].append({
                                "name": f,
                                "path": full_p,
                                "type": ext.replace(".", ""),
                                "size_mb": sz,
                                "recommended_device": "cuda" if sz < 2000 else "cpu",
                                "quantization": "q4_k_m" if "q4" in f.lower() else "standard"
                            })
                        except Exception:
                            pass

        return discovered

    def get_memory_stats(self) -> Dict[str, Any]:
        """Returns current system RAM and GPU VRAM telemetry from VRAMManager."""
        telemetry = self.vram_mgr.get_telemetry()
        return {
            "ram_used_gb": round(telemetry["host_ram_used_mb"] / 1024, 2),
            "ram_total_gb": round(telemetry["host_ram_total_mb"] / 1024, 2),
            "ram_percent": telemetry["host_ram_percent"],
            "gpu_available": telemetry["gpu_available"],
            "gpu_name": telemetry["gpu_name"],
            "device": self.device,
            "vram_allocated_gb": round(telemetry["used_vram_mb"] / 1024, 2),
            "vram_reserved_gb": round(telemetry["reserved_vram_mb"] / 1024, 2),
            "vram_total_gb": round(telemetry["total_vram_mb"] / 1024, 2),
            "vram_threshold": telemetry["threshold_state"]
        }

    def get_provider(
        self,
        provider_type: str = "local_transformer",
        model_path: Optional[str] = None
    ) -> BaseLLMProvider:
        """
        Get or lazy-initialize the requested local LLM provider.
        Shares single model instances to guarantee zero duplicate GPU memory allocations.
        """
        cache_key = f"{provider_type}_{model_path or 'default'}"

        with self._lock:
            # Check cached shared model instance
            if cache_key in self.loaded_models:
                provider = self.loaded_models[cache_key]
                self.active_provider = provider
                self.vram_mgr.touch_model(cache_key)
                return provider

            # Check if current active provider matches type
            if self.active_provider is not None:
                info = self.active_provider.get_info()
                if info.get("provider", "").lower() == provider_type.lower():
                    return self.active_provider

            # Check VRAM headroom before instantiating new GPU provider
            safe, msg = self.vram_mgr.is_safe_for_inference(estimated_mb=450.0)
            if not safe:
                print(f"⚠️ [ModelManager] VRAM pressure high: {msg}. Offloading unused models.")
                self.release_unused_models()

            if provider_type == "ollama":
                from providers.ollama_provider import OllamaProvider
                provider = OllamaProvider(model_path)
            elif provider_type == "local_gguf" and model_path and os.path.exists(model_path):
                provider = LocalGGUFProvider(model_path)
            else:
                provider = LocalTransformerProvider()

            self.loaded_models[cache_key] = provider
            self.active_provider = provider
            self.vram_mgr.register_model(cache_key, provider, estimated_vram_mb=450.0, device=self.device)

            return self.active_provider

    def get_active_provider(self) -> BaseLLMProvider:
        """
        Dynamically returns the active provider based on V.O.I.D. cloud/local configuration.
        Prioritizes Ollama when active, falling back to local transformer.
        """
        try:
            from void_cloud.cloud_manager import cloud_manager
            if cloud_manager.is_cloud_active():
                provider_name = cloud_manager.config.get("active_provider", "").lower()
                if provider_name == "ollama":
                    return self.get_provider("ollama")
        except Exception:
            pass
        return self.get_provider("local_transformer")

    def unload_active_model(self) -> bool:
        """Unloads active model and cleans VRAM."""
        with self._lock:
            if self.active_provider:
                if hasattr(self.active_provider, "unload"):
                    self.active_provider.unload()
                self.active_provider = None
            self.loaded_models.clear()
            self.release_unused_models()
            return True

    def release_unused_models(self):
        """Forces garbage collection and GPU memory cache clearing via VRAMManager."""
        self.vram_mgr.cleanup_vram(force=True)


model_manager = ModelManager.get_instance()
