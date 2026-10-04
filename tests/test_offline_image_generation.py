"""
tests/test_offline_image_generation.py
Comprehensive test suite for V.O.I.D. 100% Offline Image Generation and Retention Management.
"""

import unittest
import os
import shutil
import json
import time
from datetime import datetime, timezone, timedelta
from PIL import Image

from void_media.models import ImageRequest, ImageResult, ImageStylePreset, GalleryItem
from void_media.storage import MediaStorageManager
from void_media.offline_diffusion_engine import OfflineImageEngine
from void_media.engine import MediaEngine
from skills.media_engine import MediaSkillEngine
from skills.router import SkillRouter, SkillType
from core.tool_registry import tool_registry


class TestOfflineImageStorage(unittest.TestCase):
    """Unit tests for image storage, gallery indexing, and auto-purge."""

    def setUp(self):
        self.test_dir = os.path.join(os.getcwd(), "data", "test_images_storage")
        self.test_manifest = os.path.join(os.getcwd(), "data", "test_media_gallery.json")
        os.makedirs(self.test_dir, exist_ok=True)
        self.storage = MediaStorageManager(storage_dir=self.test_dir, manifest_path=self.test_manifest)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        if os.path.exists(self.test_manifest):
            try:
                os.remove(self.test_manifest)
            except OSError:
                pass

    def test_save_and_retrieve_gallery(self):
        # Create a dummy PIL image
        img = Image.new("RGB", (256, 256), color=(40, 100, 200))
        item = self.storage.save_image(
            image=img,
            prompt="neon cyberpunk street",
            seed=4242,
            generation_time_sec=0.12,
            engine="test_engine",
            metadata={"style": "cyberpunk"}
        )

        self.assertIsNotNone(item.image_id)
        self.assertTrue(os.path.exists(item.file_path))
        self.assertEqual(item.prompt, "neon cyberpunk street")

        # Query gallery
        gallery = self.storage.get_gallery()
        self.assertEqual(gallery["total"], 1)
        self.assertEqual(len(gallery["items"]), 1)
        self.assertEqual(gallery["items"][0]["image_id"], item.image_id)

    def test_delete_image(self):
        img = Image.new("RGB", (128, 128), color=(20, 20, 20))
        item = self.storage.save_image(
            image=img,
            prompt="to be deleted",
            seed=1,
            generation_time_sec=0.05,
            engine="test_engine"
        )
        self.assertTrue(os.path.exists(item.file_path))

        deleted = self.storage.delete_image(item.image_id)
        self.assertTrue(deleted)
        self.assertFalse(os.path.exists(item.file_path))

        gallery = self.storage.get_gallery()
        self.assertEqual(gallery["total"], 0)
        self.assertEqual(len(gallery["items"]), 0)

    def test_auto_purge_expired_images(self):
        # Save two images: one recent, one simulated 10 days old
        img = Image.new("RGB", (128, 128), color=(50, 50, 50))
        recent_item = self.storage.save_image(img, "recent image", seed=10, generation_time_sec=0.01, engine="test")
        old_item = self.storage.save_image(img, "old expired image", seed=20, generation_time_sec=0.01, engine="test")

        # Manually alter the timestamp of old_item in the manifest to 10 days ago
        ten_days_ago_ts = time.time() - (10 * 86400)
        with open(self.test_manifest, "r", encoding="utf-8") as f:
            manifest_data = json.load(f)

        for it in manifest_data:
            if it["image_id"] == old_item.image_id:
                it["timestamp"] = ten_days_ago_ts

        with open(self.test_manifest, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f)

        # Run purge with 7-day retention
        purged_count = self.storage.auto_purge(retention_days=7)

        self.assertEqual(purged_count, 1)
        self.assertFalse(os.path.exists(old_item.file_path))
        self.assertTrue(os.path.exists(recent_item.file_path))

        # Check remaining gallery
        gallery = self.storage.get_gallery()
        self.assertEqual(gallery["total"], 1)
        self.assertEqual(gallery["items"][0]["image_id"], recent_item.image_id)


class TestOfflineDiffusionEngine(unittest.TestCase):
    """Unit tests for the offline image generation engine."""

    def setUp(self):
        self.engine = OfflineImageEngine.get_instance()

    def test_offline_canvas_synthesis(self):
        req = ImageRequest(
            prompt="futuristic neon android face",
            style_preset=ImageStylePreset.CYBERPUNK,
            width=256,
            height=256,
            seed=1234
        )
        pil_img, engine_name = self.engine.generate(req)

        self.assertIsInstance(pil_img, Image.Image)
        self.assertEqual(pil_img.size, (256, 256))
        self.assertTrue("sd-turbo" in engine_name.lower() or "offline" in engine_name.lower())


class TestMediaSkillAndRouter(unittest.TestCase):
    """Unit tests for SkillRouter and MediaSkillEngine integration."""

    def setUp(self):
        self.router = SkillRouter()
        self.skill_engine = MediaSkillEngine.get_instance()

    def test_skill_routing_intent(self):
        queries = [
            "generate an image of a cybernetic panther",
            "draw a neon cityscape at night",
            "create an artwork of deep space nebula",
            "paint an oil portrait of an astronaut",
            "make a picture of robotic warrior"
        ]
        for q in queries:
            decision = self.router.route(q)
            self.assertEqual(decision.skill, SkillType.IMAGE_GENERATION, f"Failed to route '{q}' to IMAGE_GENERATION")

    def test_prompt_parser(self):
        req = self.skill_engine.parse_prompt("Can you please draw an image of a futuristic flying car cyberpunk style")
        self.assertEqual(req.style_preset, ImageStylePreset.CYBERPUNK)
        self.assertIn("futuristic flying car", req.prompt.lower())

    def test_markdown_response_format(self):
        response = self.skill_engine.handle_query("draw a miniature bonsai tree")
        self.assertIn("Offline Image Generated Successfully", response)
        self.assertIn("Engine", response)
        self.assertIn("Resolution", response)
        self.assertIn("View in Studio Gallery", response)


class TestToolRegistryIntegration(unittest.TestCase):
    """Test tool registry execution of generate_image tool."""

    def test_tool_registered_and_executable(self):
        tool = tool_registry.get_tool("generate_image")
        self.assertIsNotNone(tool, "generate_image tool not found in tool_registry")

        result = tool_registry.execute_tool(
            "generate_image",
            {"prompt": "emerald dragon in celestial mist", "style": "cinematic"}
        )
        self.assertIn("Offline Image Generated Successfully", result)
        self.assertIn("emerald dragon", result)


class TestFlaskAppMediaEndpoints(unittest.TestCase):
    """Integration test with Flask app endpoints for media."""

    def setUp(self):
        from app import app
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_gallery_and_settings_endpoints(self):
        # 1. Get Settings
        res = self.client.get('/api/image/settings')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertIn("settings", data)
        self.assertIn("retention_days", data["settings"])
        self.assertEqual(data["settings"]["retention_days"], 7)

        # 2. Update Settings
        res = self.client.post('/api/image/settings', json={"retention_days": 14})
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["settings"]["retention_days"], 14)

        # Revert settings back to 7
        self.client.post('/api/image/settings', json={"retention_days": 7})

        # 3. Generate Image via REST API
        res = self.client.post('/api/image/generate', json={
            "prompt": "luminescent quantum processor",
            "style_preset": "cyberpunk",
            "width": 256,
            "height": 256
        })
        self.assertEqual(res.status_code, 200)
        gen_data = res.get_json()
        self.assertEqual(gen_data["status"], "success")
        self.assertIn("image", gen_data)
        img_id = gen_data["image"]["image_id"]

        # 4. Get Gallery
        res = self.client.get('/api/image/gallery')
        self.assertEqual(res.status_code, 200)
        gallery_data = res.get_json()
        self.assertEqual(gallery_data["status"], "success")
        ids = [item["image_id"] for item in gallery_data.get("items", [])]
        self.assertIn(img_id, ids)

        # 5. Trigger Purge Endpoint
        res = self.client.post('/api/image/purge', json={"retention_days": 7})
        self.assertEqual(res.status_code, 200)
        purge_data = res.get_json()
        self.assertEqual(purge_data["status"], "success")

        # 6. Delete the test generated image
        res = self.client.delete(f'/api/image/{img_id}')
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
