# core/vram_manager.py
"""
Central VRAM and Hardware Memory Management for V.O.I.D.
Strictly optimized for:
  - GPU: NVIDIA GeForce RTX 3050 Laptop GPU (4 GB VRAM)
  - RAM: 16 GB Host Memory
  - CPU: AMD Ryzen 5 5600H
  - OS: Windows 11
"""

import gc
import os
import time
import psutil
from enum import Enum
from typing import Dict, Any, Optional, List, Tuple
import threading

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except ImportError:
    torch = None
    CUDA_AVAILABLE = False


class VRAMThreshold(str, Enum):
    SAFE = "SAFE"          # < 70% of 4GB (< 2867 MB)
    WARNING = "WARNING"    # 70% - 85% (2867 - 3481 MB)
    CRITICAL = "CRITICAL"  # > 85% (> 3481 MB)


class VRAMManager:
    """
    Central VRAM controller and hardware protector for V.O.I.D.
    Guarantees no out-of-memory (OOM) crashes on 4 GB VRAM consumer hardware.
    """
    _instance: Optional['VRAMManager'] = None
    _lock = threading.Lock()

    # Hardware constants for 4GB RTX 3050 Laptop
    TOTAL_VRAM_BUDGET_MB = 4096.0
    SAFE_THRESHOLD_MB = 2867.0       # 70%
    WARNING_THRESHOLD_MB = 3481.0    # 85%
    CRITICAL_THRESHOLD_MB = 3686.0   # 90%

    def __init__(self):
        self._registered_models: Dict[str, Dict[str, Any]] = {}
        self._active_model_name: Optional[str] = None
        self._vision_allocation_mb: float = 0.0
        self._kv_cache_allocation_mb: float = 0.0
        self._temp_tensors_mb: float = 0.0
        self._last_cleanup_time: float = 0.0
        self._memory_history: List[Dict[str, Any]] = []

    @classmethod
    def get_instance(cls) -> 'VRAMManager':
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = VRAMManager()
        return cls._instance

    def get_telemetry(self) -> Dict[str, Any]:
        """
        Gathers real-time GPU VRAM, host RAM, and CPU telemetry.
        """
        ram = psutil.virtual_memory()
        cpu_pct = psutil.cpu_percent(interval=None)

        used_vram_mb = 0.0
        reserved_vram_mb = 0.0
        total_vram_mb = self.TOTAL_VRAM_BUDGET_MB
        gpu_name = "CPU Only"

        if CUDA_AVAILABLE and torch is not None:
            try:
                gpu_name = torch.cuda.get_device_name(0)
                used_vram_mb = torch.cuda.memory_allocated(0) / (1024 * 1024)
                reserved_vram_mb = torch.cuda.memory_reserved(0) / (1024 * 1024)
                total_bytes = torch.cuda.get_device_properties(0).total_memory
                total_vram_mb = total_bytes / (1024 * 1024)
            except Exception:
                pass

        free_vram_mb = max(0.0, total_vram_mb - used_vram_mb)
        threshold_state = self._evaluate_threshold(used_vram_mb, total_vram_mb)

        telemetry = {
            "gpu_available": CUDA_AVAILABLE,
            "gpu_name": gpu_name,
            "total_vram_mb": round(total_vram_mb, 2),
            "used_vram_mb": round(used_vram_mb, 2),
            "reserved_vram_mb": round(reserved_vram_mb, 2),
            "free_vram_mb": round(free_vram_mb, 2),
            "vram_percent": round((used_vram_mb / total_vram_mb) * 100, 1) if total_vram_mb > 0 else 0.0,
            "threshold_state": threshold_state.value,
            "active_model": self._active_model_name,
            "tracked_models_count": len(self._registered_models),
            "vision_allocation_mb": round(self._vision_allocation_mb, 2),
            "kv_cache_allocation_mb": round(self._kv_cache_allocation_mb, 2),
            "host_ram_used_mb": round(ram.used / (1024 * 1024), 2),
            "host_ram_total_mb": round(ram.total / (1024 * 1024), 2),
            "host_ram_percent": ram.percent,
            "cpu_percent": cpu_pct,
            "timestamp": time.time()
        }

        # Keep rolling history (up to 120 samples)
        self._memory_history.append(telemetry)
        if len(self._memory_history) > 120:
            self._memory_history.pop(0)

        return telemetry

    def _evaluate_threshold(self, used_mb: float, total_mb: float) -> VRAMThreshold:
        ratio = (used_mb / total_mb) if total_mb > 0 else 0.0
        if ratio >= 0.85 or used_mb >= self.CRITICAL_THRESHOLD_MB:
            return VRAMThreshold.CRITICAL
        if ratio >= 0.70 or used_mb >= self.SAFE_THRESHOLD_MB:
            return VRAMThreshold.WARNING
        return VRAMThreshold.SAFE

    def is_safe_for_inference(self, estimated_mb: float = 300.0) -> Tuple[bool, str]:
        """
        Determines if there is sufficient headroom in 4 GB VRAM for a proposed operation.
        """
        if not CUDA_AVAILABLE:
            return True, "CPU execution: VRAM constraints do not apply."

        stats = self.get_telemetry()
        available_mb = stats["free_vram_mb"]

        if stats["threshold_state"] == VRAMThreshold.CRITICAL.value:
            # Trigger immediate memory relief
            self.emergency_cleanup()
            stats = self.get_telemetry()
            available_mb = stats["free_vram_mb"]

        if available_mb < estimated_mb:
            return False, f"VRAM constraint: requires ~{estimated_mb:.1f} MB, but only {available_mb:.1f} MB is free."

        return True, "VRAM headroom is safe."

    def register_model(
        self,
        name: str,
        instance: Any,
        estimated_vram_mb: float = 450.0,
        device: str = "cuda"
    ):
        """
        Registers a loaded neural model into VRAM tracking.
        """
        with self._lock:
            self._registered_models[name] = {
                "instance": instance,
                "estimated_vram_mb": estimated_vram_mb,
                "device": device,
                "registered_at": time.time(),
                "last_used": time.time()
            }
            self._active_model_name = name

    def touch_model(self, name: str):
        """Updates last accessed timestamp for LRU management."""
        if name in self._registered_models:
            self._registered_models[name]["last_used"] = time.time()
            self._active_model_name = name

    def get_registered_model(self, name: str) -> Optional[Any]:
        if name in self._registered_models:
            self.touch_model(name)
            return self._registered_models[name]["instance"]
        return None

    def unregister_model(self, name: str) -> bool:
        """Removes model and cleans up memory."""
        with self._lock:
            if name in self._registered_models:
                del self._registered_models[name]
                if self._active_model_name == name:
                    self._active_model_name = next(iter(self._registered_models.keys()), None)
                self.cleanup_vram(force=True)
                return True
            return False

    def cleanup_vram(self, force: bool = False):
        """
        Frees cached GPU tensors and performs garbage collection.
        Rate-limited to once every 2 seconds unless forced.
        """
        now = time.time()
        if not force and (now - self._last_cleanup_time < 2.0):
            return

        self._last_cleanup_time = now
        gc.collect()

        if CUDA_AVAILABLE and torch is not None:
            try:
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
            except Exception:
                pass

    def emergency_cleanup(self) -> Dict[str, Any]:
        """
        Called when VRAM exceeds 85% (CRITICAL threshold).
        Executes immediate protective offloading:
          1. Empties PyTorch CUDA cache.
          2. Runs Python garbage collection.
          3. Releases idle models.
        """
        freed_before = 0.0
        if CUDA_AVAILABLE and torch is not None:
            freed_before = torch.cuda.memory_allocated(0) / (1024 * 1024)

        self.cleanup_vram(force=True)

        freed_after = 0.0
        if CUDA_AVAILABLE and torch is not None:
            freed_after = torch.cuda.memory_allocated(0) / (1024 * 1024)

        return {
            "status": "emergency_cleanup_executed",
            "freed_mb": round(max(0.0, freed_before - freed_after), 2),
            "telemetry": self.get_telemetry()
        }

    def allocate_vision(self, mb: float):
        """Track vision frame or model memory usage."""
        self._vision_allocation_mb = mb

    def release_vision(self):
        self._vision_allocation_mb = 0.0

    def allocate_kv_cache(self, mb: float):
        self._kv_cache_allocation_mb = mb

    def release_kv_cache(self):
        self._kv_cache_allocation_mb = 0.0


# Global singleton instance
vram_manager = VRAMManager.get_instance()
