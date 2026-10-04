# tests/test_mcp_server.py
import unittest
import json
from core.mcp.server import mcp_server
from core.mcp.protocol import LATEST_PROTOCOL_VERSION, METHOD_NOT_FOUND


class TestMCPServer(unittest.TestCase):
    def setUp(self):
        self.server = mcp_server

    def test_initialize(self):
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": LATEST_PROTOCOL_VERSION,
                "clientInfo": {"name": "test-client", "version": "1.0.0"}
            }
        }
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 1)
        self.assertIn("result", res)
        self.assertEqual(res["result"]["protocolVersion"], LATEST_PROTOCOL_VERSION)
        self.assertEqual(res["result"]["serverInfo"]["name"], "void-os-layer")

    def test_ping(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "ping"}
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 2)
        self.assertEqual(res.get("result"), {})

    def test_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 3, "method": "tools/list"}
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 3)
        tools = res["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        self.assertIn("void_system_stats", tool_names)
        self.assertIn("void_list_windows", tool_names)
        self.assertIn("void_focus_window", tool_names)
        self.assertIn("void_desktop_action", tool_names)
        self.assertIn("void_take_screenshot", tool_names)

    def test_tools_call_system_stats(self):
        req = {
            "jsonrpc": "2.0",
            "id": 4,
            "method": "tools/call",
            "params": {
                "name": "void_system_stats",
                "arguments": {}
            }
        }
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 4)
        self.assertFalse(res["result"]["isError"])
        self.assertGreater(len(res["result"]["content"]), 0)
        self.assertEqual(res["result"]["content"][0]["type"], "text")

    def test_tools_call_list_windows(self):
        req = {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "void_list_windows",
                "arguments": {"visible_only": True}
            }
        }
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 5)
        self.assertFalse(res["result"]["isError"])
        text = res["result"]["content"][0]["text"]
        parsed = json.loads(text)
        self.assertIn("windows", parsed)

    def test_resources_list(self):
        req = {"jsonrpc": "2.0", "id": 6, "method": "resources/list"}
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 6)
        resources = res["result"]["resources"]
        uris = [r["uri"] for r in resources]
        self.assertIn("void://system/telemetry", uris)
        self.assertIn("void://desktop/windows", uris)

    def test_resources_read_telemetry(self):
        req = {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "resources/read",
            "params": {"uri": "void://system/telemetry"}
        }
        res = self.server.handle_request(req)
        self.assertEqual(res.get("id"), 7)
        contents = res["result"]["contents"]
        self.assertEqual(len(contents), 1)
        self.assertEqual(contents[0]["uri"], "void://system/telemetry")

    def test_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 99, "method": "non_existent_method"}
        res = self.server.handle_request(req)
        self.assertIn("error", res)
        self.assertEqual(res["error"]["code"], METHOD_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
