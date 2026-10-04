# tests/test_flask_app.py
import unittest
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app

class TestFlaskApp(unittest.TestCase):
    def setUp(self):
        self.client = app.test_client()

    def test_index_route(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_diagnostics_route(self):
        response = self.client.get("/api/diagnostics")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["core"], "ONLINE")
        self.assertIn("tools", data)

    def test_agent_state_route(self):
        response = self.client.get("/api/agent/state")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("cpu_usage_percent", data)
        self.assertIn("ram_percent", data)
        self.assertIn("offline_mode", data)

    def test_tools_route(self):
        response = self.client.get("/api/tools")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("tools", data)
        self.assertGreater(data["count"], 0)

    def test_memory_route(self):
        # Store
        res_post = self.client.post("/api/memory", json={"text": "Flask test memory", "tier": "semantic"})
        self.assertEqual(res_post.status_code, 200)

        # Get
        res_get = self.client.get("/api/memory?q=Flask")
        self.assertEqual(res_get.status_code, 200)
        data = json.loads(res_get.data)
        self.assertGreater(data["count"], 0)

        # Forget
        res_del = self.client.delete("/api/memory", json={"target": "Flask test memory"})
        self.assertEqual(res_del.status_code, 200)

    def test_network_status_route(self):
        response = self.client.get("/api/network/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIn("offline_mode", data)
        self.assertIn("internet_available", data)
        self.assertIn("local_components", data)

    def test_search_route_offline(self):
        from lib.offline_manager import offline_mgr
        offline_mgr.cached_online_state = False
        offline_mgr.last_check_time = 9999999999.0

        response = self.client.get("/api/search?q=Python+news")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "offline")
        self.assertTrue(data["no_internet"])
        self.assertIn("No Internet Access", data["result"])

    def test_search_route_empty_query(self):
        response = self.client.get("/api/search?q=")
        self.assertEqual(response.status_code, 400)

    def test_chat_stream_empty(self):
        response = self.client.post("/api/chat/stream", json={"message": ""})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))
        data = response.get_data(as_text=True)
        self.assertIn("data:", data)
        self.assertIn("done", data)

    def test_chat_stream_deterministic_tool(self):
        response = self.client.post("/api/chat/stream", json={"message": "what time is it?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))
        data = response.get_data(as_text=True)
        self.assertIn("data:", data)
        self.assertIn("tool_call", data)
        self.assertIn("done", data)

    def test_health_route(self):
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
        data = json.loads(response.data)
        self.assertEqual(data["status"], "online")

    def test_api_chat_json_response(self):
        response = self.client.post("/api/chat", json={"message": "what time is it?"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")
        data = json.loads(response.data)
        self.assertIn("response", data)
        self.assertIn("reply", data)
        self.assertIn("content", data)
        self.assertEqual(data["status"], "success")

    def test_plugins_list_route(self):
        response = self.client.get("/api/plugins")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("plugins", data)
        plugin_ids = [p["id"] for p in data["plugins"]]
        self.assertIn("gmail_analyzer", plugin_ids)

    def test_gmail_status_route(self):
        response = self.client.get("/api/plugins/gmail/status")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("connected", data)
        self.assertIn("configured", data)

    def test_gmail_analyze_route(self):
        response = self.client.post("/api/plugins/gmail/analyze", json={"query": "analyze my gmail"})
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("report", data)
        self.assertIn("total_emails", data)
    def test_vision_page_route(self):
        response = self.client.get("/vision")
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn("V.O.I.D. PERCEPTION", html)
        self.assertIn("Subject Dossier", html)
        self.assertIn("EXCLUSIVE CAMERA SESSION", html)

    def test_vision_subject_route(self):
        response = self.client.get("/api/vision/subject")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("subject", data)

    def test_vision_camera_exclusivity(self):
        # 1. Access denied when not on /vision page
        res_denied = self.client.post("/api/vision/start", json={})
        self.assertEqual(res_denied.status_code, 403)
        data_denied = json.loads(res_denied.data)
        self.assertEqual(data_denied["status"], "denied")

        # 2. Feed denied when not on /vision page
        feed_denied = self.client.get("/api/vision/feed")
        self.assertEqual(feed_denied.status_code, 403)

        # 3. Stop camera is always allowed and safe
        res_stop = self.client.post("/api/vision/stop")
        self.assertEqual(res_stop.status_code, 200)
        data_stop = json.loads(res_stop.data)
        self.assertFalse(data_stop["active"])

if __name__ == "__main__":
    unittest.main()

