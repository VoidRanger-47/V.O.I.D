"""
void_media/storage.py
Storage manager for V.O.I.D. generated images.
Handles filesystem persistence, manifest indexing, and configurable auto-purging.
"""

import os
import json
import time
import uuid
import logging
from typing import Dict, Any, List, Optional
from PIL import Image

from void_media.models import ImageResult, GalleryItem

logger = logging.getLogger("void.media.storage")


class MediaStorageManager:
    """
    Manages local image artifacts in static/generated/images and their persistent metadata.
    Enforces configurable auto-purge retention policies (default: 7 days).
    """
    _instance: Optional['MediaStorageManager'] = None

    def __init__(self, base_dir: Optional[str] = None, storage_dir: Optional[str] = None, manifest_path: Optional[str] = None):
        if base_dir is None:
            # Root directory of VOID
            base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        self.base_dir = base_dir

        self.images_dir = storage_dir if storage_dir else os.path.join(self.base_dir, "static", "generated", "images")
        self.data_dir = os.path.join(self.base_dir, "data")
        self.manifest_path = manifest_path if manifest_path else os.path.join(self.data_dir, "media_gallery.json")
        self.settings_path = os.path.join(self.data_dir, "media_settings.json")

        os.makedirs(self.images_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
        os.makedirs(self.data_dir, exist_ok=True)

        self._ensure_manifest()
        self._ensure_settings()

    @classmethod
    def get_instance(cls) -> 'MediaStorageManager':
        if cls._instance is None:
            cls._instance = MediaStorageManager()
        return cls._instance

    def _ensure_manifest(self):
        """Initializes empty gallery manifest if not present."""
        if not os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "w", encoding="utf-8") as f:
                    json.dump([], f, indent=2)
            except Exception as e:
                logger.error(f"Failed to initialize gallery manifest: {e}")

    def _ensure_settings(self):
        """Initializes default media settings (7-day retention) if not present."""
        if not os.path.exists(self.settings_path):
            default_settings = {
                "retention_days": 7,
                "auto_purge_enabled": True,
                "last_purge_timestamp": 0.0,
                "default_width": 512,
                "default_height": 512,
                "max_gallery_items": 500
            }
            try:
                with open(self.settings_path, "w", encoding="utf-8") as f:
                    json.dump(default_settings, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to initialize media settings: {e}")

    def get_settings(self) -> Dict[str, Any]:
        """Load current media generation & retention settings."""
        try:
            if os.path.exists(self.settings_path):
                with open(self.settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Error reading media settings: {e}")
        return {"retention_days": 7, "auto_purge_enabled": True}

    def update_settings(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update media settings (e.g. retention_days)."""
        current = self.get_settings()
        current.update(updates)
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(current, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write media settings: {e}")
        return current

    def save_image(
        self,
        image: Image.Image,
        prompt: str,
        seed: int,
        generation_time_sec: float,
        engine: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ImageResult:
        """
        Saves a PIL Image to static/generated/images/, updates manifest, and triggers auto-purge.
        """
        now = time.time()
        image_id = f"img_{int(now)}_{uuid.uuid4().hex[:6]}"
        filename = f"{image_id}.png"
        file_path = os.path.join(self.images_dir, filename)
        web_url = f"/static/generated/images/{filename}"

        # Save PNG to disk
        image.save(file_path, format="PNG", optimize=True)
        size_bytes = os.path.getsize(file_path)
        w, h = image.size

        # Compute expiration timestamp based on retention_days
        settings = self.get_settings()
        retention_days = float(settings.get("retention_days", 7))
        expires_at = (now + retention_days * 86400) if retention_days > 0 else None

        item = GalleryItem(
            image_id=image_id,
            prompt=prompt,
            web_url=web_url,
            file_path=file_path,
            timestamp=now,
            size_bytes=size_bytes,
            width=w,
            height=h,
            engine=engine,
            seed=seed,
            expires_at=expires_at
        )

        self._append_manifest(item)

        # Trigger background auto-purge periodically
        if settings.get("auto_purge_enabled", True):
            self.auto_purge(retention_days=retention_days)

        return ImageResult(
            image_id=image_id,
            file_path=file_path,
            web_url=web_url,
            prompt=prompt,
            seed=seed,
            generation_time_sec=generation_time_sec,
            timestamp=now,
            width=w,
            height=h,
            size_bytes=size_bytes,
            engine=engine,
            metadata=metadata or {}
        )

    def _load_manifest(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.manifest_path):
            return []
        try:
            with open(self.manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading media manifest: {e}")
            return []

    def _save_manifest(self, items: List[Dict[str, Any]]):
        try:
            with open(self.manifest_path, "w", encoding="utf-8") as f:
                json.dump(items, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving media manifest: {e}")

    def _append_manifest(self, item: GalleryItem):
        items = self._load_manifest()
        items.insert(0, item.to_dict())  # Newest first
        self._save_manifest(items)

    def get_gallery(self, limit: int = 50, offset: int = 0, query: Optional[str] = None) -> Dict[str, Any]:
        """Retrieve paginated gallery items sorted newest first with optional prompt search."""
        items = self._load_manifest()

        # Validate that referenced files actually exist on disk
        valid_items = []
        for it in items:
            fp = it.get("file_path", "")
            if os.path.exists(fp):
                valid_items.append(it)

        # Filter by search query if provided
        if query:
            q_low = query.lower().strip()
            valid_items = [it for it in valid_items if q_low in it.get("prompt", "").lower()]

        total_count = len(valid_items)
        paginated = valid_items[offset:offset + limit]

        return {
            "items": paginated,
            "total": total_count,
            "limit": limit,
            "offset": offset
        }

    def delete_image(self, image_id: str) -> bool:
        """Explicitly delete an image from disk and gallery manifest."""
        items = self._load_manifest()
        new_items = []
        deleted = False

        for it in items:
            if it.get("image_id") == image_id:
                fp = it.get("file_path", "")
                if os.path.exists(fp):
                    try:
                        os.remove(fp)
                    except Exception as e:
                        logger.warning(f"Could not remove image file {fp}: {e}")
                deleted = True
            else:
                new_items.append(it)

        if deleted:
            self._save_manifest(new_items)
        return deleted

    def auto_purge(self, retention_days: Optional[float] = None) -> int:
        """
        Scans gallery items and filesystem, safely pruning images older than retention_days.
        If retention_days <= 0, auto-purge is skipped (permanent retention).
        Returns number of pruned items.
        """
        if retention_days is None:
            settings = self.get_settings()
            retention_days = float(settings.get("retention_days", 7))

        if retention_days <= 0:
            return 0  # Permanent retention

        now = time.time()
        max_age_seconds = retention_days * 86400
        cutoff_time = now - max_age_seconds

        items = self._load_manifest()
        retained_items = []
        pruned_count = 0

        for it in items:
            ts = float(it.get("timestamp", 0.0))
            if ts < cutoff_time:
                # Expired -> delete file from disk
                fp = it.get("file_path", "")
                if os.path.exists(fp):
                    try:
                        os.remove(fp)
                    except Exception as e:
                        logger.warning(f"Error purging file {fp}: {e}")
                pruned_count += 1
            else:
                retained_items.append(it)

        if pruned_count > 0:
            self._save_manifest(retained_items)
            logger.info(f"Auto-purge complete: Removed {pruned_count} images older than {retention_days} days.")

        # Update last purge timestamp
        settings = self.get_settings()
        settings["last_purge_timestamp"] = now
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        except Exception:
            pass

        return pruned_count
