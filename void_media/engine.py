"""
void_media/engine.py
Central Coordinator for V.O.I.D. Offline Image Generation.
Provides a unified API for chat, skills, autonomous agents, and web endpoints.
"""

import time
import logging
from typing import Dict, Any, Optional

from void_media.models import ImageRequest, ImageResult, ImageStylePreset
from void_media.storage import MediaStorageManager
from void_media.offline_diffusion_engine import OfflineImageEngine

logger = logging.getLogger("void.media.engine")


class MediaEngine:
    """
    Main API interface for V.O.I.D. Offline Image Generation.
    """
    _instance: Optional['MediaEngine'] = None

    def __init__(self):
        self.storage = MediaStorageManager.get_instance()
        self.generator = OfflineImageEngine.get_instance()
        logger.info("MediaEngine initialized for 100% offline image generation.")

    @classmethod
    def get_instance(cls) -> 'MediaEngine':
        if cls._instance is None:
            cls._instance = MediaEngine()
        return cls._instance

    def generate_image(self, request: ImageRequest) -> ImageResult:
        """
        Executes local generation and saves the result with metadata and auto-purge tracking.
        """
        start_t = time.time()
        logger.info(f"MediaEngine: Generating image for prompt: '{request.prompt[:50]}...'")

        # Generate image offline
        pil_image, engine_name = self.generator.generate(request)
        duration = time.time() - start_t

        seed = request.seed if request.seed is not None else 42

        # Save to disk and update manifest
        result = self.storage.save_image(
            image=pil_image,
            prompt=request.prompt,
            seed=seed,
            generation_time_sec=duration,
            engine=engine_name,
            metadata={
                "style_preset": request.style_preset.value,
                "negative_prompt": request.negative_prompt,
                "steps": request.steps,
                "guidance_scale": request.guidance_scale
            }
        )

        logger.info(f"MediaEngine: Image generation complete in {duration:.2f}s -> {result.web_url}")
        return result

    def get_gallery(self, limit: int = 50, offset: int = 0, query: Optional[str] = None) -> Dict[str, Any]:
        """Returns gallery items."""
        return self.storage.get_gallery(limit=limit, offset=offset, query=query)

    def delete_image(self, image_id: str) -> bool:
        """Deletes an image by ID."""
        return self.storage.delete_image(image_id)

    def get_settings(self) -> Dict[str, Any]:
        """Returns current media settings (e.g. retention_days)."""
        return self.storage.get_settings()

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Updates media settings."""
        return self.storage.update_settings(updates)

    def trigger_auto_purge(self) -> int:
        """Manually trigger auto-purge."""
        return self.storage.auto_purge()

    def get_telemetry(self) -> Dict[str, Any]:
        """Returns engine and hardware telemetry."""
        gen_telem = self.generator.get_telemetry()
        settings = self.storage.get_settings()
        gallery_info = self.storage.get_gallery(limit=1)
        return {
            **gen_telem,
            "total_images": gallery_info["total"],
            "retention_days": settings.get("retention_days", 7),
            "auto_purge_enabled": settings.get("auto_purge_enabled", True)
        }


# Global Singleton Instance
media_engine = MediaEngine.get_instance()
