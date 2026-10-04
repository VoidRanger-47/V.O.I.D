"""
void_media/models.py
Data models and schemas for the V.O.I.D. Offline Image Generation Engine.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional, List


class ImageStylePreset(str, Enum):
    PHOTOREALISTIC = "photorealistic"
    CYBERPUNK = "cyberpunk"
    ANIME = "anime"
    CINEMATIC = "cinematic"
    THREE_D_RENDER = "3d_render"
    OIL_PAINTING = "oil_painting"
    MINIMALIST = "minimalist"
    NONE = "none"


STYLE_PROMPT_PREFIXES = {
    ImageStylePreset.PHOTOREALISTIC: "masterpiece, ultra-photorealistic, high dynamic range, sharp focus, 8k resolution, raw photography, natural lighting: ",
    ImageStylePreset.CYBERPUNK: "cyberpunk aesthetic, neon glow, holographic interfaces, futuristic city, dark rain-slicked atmosphere, octane render: ",
    ImageStylePreset.ANIME: "modern high-end anime concept art, Makoto Shinkai aesthetic, detailed background, crisp lines, vibrant digital painting: ",
    ImageStylePreset.CINEMATIC: "cinematic film still, 35mm photograph, anamorphic lens flare, dramatic lighting, depth of field, color graded: ",
    ImageStylePreset.THREE_D_RENDER: "octane 3D render, raytracing, subsurface scattering, Blender Cycles, clean reflections, volumetric light: ",
    ImageStylePreset.OIL_PAINTING: "rich classical oil painting, textured canvas, visible brushstrokes, dynamic impasto, Rembrandt lighting: ",
    ImageStylePreset.MINIMALIST: "minimalist vector art, clean geometry, negative space, elegant palette, contemporary poster design: ",
    ImageStylePreset.NONE: ""
}


@dataclass
class ImageRequest:
    prompt: str
    negative_prompt: str = "blurry, low quality, distorted, deformed, watermark, signature, artifacts, ugly"
    width: int = 512
    height: int = 512
    steps: int = 4
    guidance_scale: float = 1.8
    seed: Optional[int] = None
    style_preset: ImageStylePreset = ImageStylePreset.NONE

    def get_effective_prompt(self) -> str:
        """Appends stylistic prefixes if specified."""
        prefix = STYLE_PROMPT_PREFIXES.get(self.style_preset, "")
        return f"{prefix}{self.prompt}".strip()


@dataclass
class ImageResult:
    image_id: str
    file_path: str
    web_url: str
    prompt: str
    seed: int
    generation_time_sec: float
    timestamp: float
    width: int
    height: int
    size_bytes: int
    engine: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "file_path": self.file_path,
            "web_url": self.web_url,
            "prompt": self.prompt,
            "seed": self.seed,
            "generation_time_sec": round(self.generation_time_sec, 2),
            "timestamp": self.timestamp,
            "width": self.width,
            "height": self.height,
            "size_bytes": self.size_bytes,
            "engine": self.engine,
            "metadata": self.metadata
        }


@dataclass
class GalleryItem:
    image_id: str
    prompt: str
    web_url: str
    file_path: str
    timestamp: float
    size_bytes: int
    width: int
    height: int
    engine: str
    seed: int
    expires_at: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_id": self.image_id,
            "prompt": self.prompt,
            "web_url": self.web_url,
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "size_bytes": self.size_bytes,
            "width": self.width,
            "height": self.height,
            "engine": self.engine,
            "seed": self.seed,
            "expires_at": self.expires_at
        }
