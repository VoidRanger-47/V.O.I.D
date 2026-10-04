"""
void_cloud/ollama/cli.py
Command-Line Interface for V.O.I.D. Ollama Offline Model Engine.

Usage:
  python -m void_cloud.ollama.cli status
  python -m void_cloud.ollama.cli models
  python -m void_cloud.ollama.cli set-model <model_name>
  python -m void_cloud.ollama.cli set-host <url>
  python -m void_cloud.ollama.cli pull <model_name>
  python -m void_cloud.ollama.cli run "<prompt>"
  python -m void_cloud.ollama.cli chat
  python -m void_cloud.ollama.cli on
  python -m void_cloud.ollama.cli off
"""

import sys
import time
from typing import List

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if sys.stderr and hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from void_cloud.ollama.manager import OllamaOfflineManager


def print_banner():
    print("=" * 65)
    print("[OLLAMA] V.O.I.D. Offline LLM Engine")
    print("         100% Local Inference & Neural Perception")
    print("=" * 65)


def cmd_status(mgr: OllamaOfflineManager):
    print_banner()
    st = mgr.get_status()
    print(f"Enabled        : {'YES' if st['enabled'] else 'NO'}")
    print(f"Server Status  : {'[RUNNING]' if st['server_running'] else '[STOPPED / UNREACHABLE]'}")
    print(f"Host Endpoint  : {st['host']}")
    print(f"Active Model   : {st['active_model']}")
    print(f"Model Present  : {'[YES]' if st['has_active_model'] else '[NOT DOWNLOADED]'}")
    print(f"Context Window : {st['num_ctx']} tokens")
    print(f"Temperature    : {st['temperature']}")
    print("-" * 65)

    if st['server_running']:
        models = st['installed_models']
        if models:
            print(f"Installed Models ({len(models)}):")
            for m in models:
                mark = "* " if m.startswith(st['active_model']) else "  "
                print(f"  {mark}{m}")
        else:
            print("No models downloaded yet. Run:")
            print(f"  python -m void_cloud.ollama.cli pull {st['active_model']}")
    else:
        print("[!] Ollama daemon is not responding.")
        print("    Start it by running 'ollama serve' in another terminal,")
        print("    or install Ollama from https://ollama.com")
    print("=" * 65)


def cmd_models(mgr: OllamaOfflineManager):
    if not mgr.client.is_server_available():
        print(f"[!] Error: Cannot connect to Ollama at {mgr.config.host}")
        return

    models = mgr.client.list_models()
    if not models:
        print("No models found locally.")
        print(f"To download one, run: python -m void_cloud.ollama.cli pull {mgr.config.model}")
        return

    print("=" * 65)
    print(f"Available Local Offline Models ({len(models)}):")
    print("=" * 65)
    for m in models:
        name = m.get("name", "unknown")
        size_gb = m.get("size", 0) / (1024 ** 3)
        details = m.get("details", {})
        param_size = details.get("parameter_size", "unknown")
        quant = details.get("quantization_level", "unknown")
        active = " (ACTIVE)" if name.startswith(mgr.config.model) else ""
        print(f" - {name:<24} | {size_gb:.2f} GB | {param_size} | {quant}{active}")
    print("=" * 65)


def cmd_set_model(mgr: OllamaOfflineManager, model_name: str):
    mgr.set_model(model_name)
    print(f"[OK] Active Ollama offline model set to: '{model_name}'")
    if mgr.client.is_server_available():
        if mgr.client.has_model(model_name):
            print(f"     Model '{model_name}' is verified and installed locally.")
        else:
            print(f"     [!] Model '{model_name}' is NOT yet downloaded.")
            print(f"     Run: python -m void_cloud.ollama.cli pull {model_name}")


def cmd_set_host(mgr: OllamaOfflineManager, host_url: str):
    mgr.set_host(host_url)
    print(f"[OK] Ollama host URL set to: '{host_url}'")


def cmd_pull(mgr: OllamaOfflineManager, model_name: str):
    if not mgr.client.is_server_available():
        print(f"[!] Error: Cannot connect to Ollama at {mgr.config.host}")
        return

    print(f"[PULL] Pulling model '{model_name}' from Ollama library...")
    print("       (This runs locally, streaming the model directly to your machine)\n")
    try:
        last_status = ""
        for chunk in mgr.pull_model(model_name):
            status = chunk.get("status", "")
            completed = chunk.get("completed", 0)
            total = chunk.get("total", 0)

            if total > 0 and completed > 0:
                pct = (completed / total) * 100
                mb_done = completed / (1024 * 1024)
                mb_total = total / (1024 * 1024)
                sys.stdout.write(f"\r       [{status}] {pct:5.1f}% ({mb_done:.1f} MB / {mb_total:.1f} MB)")
                sys.stdout.flush()
            elif status != last_status:
                print(f"       [{status}]")
                last_status = status

        print(f"\n\n[OK] Successfully downloaded '{model_name}'!")
        mgr.set_model(model_name)
    except Exception as e:
        print(f"\n[ERROR] Pull failed: {e}")


def cmd_run(mgr: OllamaOfflineManager, prompt: str):
    print(f"Model  : {mgr.config.model} (100% Offline)")
    print(f"Prompt : {prompt}")
    print("-" * 65)

    try:
        start_t = time.time()
        token_count = 0
        for token in mgr.stream_tokens(prompt):
            sys.stdout.write(token)
            sys.stdout.flush()
            token_count += 1
        elapsed = time.time() - start_t
        tps = token_count / elapsed if elapsed > 0 else 0
        print(f"\n\n[Finished in {elapsed:.2f}s - {tps:.1f} tokens/sec]")
    except Exception as e:
        print(f"\n[ERROR] Generation error: {e}")


def cmd_chat(mgr: OllamaOfflineManager):
    print_banner()
    print(f"Active Model: {mgr.config.model} | Type 'exit' or 'quit' to end.\n")

    history = []
    while True:
        try:
            user_in = input("You > ").strip()
            if not user_in:
                continue
            if user_in.lower() in ("exit", "quit"):
                print("Exiting chat session.")
                break

            history.append({"role": "user", "content": user_in})
            print("\nV.O.I.D. > ", end="", flush=True)

            response_tokens = []
            for token in mgr.client.stream_chat(history):
                sys.stdout.write(token)
                sys.stdout.flush()
                response_tokens.append(token)
            print("\n")
            history.append({"role": "assistant", "content": "".join(response_tokens)})

        except (KeyboardInterrupt, EOFError):
            print("\nExiting.")
            break


def main():
    args = sys.argv[1:]
    mgr = OllamaOfflineManager.get_instance()

    if not args or args[0] in ("-h", "--help", "help"):
        print(__doc__)
        return

    cmd = args[0].lower()

    if cmd == "status":
        cmd_status(mgr)
    elif cmd in ("models", "list", "ls"):
        cmd_models(mgr)
    elif cmd == "set-model":
        if len(args) < 2:
            print("Usage: python -m void_cloud.ollama.cli set-model <model_name>")
            sys.exit(1)
        cmd_set_model(mgr, args[1])
    elif cmd == "set-host":
        if len(args) < 2:
            print("Usage: python -m void_cloud.ollama.cli set-host <url>")
            sys.exit(1)
        cmd_set_host(mgr, args[1])
    elif cmd == "pull":
        if len(args) < 2:
            print("Usage: python -m void_cloud.ollama.cli pull <model_name>")
            sys.exit(1)
        cmd_pull(mgr, args[1])
    elif cmd in ("run", "generate", "test"):
        prompt = " ".join(args[1:]) if len(args) > 1 else "Introduce yourself in two sentences."
        cmd_run(mgr, prompt)
    elif cmd == "chat":
        cmd_chat(mgr)
    elif cmd == "on":
        mgr.set_enabled(True)
        print("✅ Ollama offline engine enabled.")
    elif cmd == "off":
        mgr.set_enabled(False)
        print("⭕ Ollama offline engine disabled.")
    else:
        print(f"Unknown command: '{cmd}'. Run with --help for options.")
        sys.exit(1)


if __name__ == "__main__":
    main()
