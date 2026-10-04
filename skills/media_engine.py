"""
skills/media_engine.py
Skill Engine for V.O.I.D. Image Generation.
Bridges conversational natural language prompts and multi-agent directives to the offline image engine.
"""

import re
from typing import Dict, Any, Optional
from void_media.models import ImageRequest, ImageStylePreset
from void_media.engine import media_engine


class MediaSkillEngine:
    """
    Skill interface for handling image generation directives.
    """
    _instance: Optional['MediaSkillEngine'] = None

    def __init__(self):
        self.engine = media_engine

    @classmethod
    def get_instance(cls) -> 'MediaSkillEngine':
        if cls._instance is None:
            cls._instance = MediaSkillEngine()
        return cls._instance

    def parse_prompt(self, query: str) -> ImageRequest:
        """Extract clean prompt and style preset from conversational text."""
        text = query.strip()
        low = text.lower()

        # Detect style preset
        style = ImageStylePreset.NONE
        if "photorealistic" in low or "realistic photo" in low or "dslr" in low or "8k" in low:
            style = ImageStylePreset.PHOTOREALISTIC
        elif "cyberpunk" in low or "neon" in low:
            style = ImageStylePreset.CYBERPUNK
        elif "anime" in low or "manga" in low or "shinkai" in low:
            style = ImageStylePreset.ANIME
        elif "cinematic" in low or "movie still" in low or "film still" in low:
            style = ImageStylePreset.CINEMATIC
        elif "3d render" in low or "octane" in low or "unreal engine" in low:
            style = ImageStylePreset.THREE_D_RENDER
        elif "oil painting" in low or "canvas painting" in low or "impressionist" in low:
            style = ImageStylePreset.OIL_PAINTING
        elif "minimalist" in low or "vector" in low or "flat art" in low:
            style = ImageStylePreset.MINIMALIST

        # Strip command prefixes
        strip_patterns = [
            r"^(?:please\s+)?(?:can\s+you\s+)?(?:generate|create|render|draw|make|paint|produce)\s+(?:an?\s+)?(?:image|picture|photo|artwork|illustration|graphic|art)\s+(?:of\s+|about\s+|showing\s+)?",
            r"^(?:generate|create|render|draw|make)\s+(?:me\s+)?(?:an?\s+)?",
            r"^(?:draw|sketch|paint)\s+(?:an?\s+)?",
            r"^image\s+(?:of\s+|for\s+)?",
            r"^picture\s+(?:of\s+|for\s+)?"
        ]

        cleaned = text
        for pat in strip_patterns:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE).strip()

        if not cleaned:
            cleaned = text

        return ImageRequest(
            prompt=cleaned,
            style_preset=style,
            width=512,
            height=512
        )

    def handle_query(self, query: str) -> str:
        """Generates an image and formats a rich Markdown visual response."""
        request = self.parse_prompt(query)
        result = self.engine.generate_image(request)

        style_badge = f" | **Style**: `{request.style_preset.value.title()}`" if request.style_preset != ImageStylePreset.NONE else ""

        response = (
            f"🎨 **Offline Image Generated Successfully**\n\n"
            f"![{result.prompt}]({result.web_url})\n\n"
            f"• **Prompt**: *\"{result.prompt}\"*{style_badge}\n"
            f"• **Engine**: `{result.engine}` (100% Offline)\n"
            f"• **Resolution**: {result.width}×{result.height}px | **Seed**: `{result.seed}`\n"
            f"• **Generation Latency**: {result.generation_time_sec:.2f}s\n"
            f"• 📥 [Download Image PNG]({result.web_url}) • 🖼️ [View in Studio Gallery](#image-studio-modal)"
        )
        return response


# Global Singleton Instance
media_skill_engine = MediaSkillEngine.get_instance()
