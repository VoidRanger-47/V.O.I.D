# core/mcp/stdio_server.py
"""
V.O.I.D. MCP Stdio Server Runner.
Entry point for external MCP clients (Claude Desktop, Cursor, Antigravity, Zed)
connecting to V.O.I.D. over standard I/O pipes.

Usage in Claude Desktop / Cursor config:
{
  "mcpServers": {
    "void": {
      "command": "python",
      "args": ["-m", "core.mcp.stdio_server"],
      "cwd": "C:\\Users\\kbven\\OneDrive\\Documents\\VOID"
    }
  }
}
"""

import sys
import os
import json
import logging
import builtins

# 1. Capture pristine stdout specifically for MCP JSON-RPC protocol frames
_rpc_stdout = sys.stdout
_rpc_stdin = sys.stdin

# 2. Redirect Python's standard print() to stderr to prevent any library/plugin logs
# from corrupting the JSON-RPC stdout pipe
def _safe_stderr_print(*args, **kwargs):
    sep = kwargs.get("sep", " ")
    end = kwargs.get("end", "\n")
    sys.stderr.write(sep.join(str(a) for a in args) + end)
    sys.stderr.flush()

builtins.print = _safe_stderr_print
sys.stdout = sys.stderr
sys.__stdout__ = sys.stderr

# Ensure project root is in sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

# Configure logging to stderr
logging.basicConfig(
    stream=sys.stderr,
    level=logging.INFO,
    format="%(asctime)s [VOID-MCP] %(levelname)s: %(message)s"
)
logger = logging.getLogger("VOID.MCP.Stdio")

from core.mcp.server import mcp_server


def main():
    logger.info("V.O.I.D. MCP Stdio Server started. Listening on stdin...")

    while True:
        try:
            line = _rpc_stdin.readline()
            if not line:
                break

            line = line.strip()
            if not line:
                continue

            try:
                request = json.loads(line)
            except json.JSONDecodeError as e:
                err_resp = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {"code": -32700, "message": f"Parse error: {str(e)}"}
                }
                _rpc_stdout.write(json.dumps(err_resp) + "\n")
                _rpc_stdout.flush()
                continue

            response = mcp_server.handle_request(request)

            # Notifications have no response
            if response:
                _rpc_stdout.write(json.dumps(response) + "\n")
                _rpc_stdout.flush()

        except KeyboardInterrupt:
            logger.info("MCP Stdio Server shutting down gracefully.")
            break
        except Exception as e:
            logger.error(f"Unexpected error in stdio server loop: {e}", exc_info=True)


if __name__ == "__main__":
    main()
