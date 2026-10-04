# tests/test_agi_api_integration.py
import unittest
import sys
import json
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import app

class TestAgiApiIntegration(unittest.TestCase):
    """
    Validates end-to-end integration of the 10-Phase AGI Cognitive Architecture
    with the Flask API for Web and Mobile Phone clients.
    """
    def setUp(self):
        self.client = app.test_client()

    def test_mobile_chat_api(self):
        """Validates /api/chat contract for mobile phone (Android/Flutter) clients."""
        payload = {
            "message": "what is 15 + 27?",
            "settings": {"temperature": 0.5, "maxTokens": 100}
        }
        response = self.client.post("/api/chat", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers.get("Access-Control-Allow-Origin"), "*")

        data = json.loads(response.data)
        # Mobile clients rely on response, reply, content, status
        self.assertIn("response", data)
        self.assertIn("reply", data)
        self.assertIn("content", data)
        self.assertEqual(data["status"], "success")

        # AGI Cognitive attributes
        self.assertIn("cognitive_state", data)
        self.assertIn("task_id", data["cognitive_state"])
        self.assertIn("plan", data)
        self.assertIn("executed_tools", data)
        self.assertIn("duration_s", data)
        self.assertGreaterEqual(data["duration_s"], 0.0)

    def test_web_chat_stream_api(self):
        """Validates /api/chat/stream SSE events for Web UI and mobile streaming."""
        payload = {
            "message": "what time is it?",
            "thinking_mode": False
        }
        response = self.client.post("/api/chat/stream", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/event-stream", response.headers.get("Content-Type", ""))

        raw_data = response.get_data(as_text=True)
        self.assertIn("data:", raw_data)
        self.assertIn("task_init", raw_data)
        self.assertIn("tool_call", raw_data)
        self.assertIn("meta_cognition", raw_data)
        self.assertIn("done", raw_data)

    def test_agi_state_and_status_routes(self):
        """Validates real-time telemetry across all 10 AGI phases."""
        for endpoint in ["/api/agi/state", "/api/agi/status"]:
            response = self.client.get(endpoint)
            self.assertEqual(response.status_code, 200)
            data = json.loads(response.data)
            self.assertEqual(data["status"], "success")
            self.assertIn("agi_core", data)

            core = data["agi_core"]
            self.assertIn("supervisor", core)
            self.assertIn("self_model", core)
            self.assertIn("world_model", core)
            self.assertIn("experience_memory", core)
            self.assertIn("skills", core)
            self.assertIn("sleep_daemon", core)
            self.assertIn("adaptation_guard", core)
            self.assertIn("proactive", core)

    def test_agi_world_model_crud(self):
        """Validates inspecting and updating the persistent World Model."""
        # 1. Register entity
        create_res = self.client.post("/api/agi/world_model", json={
            "name": "NeuralNPU",
            "type": "hardware_accelerator",
            "properties": {"tflops": 25.5, "architecture": "tensor"}
        })
        self.assertEqual(create_res.status_code, 200)
        cdata = json.loads(create_res.data)
        self.assertEqual(cdata["status"], "success")
        self.assertEqual(cdata["entity"]["name"], "NeuralNPU")

        # 2. Query entity
        query_res = self.client.get("/api/agi/world_model?q=NeuralNPU")
        self.assertEqual(query_res.status_code, 200)
        qdata = json.loads(query_res.data)
        self.assertEqual(qdata["status"], "success")
        self.assertIsNotNone(qdata["entity"])
        self.assertEqual(qdata["entity"]["name"], "NeuralNPU")

        # 3. List world model
        list_res = self.client.get("/api/agi/world_model")
        self.assertEqual(list_res.status_code, 200)
        ldata = json.loads(list_res.data)
        self.assertGreaterEqual(ldata["entity_count"], 1)

    def test_agi_experiences_route(self):
        """Validates Experience Memory endpoint."""
        response = self.client.get("/api/agi/experiences")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("total_experiences", data)
        self.assertIn("procedural_rules", data)
        self.assertIn("experiences", data)

    def test_agi_proactive_routes(self):
        """Validates Proactive Assistance context evaluation and proposal storage."""
        # 1. Evaluate context
        post_res = self.client.post("/api/agi/proactive", json={
            "context": {
                "cpu_percent": 95.0,
                "ram_percent": 88.0,
                "active_window": "VSCode"
            }
        })
        self.assertEqual(post_res.status_code, 200)
        pdata = json.loads(post_res.data)
        self.assertEqual(pdata["status"], "success")
        self.assertIn("new_proposals", pdata)

        # 2. List proposals
        get_res = self.client.get("/api/agi/proactive")
        self.assertEqual(get_res.status_code, 200)
        gdata = json.loads(get_res.data)
        self.assertEqual(gdata["status"], "success")
        self.assertIn("proposals", gdata)

    def test_agi_sleep_consolidation_trigger(self):
        """Validates on-demand Sleep Consolidation & Dreaming cycle."""
        response = self.client.post("/api/agi/sleep/trigger")
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("report", data)
        self.assertIn("experiences_reviewed", data["report"])
        self.assertIn("rules_synthesized", data["report"])

    def test_agi_curiosity_trigger(self):
        """Validates autonomous curiosity exploration via API."""
        response = self.client.post("/api/agi/curiosity/trigger", json={
            "topic": "Neuromorphic Computing"
        })
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("gap", data)
        self.assertEqual(data["gap"]["topic"], "Neuromorphic Computing")

    def test_agi_empirical_verify(self):
        """Validates Empirical Engine verification endpoint."""
        # Code verification (AST check + Sandbox run)
        valid_code = "def compute(x):\n    return x * 2\n"
        res_code = self.client.post("/api/agi/verify", json={"code": valid_code})
        self.assertEqual(res_code.status_code, 200)
        data_code = json.loads(res_code.data)
        self.assertEqual(data_code["status"], "success")
        self.assertEqual(data_code["verification"]["status"], "PASS")

        # Claim verification
        res_claim = self.client.post("/api/agi/verify", json={"claim": "System has 16GB RAM"})
        self.assertEqual(res_claim.status_code, 200)
        data_claim = json.loads(res_claim.data)
        self.assertEqual(data_claim["status"], "success")
        self.assertEqual(data_claim["verification"]["status"], "PASS")

if __name__ == "__main__":
    unittest.main()
