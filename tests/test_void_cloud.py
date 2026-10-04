# tests/test_void_cloud.py
import unittest
import os
import sys
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from void_cloud.gemini_client import GeminiClient
from void_cloud.cloud_manager import CloudManager
from void_cloud import cli


class TestVoidCloud(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = os.path.join(self.temp_dir.name, "config.json")
        self.mgr = CloudManager(config_path=self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_state_is_offline(self):
        status = self.mgr.get_status()
        self.assertFalse(status["enabled"])
        self.assertFalse(status["is_active"])
        self.assertFalse(self.mgr.is_cloud_active())
        self.assertEqual(status["provider"], "gemini")
        self.assertEqual(status["model_name"], "gemini-3.6-flash")

    def test_set_api_key_and_enable(self):
        self.mgr.set_api_key("AIzaSyFakeKey12345")
        self.mgr.set_enabled(True)
        self.assertTrue(self.mgr.is_cloud_active())
        self.assertTrue(self.mgr.get_status()["api_key_configured"])

        # Disable
        self.mgr.set_enabled(False)
        self.assertFalse(self.mgr.is_cloud_active())

    def test_set_model(self):
        self.mgr.set_model("gemini-2.0-pro-exp")
        self.assertEqual(self.mgr.get_status()["model_name"], "gemini-2.0-pro-exp")

    def test_gemini_sse_stream_parsing(self):
        client = GeminiClient(api_key="AIzaSyFakeKey", model_name="gemini-2.0-flash")
        
        # Simulate SSE response data
        mock_chunks = [
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"Hello\"}]}}]}\n\n",
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \" world\"}]}}]}\n\n",
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"!\"}]}}]}\n\n",
            b"data: [DONE]\n\n"
        ]

        mock_resp = MagicMock()
        mock_resp.__enter__.return_value = iter(mock_chunks)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            tokens = list(client.stream_generate_tokens("Hi"))
            self.assertEqual(tokens, ["Hello", " world", "!"])

    def test_cli_commands(self):
        # Test CLI On/Off
        args_mock = MagicMock()
        cli.cmd_on(self.mgr, args_mock)
        self.assertTrue(self.mgr.config["cloud_mode_enabled"])

        cli.cmd_off(self.mgr, args_mock)
        self.assertFalse(self.mgr.config["cloud_mode_enabled"])

        # Test CLI set-key
        args_key = MagicMock()
        args_key.key = "AIzaSyTest123"
        with patch.object(self.mgr, "test_connection", return_value=(True, "Mock OK")):
            cli.cmd_set_key(self.mgr, args_key)
            self.assertEqual(self.mgr.config["api_key"], "AIzaSyTest123")

        # Test CLI set-model
        args_model = MagicMock()
        args_model.model = "gemini-2.0-flash"
        cli.cmd_set_model(self.mgr, args_model)
        self.assertEqual(self.mgr.config["model_name"], "gemini-2.0-flash")


if __name__ == "__main__":
    unittest.main()
