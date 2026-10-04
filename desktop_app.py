# desktop_app.py
"""
V.O.I.D. Native Desktop Application Launcher
Launches V.O.I.D. in a dedicated, frameless standalone desktop window using Chromium App Runtime.
Auto-manages the local Python backend lifecycle.
"""
import os
import sys
import time
import subprocess
import urllib.request
import signal

SERVER_URL = "http://127.0.0.1:5000"
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

CHROME_EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\Application\msedge.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
]

def find_app_browser() -> str:
    """Finds a Chromium-based browser that supports native standalone --app mode."""
    for path in CHROME_EDGE_CANDIDATES:
        if os.path.isfile(path):
            return path
    return ""

def is_server_ready(url: str, timeout: float = 0.5) -> bool:
    """Checks if the local V.O.I.D. server is accepting HTTP connections."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=timeout) as res:
            return res.status in (200, 302, 404)
    except Exception:
        return False

def wait_for_server(url: str, max_wait: float = 30.0) -> bool:
    """Polls until the backend is online or timeout expires."""
    start = time.time()
    while time.time() - start < max_wait:
        if is_server_ready(url):
            return True
        time.sleep(0.5)
    return False

def main():
    print("=" * 60)
    print("      V.O.I.D. — Advanced Neural Interface Desktop App")
    print("=" * 60)

    server_process = None

    # 1. Start backend if not already running
    if not is_server_ready(SERVER_URL):
        print("🚀 [Backend] Starting local V.O.I.D. Neural Engine (app.py)...")
        app_script = os.path.join(PROJECT_ROOT, "app.py")
        server_process = subprocess.Popen(
            [sys.executable, app_script],
            cwd=PROJECT_ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0
        )

        print("⏳ [Backend] Waiting for neural model and services to initialize...")
        if not wait_for_server(SERVER_URL, max_wait=35.0):
            print("❌ Error: V.O.I.D. backend failed to start.")
            if server_process:
                server_process.kill()
            sys.exit(1)
    else:
        print("✅ [Backend] Active V.O.I.D. server detected on http://127.0.0.1:5000.")

    # 2. Launch Native Desktop Window
    browser_exe = find_app_browser()
    user_data_dir = os.path.join(PROJECT_ROOT, ".void_desktop_profile")
    os.makedirs(user_data_dir, exist_ok=True)

    if browser_exe:
        print(f"🖥️  [Desktop] Launching native window via: {os.path.basename(browser_exe)}")
        cmd = [
            browser_exe,
            f"--app={SERVER_URL}",
            "--window-size=1300,880",
            f"--user-data-dir={user_data_dir}",
            "--disable-extensions",
            "--app-id=void_neural_ai"
        ]
        
        try:
            app_win = subprocess.Popen(cmd)
            print("✨ [V.O.I.D.] Desktop application is running. Close the window to exit.")
            app_win.wait()
        except KeyboardInterrupt:
            print("\nShutting down...")
    else:
        # Fallback to default browser
        import webbrowser
        print("🌐 [Browser] Opening V.O.I.D. in default web browser...")
        webbrowser.open(SERVER_URL)

    # 3. Clean up backend on desktop app close
    if server_process:
        print("🛑 [Backend] Gracefully closing local Python engine...")
        try:
            if os.name == "nt":
                subprocess.call(["taskkill", "/F", "/T", "/PID", str(server_process.pid)],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                server_process.terminate()
        except Exception:
            pass

    print("👋 V.O.I.D. Desktop App closed.")

if __name__ == "__main__":
    main()
