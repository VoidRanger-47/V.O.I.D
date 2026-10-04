# tests/test_web_voice.py
import unittest
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app
from void_voice.tts.piper_engine import VoiceEngine

class TestWebVoice(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()
        self.engine = VoiceEngine({"tts_enabled": True})

    def test_clean_text_for_speech(self):
        sample = "<thinking>Deep reasoning thought</thinking>Here is **bold** text and `code snippet` with ```python\nprint(1)\n``` and [link](http://test.com)."
        cleaned = self.engine.clean_text_for_speech(sample)
        self.assertNotIn("Deep reasoning thought", cleaned)
        self.assertNotIn("<thinking>", cleaned)
        self.assertNotIn("```", cleaned)
        self.assertIn("Here is bold text", cleaned)
        self.assertIn("Code block omitted", cleaned)

    def test_voice_engine_synthesize_to_bytes(self):
        audio_bytes = self.engine.synthesize_to_bytes("Hello from VOID automated voice tests.")
        self.assertIsNotNone(audio_bytes)
        self.assertGreater(len(audio_bytes), 44)  # Valid WAV file is larger than 44-byte header
        self.assertEqual(audio_bytes[:4], b"RIFF")

    def test_api_voice_status(self):
        response = self.client.get("/api/voice/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data.get("web_speech_supported"))
        self.assertIn("tts_available", data)
        self.assertIn("language", data)

    def test_api_voice_speak_post(self):
        response = self.client.post("/api/voice/speak", json={"text": "Speaking through web interface."})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/wav")
        self.assertGreater(len(response.data), 44)
        self.assertEqual(response.data[:4], b"RIFF")

    def test_api_voice_speak_get(self):
        response = self.client.get("/api/voice/speak?text=Hello+from+browser+query")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, "audio/wav")
        self.assertGreater(len(response.data), 44)
        self.assertEqual(response.data[:4], b"RIFF")

    def test_api_voice_speak_empty(self):
        response = self.client.post("/api/voice/speak", json={"text": ""})
        self.assertEqual(response.status_code, 400)
        data = json.loads(response.data)
        self.assertEqual(data.get("status"), "error")

if __name__ == "__main__":
    unittest.main()
