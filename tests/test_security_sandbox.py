# tests/test_security_sandbox.py
import unittest
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.security import SecurityManager, PermissionLevel, SecurityViolationError

class TestSecuritySandbox(unittest.TestCase):
    def setUp(self):
        self.security = SecurityManager()
        self.security.reset_emergency_stop()

    def test_blocks_dangerous_eval(self):
        code = "eval('1 + 1')"
        is_safe, error = self.security.scan_python_ast(code)
        self.assertFalse(is_safe)
        self.assertIn("Security Violation", error)

    def test_blocks_dangerous_os_system(self):
        code = "import os\nos.system('dir')"
        is_safe, error = self.security.scan_python_ast(code)
        self.assertFalse(is_safe)
        self.assertIn("Security Violation", error)

    def test_blocks_forbidden_network_imports(self):
        code = "import socket\ns = socket.socket()"
        is_safe, error = self.security.scan_python_ast(code)
        self.assertFalse(is_safe)
        self.assertIn("socket", error)

    def test_blocks_subprocess_calls(self):
        code = "import subprocess\nsubprocess.Popen(['notepad'])"
        is_safe, error = self.security.scan_python_ast(code)
        self.assertFalse(is_safe)
        self.assertIn("subprocess", error)

    def test_executes_safe_math_python(self):
        code = "import math\nx = math.sqrt(144)\nprint(f'Result: {int(x)}')"
        res = self.security.execute_sandboxed_python(code)
        self.assertTrue(res["success"])
        self.assertEqual(res["output"], "Result: 12")

    def test_emergency_stop_blocks_execution(self):
        self.security.trigger_emergency_stop("Test emergency trigger")
        res = self.security.execute_sandboxed_python("print('hello')")
        self.assertFalse(res["success"])
        self.assertIn("Emergency Stop", res["output"])

        with self.assertRaises(SecurityViolationError):
            self.security.verify_permission(PermissionLevel.LEVEL_1_READ_INFO, "test_tool")

        # Reset emergency stop
        self.security.reset_emergency_stop()
        self.assertTrue(self.security.verify_permission(PermissionLevel.LEVEL_1_READ_INFO, "test_tool"))

if __name__ == "__main__":
    unittest.main()
