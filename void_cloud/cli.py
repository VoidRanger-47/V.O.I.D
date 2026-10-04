"""
void_cloud/cli.py
Host-Only Command Line Interface for V.O.I.D. Cloud Engine.
Control cloud token generation, switch models, and configure API keys exclusively from the host console.
"""

import sys
import os
import argparse
from pathlib import Path

# Add project root to sys.path
project_root = str(Path(__file__).resolve().parents[1])
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from void_cloud.cloud_manager import CloudManager


def print_banner():
    print("=" * 60)
    print("[CLOUD] V.O.I.D. HOST-ONLY CLOUD ENGINE CONTROL SWITCH")
    print("=" * 60)


def cmd_status(mgr: CloudManager, args):
    print_banner()
    status = mgr.get_status()
    enabled_str = "[ENABLED] (Cloud Active)" if status["is_active"] else ("[ENABLED] (Missing API Key)" if status["enabled"] else "[DISABLED] (100% Offline Local Model)")
    key_str = "[CONFIGURED]" if status["api_key_configured"] else "[NOT CONFIGURED] (Use: python -m void_cloud.cli set-key <KEY>)"

    print(f"* Cloud Mode Switch:    {enabled_str}")
    print(f"* Active Provider:      {status['provider'].upper()}")
    print(f"* Model Name:           {status['model_name']}")
    print(f"* Gemini API Key:       {key_str}")
    print(f"* Temperature / Top-P:  {status['temperature']} / 0.95")
    print(f"* Auto-Local Fallback:  {'ON' if status['auto_fallback'] else 'OFF'}")
    print("-" * 60)

    if status["api_key_configured"]:
        print("Testing live connectivity to Google Generative Language API...")
        ok, msg = mgr.test_connection()
        if ok:
            print(f"[OK] Connection Status: {msg}")
        else:
            print(f"[WARN] Connection Status: {msg}")
    else:
        print("-> To connect Gemini 2.0, run: python -m void_cloud.cli set-key <YOUR_GEMINI_API_KEY>")
    print("=" * 60)


def cmd_on(mgr: CloudManager, args):
    mgr.set_enabled(True)
    print("[ENABLED] Cloud Token Generation ENABLED for V.O.I.D.")
    if not mgr.gemini_client.is_configured():
        print("[NOTICE] API key is not yet set. Run: python -m void_cloud.cli set-key <YOUR_API_KEY>")
    else:
        print(f"[READY] V.O.I.D. will now generate tokens via {mgr.config.get('model_name', 'gemini-2.0-flash')}.")


def cmd_off(mgr: CloudManager, args):
    mgr.set_enabled(False)
    print("[DISABLED] Cloud Token Generation DISABLED.")
    print("[OFFLINE] V.O.I.D. is now operating in 100% OFFLINE mode using the local PyTorch transformer.")


def cmd_set_key(mgr: CloudManager, args):
    key = args.key.strip()
    if not key:
        print("[ERROR] API key cannot be empty.")
        return
    mgr.set_api_key(key)
    print(f"[SUCCESS] Gemini API key saved successfully in void_cloud/config.json.")
    print("Testing connection...")
    ok, msg = mgr.test_connection()
    if ok:
        print(f"[OK] {msg}")
    else:
        print(f"[WARN] {msg}")


def cmd_set_model(mgr: CloudManager, args):
    model = args.model.strip()
    if not model:
        print("[ERROR] Model name cannot be empty.")
        return
    mgr.set_model(model)
    print(f"[SUCCESS] Cloud Model set to '{model}'.")


def cmd_test(mgr: CloudManager, args):
    prompt = args.prompt or "Hello V.O.I.D., introduce yourself in 2 sentences."
    model_name = mgr.config.get('model_name', 'gemini-3.6-flash')
    print(f"[TEST] Testing live token streaming from {model_name}...")
    print(f"Prompt: \"{prompt}\"\n")
    print("Response: ", end="", flush=True)

    try:
        token_count = 0
        for token in mgr.gemini_client.stream_generate_tokens(prompt):
            print(token, end="", flush=True)
            token_count += 1
        print(f"\n\n[SUCCESS] Streaming test complete ({token_count} chunks received).")
    except Exception as e:
        print(f"\n[ERROR] Streaming failed: {e}")


def main():
    mgr = CloudManager.get_instance()

    parser = argparse.ArgumentParser(
        description="V.O.I.D. Host-Only Cloud Engine Control CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m void_cloud.cli status
  python -m void_cloud.cli on
  python -m void_cloud.cli off
  python -m void_cloud.cli set-key AIzaSy...
  python -m void_cloud.cli set-model gemini-2.0-flash
  python -m void_cloud.cli test "Explain quantum computing briefly"
        """
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # status
    p_status = subparsers.add_parser("status", help="Show current cloud mode status and test connection")
    p_status.set_defaults(func=cmd_status)

    # on / enable
    p_on = subparsers.add_parser("on", help="Enable cloud model token generation")
    p_on.set_defaults(func=cmd_on)

    # off / disable
    p_off = subparsers.add_parser("off", help="Disable cloud mode (revert to 100% offline local model)")
    p_off.set_defaults(func=cmd_off)

    # set-key
    p_key = subparsers.add_parser("set-key", help="Set Gemini API Key")
    p_key.add_argument("key", type=str, help="Gemini API Key")
    p_key.set_defaults(func=cmd_set_key)

    # set-model
    p_model = subparsers.add_parser("set-model", help="Set active Cloud Model name (e.g. gemini-2.0-flash)")
    p_model.add_argument("model", type=str, help="Model name (e.g. gemini-2.0-flash, gemini-2.0-pro-exp)")
    p_model.set_defaults(func=cmd_set_model)

    # test
    p_test = subparsers.add_parser("test", help="Test live streaming token generation in terminal")
    p_test.add_argument("prompt", nargs="?", default="Hello V.O.I.D.!", help="Test prompt")
    p_test.set_defaults(func=cmd_test)

    if len(sys.argv) == 1:
        cmd_status(mgr, None)
        return

    args = parser.parse_args()
    if hasattr(args, "func"):
        args.func(mgr, args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
