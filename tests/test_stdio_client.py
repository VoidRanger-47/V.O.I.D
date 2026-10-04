# tests/test_stdio_client.py
import subprocess
import json
import unittest


class TestMCPStdioClient(unittest.TestCase):
    def test_stdio_handshake(self):
        proc = subprocess.Popen(
            ['python', '-m', 'core.mcp.stdio_server'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        init_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05"}
        }) + "\n"

        tools_req = json.dumps({
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }) + "\n"

        stdout, stderr = proc.communicate(input=init_req + tools_req, timeout=20)
        lines = [line.strip() for line in stdout.strip().split("\n") if line.strip()]

        self.assertEqual(len(lines), 2, f"Expected exactly 2 JSON-RPC responses, got {len(lines)}: {lines}")

        resp1 = json.loads(lines[0])
        self.assertEqual(resp1.get("id"), 1)
        self.assertEqual(resp1.get("result", {}).get("protocolVersion"), "2024-11-05")

        resp2 = json.loads(lines[1])
        self.assertEqual(resp2.get("id"), 2)
        tools = resp2.get("result", {}).get("tools", [])
        self.assertGreater(len(tools), 0)


if __name__ == "__main__":
    unittest.main()
