# skills/computer_control.py
import subprocess
import os
import sys
import platform
import psutil
import shutil
import re
import time
import webbrowser
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

# Dangerous / Destructive system commands that are strictly disallowed
BLOCKED_COMMANDS = {
    "rm", "del", "erase", "format", "diskpart", "shutdown", "reboot",
    "regedit", "vssadmin", "bcdedit", "kill -9", "pkill -9", "taskkill /f"
}

# Extensive Canonical Slang, Acronyms, Protocol URIs, and Web Fallbacks
CANONICAL_APP_CATALOG: Dict[str, Dict[str, Any]] = {
    # --- SOCIAL & MESSAGING ---
    "instagram": {
        "display": "Instagram",
        "aliases": ["insta", "ig", "instagram app"],
        "windows": ["instagram:", "instagram.exe", "Instagram"],
        "uris": ["instagram://", "instagram:"],
        "web": "https://www.instagram.com"
    },
    "telegram": {
        "display": "Telegram",
        "aliases": ["tg", "telegram desktop", "tele"],
        "windows": ["telegram.exe", "Telegram.exe", "Telegram"],
        "uris": ["tg://", "telegram:"],
        "web": "https://web.telegram.org"
    },
    "whatsapp": {
        "display": "WhatsApp",
        "aliases": ["wa", "wp", "whatsapp desktop", "what's app"],
        "windows": ["whatsapp:", "WhatsApp.exe", "whatsapp.exe", "WhatsApp"],
        "uris": ["whatsapp://", "whatsapp:"],
        "web": "https://web.whatsapp.com"
    },
    "discord": {
        "display": "Discord",
        "aliases": ["dc"],
        "windows": [
            "discord:",
            os.path.expandvars(r"%LocalAppData%\Discord\Update.exe --processStart Discord.exe"),
            "Discord.exe",
            "discord.exe"
        ],
        "uris": ["discord://", "discord:"],
        "web": "https://discord.com/app"
    },
    "slack": {
        "display": "Slack",
        "aliases": [],
        "windows": ["slack:", "slack.exe", "Slack.exe", "slack"],
        "uris": ["slack://", "slack:"],
        "web": "https://app.slack.com"
    },
    "teams": {
        "display": "Microsoft Teams",
        "aliases": ["ms teams", "msteams"],
        "windows": ["ms-teams:", "teams.exe", "Teams.exe", "teams"],
        "uris": ["ms-teams:"],
        "web": "https://teams.microsoft.com"
    },
    "twitter": {
        "display": "Twitter / X",
        "aliases": ["x", "tweet", "twitter app"],
        "windows": ["twitter:", "x:"],
        "uris": ["twitter://", "x://"],
        "web": "https://x.com"
    },
    "reddit": {
        "display": "Reddit",
        "aliases": [],
        "windows": ["reddit:"],
        "uris": ["reddit:"],
        "web": "https://www.reddit.com"
    },
    "snapchat": {
        "display": "Snapchat",
        "aliases": ["snap"],
        "windows": ["snapchat:"],
        "uris": ["snapchat:"],
        "web": "https://web.snapchat.com"
    },
    "tiktok": {
        "display": "TikTok",
        "aliases": ["tt"],
        "windows": ["tiktok:"],
        "uris": ["tiktok:"],
        "web": "https://www.tiktok.com"
    },
    "linkedin": {
        "display": "LinkedIn",
        "aliases": [],
        "windows": [],
        "uris": ["linkedin:"],
        "web": "https://www.linkedin.com"
    },

    # --- MEDIA & STREAMING ---
    "spotify": {
        "display": "Spotify",
        "aliases": ["spot"],
        "windows": ["spotify:", "spotify.exe", "Spotify.exe", "spotify"],
        "uris": ["spotify://", "spotify:"],
        "web": "https://open.spotify.com"
    },
    "youtube": {
        "display": "YouTube",
        "aliases": ["yt", "you tube"],
        "windows": ["youtube:"],
        "uris": ["youtube:", "vnd.youtube:"],
        "web": "https://www.youtube.com"
    },
    "netflix": {
        "display": "Netflix",
        "aliases": [],
        "windows": ["netflix:"],
        "uris": ["netflix:"],
        "web": "https://www.netflix.com"
    },
    "prime video": {
        "display": "Amazon Prime Video",
        "aliases": ["prime", "amazon prime", "amazon video"],
        "windows": ["primevideo:"],
        "uris": ["primevideo:"],
        "web": "https://www.primevideo.com"
    },
    "vlc": {
        "display": "VLC Media Player",
        "aliases": ["vlc player"],
        "windows": ["vlc.exe", "vlc", os.path.expandvars(r"%ProgramFiles%\VideoLAN\VLC\vlc.exe")],
        "uris": ["vlc://"],
        "web": None
    },
    "steam": {
        "display": "Steam",
        "aliases": [],
        "windows": ["steam:", "steam.exe", "Steam.exe", "steam"],
        "uris": ["steam://", "steam:"],
        "web": "https://store.steampowered.com"
    },
    "epic games": {
        "display": "Epic Games Launcher",
        "aliases": ["epic", "epic games launcher", "epic store"],
        "windows": ["com.epicgames.launcher:", "EpicGamesLauncher.exe"],
        "uris": ["com.epicgames.launcher:"],
        "web": "https://store.epicgames.com"
    },

    # --- PRODUCTIVITY & DEV ---
    "vscode": {
        "display": "Visual Studio Code",
        "aliases": ["vs code", "visual studio code", "code"],
        "windows": [
            os.path.expandvars(r"%LocalAppData%\Programs\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%ProgramFiles%\Microsoft VS Code\Code.exe"),
            os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft VS Code\Code.exe"),
            "Code.exe",
            "vscode://",
            "code.cmd"
        ],
        "uris": ["vscode://"],
        "web": "https://vscode.dev"
    },
    "notepad": {
        "display": "Notepad",
        "aliases": ["text editor"],
        "windows": ["notepad.exe"],
        "uris": [],
        "web": None
    },
    "calculator": {
        "display": "Calculator",
        "aliases": ["calc", "calc.exe"],
        "windows": ["calculator:", "calc.exe"],
        "uris": ["calculator:"],
        "web": None
    },
    "explorer": {
        "display": "File Explorer",
        "aliases": ["file explorer", "files", "my files", "folder", "my computer"],
        "windows": ["explorer.exe"],
        "uris": [],
        "web": None
    },
    "terminal": {
        "display": "Terminal",
        "aliases": ["windows terminal", "term", "wt"],
        "windows": ["wt.exe", "powershell.exe", "cmd.exe"],
        "uris": [],
        "web": None
    },
    "powershell": {
        "display": "PowerShell",
        "aliases": ["pwsh"],
        "windows": ["powershell.exe", "pwsh.exe"],
        "uris": [],
        "web": None
    },
    "cmd": {
        "display": "Command Prompt",
        "aliases": ["command prompt", "prompt"],
        "windows": ["cmd.exe"],
        "uris": [],
        "web": None
    },
    "word": {
        "display": "Microsoft Word",
        "aliases": ["ms word", "winword"],
        "windows": ["winword.exe", "word"],
        "uris": ["ms-word:"],
        "web": "https://office.live.com/start/Word.aspx"
    },
    "excel": {
        "display": "Microsoft Excel",
        "aliases": ["ms excel"],
        "windows": ["excel.exe"],
        "uris": ["ms-excel:"],
        "web": "https://office.live.com/start/Excel.aspx"
    },
    "powerpoint": {
        "display": "Microsoft PowerPoint",
        "aliases": ["ppt", "ms powerpoint"],
        "windows": ["powerpnt.exe"],
        "uris": ["ms-powerpoint:"],
        "web": "https://office.live.com/start/PowerPoint.aspx"
    },
    "obsidian": {
        "display": "Obsidian",
        "aliases": ["notes"],
        "windows": ["obsidian:", "Obsidian.exe", "obsidian"],
        "uris": ["obsidian://"],
        "web": None
    },
    "notion": {
        "display": "Notion",
        "aliases": [],
        "windows": ["notion:", "Notion.exe", "notion"],
        "uris": ["notion://"],
        "web": "https://www.notion.so"
    },
    "figma": {
        "display": "Figma",
        "aliases": [],
        "windows": ["Figma.exe", "figma"],
        "uris": ["figma://"],
        "web": "https://www.figma.com"
    },
    "blender": {
        "display": "Blender",
        "aliases": [],
        "windows": ["blender.exe", "blender", "blender-launcher.exe"],
        "uris": [],
        "web": None
    },
    "postman": {
        "display": "Postman",
        "aliases": [],
        "windows": ["Postman.exe", "postman.exe", "postman:"],
        "uris": ["postman://"],
        "web": "https://web.postman.co"
    },
    "davinci resolve": {
        "display": "DaVinci Resolve",
        "aliases": ["davinci", "resolve"],
        "windows": ["Resolve.exe", "resolve.exe"],
        "uris": [],
        "web": None
    },
    "bluestacks": {
        "display": "BlueStacks 5",
        "aliases": ["bluestacks 5", "bs5", "android emulator"],
        "windows": ["HD-Player.exe", "BlueStacks.exe"],
        "uris": [],
        "web": None
    },

    # --- BROWSERS ---
    "chrome": {
        "display": "Google Chrome",
        "aliases": ["google chrome", "google"],
        "windows": ["chrome.exe", "chrome", "google-chrome"],
        "uris": ["googlechrome:"],
        "web": None
    },
    "edge": {
        "display": "Microsoft Edge",
        "aliases": ["msedge", "microsoft edge"],
        "windows": ["msedge.exe", "msedge", "microsoft-edge:"],
        "uris": ["microsoft-edge:"],
        "web": None
    },
    "firefox": {
        "display": "Mozilla Firefox",
        "aliases": ["mozilla firefox", "ff"],
        "windows": ["firefox.exe", "firefox"],
        "uris": ["firefox:"],
        "web": None
    },
    "brave": {
        "display": "Brave Browser",
        "aliases": ["brave"],
        "windows": ["brave.exe", "brave"],
        "uris": ["brave:"],
        "web": None
    },

    # --- AI PLATFORMS ---
    "chatgpt": {
        "display": "ChatGPT",
        "aliases": ["gpt", "openai"],
        "windows": ["chatgpt:"],
        "uris": ["chatgpt:"],
        "web": "https://chatgpt.com"
    },
    "gemini": {
        "display": "Google Gemini",
        "aliases": ["google gemini"],
        "windows": [],
        "uris": [],
        "web": "https://gemini.google.com"
    },
    "claude": {
        "display": "Claude AI",
        "aliases": ["anthropic claude"],
        "windows": ["claude:"],
        "uris": ["claude:"],
        "web": "https://claude.ai"
    },

    # --- SYSTEM & UTILITIES ---
    "settings": {
        "display": "Windows Settings",
        "aliases": ["win settings", "pc settings", "system settings"],
        "windows": ["ms-settings:"],
        "uris": ["ms-settings:"],
        "web": None
    },
    "task manager": {
        "display": "Task Manager",
        "aliases": ["taskmgr", "task manager", "tasks"],
        "windows": ["taskmgr.exe"],
        "uris": [],
        "web": None
    },
    "camera": {
        "display": "Camera",
        "aliases": ["webcam", "win camera"],
        "windows": ["microsoft.windows.camera:"],
        "uris": ["microsoft.windows.camera:"],
        "web": None
    },
    "snipping tool": {
        "display": "Snipping Tool / Screen Clip",
        "aliases": ["snip", "screenshot", "screen capture", "snippingtool"],
        "windows": ["ms-screenclip:", "SnippingTool.exe"],
        "uris": ["ms-screenclip:"],
        "web": None
    },
    "clock": {
        "display": "Clock & Alarm",
        "aliases": ["alarm", "timer", "stopwatch"],
        "windows": ["ms-clock:"],
        "uris": ["ms-clock:"],
        "web": None
    },
    "control panel": {
        "display": "Control Panel",
        "aliases": ["cpanel"],
        "windows": ["control.exe"],
        "uris": [],
        "web": None
    },
    "paint": {
        "display": "Paint",
        "aliases": ["mspaint", "paint app"],
        "windows": ["mspaint.exe", "ms-paint:"],
        "uris": ["ms-paint:"],
        "web": None
    }
}


class UniversalAppRegistry:
    """
    Scans, indexes, and caches all applications across Host PC and connected devices.
    """
    _instance: Optional['UniversalAppRegistry'] = None

    def __init__(self):
        self.cached_apps: Dict[str, Dict[str, Any]] = {}
        self.last_scan_time: float = 0.0
        self.cache_ttl: float = 120.0  # Re-index every 2 minutes
        self.system = platform.system().lower()

    @classmethod
    def get_instance(cls) -> 'UniversalAppRegistry':
        if cls._instance is None:
            cls._instance = UniversalAppRegistry()
        return cls._instance

    def scan_installed_apps(self, force: bool = False) -> Dict[str, Dict[str, Any]]:
        """
        Deep scan of all system applications on Host PC.
        """
        now = time.time()
        if not force and self.cached_apps and (now - self.last_scan_time < self.cache_ttl):
            return self.cached_apps

        apps: Dict[str, Dict[str, Any]] = {}

        # 1. Seed with Canonical App Catalog
        for key, info in CANONICAL_APP_CATALOG.items():
            entry = {
                "name": info["display"],
                "key": key,
                "type": "catalog",
                "targets": info.get("windows" if self.system == "windows" else "uris", []),
                "uris": info.get("uris", []),
                "web": info.get("web"),
                "aliases": info.get("aliases", [])
            }
            apps[key] = entry
            for alias in info.get("aliases", []):
                apps[alias.lower()] = entry

        # 2. Windows Deep Scan
        if self.system == "windows":
            # 2a. Start Menu Shortcuts (.lnk and .url)
            start_dirs = [
                os.path.expandvars(r'%ProgramData%\Microsoft\Windows\Start Menu\Programs'),
                os.path.expandvars(r'%AppData%\Microsoft\Windows\Start Menu\Programs'),
                os.path.expandvars(r'%UserProfile%\Desktop'),
                os.path.expandvars(r'%Public%\Desktop'),
            ]
            for sdir in start_dirs:
                if os.path.isdir(sdir):
                    for root, _, files in os.walk(sdir):
                        for f in files:
                            if f.lower().endswith(('.lnk', '.url')):
                                name = os.path.splitext(f)[0].strip()
                                full_path = os.path.join(root, f)
                                clean_key = name.lower()
                                apps[clean_key] = {
                                    "name": name,
                                    "key": clean_key,
                                    "target": full_path,
                                    "type": "shortcut",
                                    "source": "start_menu"
                                }

            # 2b. Registry App Paths
            try:
                import winreg
                for root_key in [winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE]:
                    try:
                        key_path = r'SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths'
                        with winreg.OpenKey(root_key, key_path) as k:
                            num_subkeys, _, _ = winreg.QueryInfoKey(k)
                            for i in range(num_subkeys):
                                try:
                                    subkey_name = winreg.EnumKey(k, i)
                                    with winreg.OpenKey(k, subkey_name) as sk:
                                        val, _ = winreg.QueryValueEx(sk, '')
                                        if val and os.path.exists(val):
                                            name = os.path.splitext(subkey_name)[0]
                                            clean_key = name.lower()
                                            if clean_key not in apps:
                                                apps[clean_key] = {
                                                    "name": name,
                                                    "key": clean_key,
                                                    "target": val,
                                                    "type": "executable",
                                                    "source": "registry_app_paths"
                                                }
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass

            # 2c. Windows Registry Uninstall Keys (All installed software)
            try:
                import winreg
                uninstall_paths = [
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_LOCAL_MACHINE, r"Software\Wow6432Node\Microsoft\Windows\CurrentVersion\Uninstall"),
                    (winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
                ]
                for root_key, path in uninstall_paths:
                    try:
                        with winreg.OpenKey(root_key, path) as k:
                            num_subkeys, _, _ = winreg.QueryInfoKey(k)
                            for i in range(num_subkeys):
                                try:
                                    subkey_name = winreg.EnumKey(k, i)
                                    with winreg.OpenKey(k, subkey_name) as sk:
                                        try:
                                            disp_name, _ = winreg.QueryValueEx(sk, "DisplayName")
                                        except Exception:
                                            disp_name = None
                                        try:
                                            icon, _ = winreg.QueryValueEx(sk, "DisplayIcon")
                                            if icon and "," in icon:
                                                icon = icon.split(",")[0].strip('"')
                                        except Exception:
                                            icon = None
                                        try:
                                            loc, _ = winreg.QueryValueEx(sk, "InstallLocation")
                                        except Exception:
                                            loc = None

                                        target = None
                                        if icon and os.path.exists(icon) and icon.lower().endswith('.exe'):
                                            target = icon
                                        elif loc and os.path.isdir(loc):
                                            for f in os.listdir(loc):
                                                if f.lower().endswith('.exe'):
                                                    target = os.path.join(loc, f)
                                                    break

                                        if disp_name and target:
                                            clean_key = disp_name.lower().strip()
                                            apps[clean_key] = {
                                                "name": disp_name,
                                                "key": clean_key,
                                                "target": target,
                                                "type": "installed_app",
                                                "source": "uninstall_registry"
                                            }
                                except Exception:
                                    pass
                    except Exception:
                        pass
            except Exception:
                pass

            # 2d. PowerShell Get-StartApps (Universal Store / UWP / MSIX / Desktop apps)
            try:
                import json
                res = subprocess.run(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", "Get-StartApps | ConvertTo-Json -Compress"],
                    capture_output=True, text=True, timeout=4
                )
                if res.returncode == 0 and res.stdout.strip():
                    data = json.loads(res.stdout)
                    if isinstance(data, dict):
                        data = [data]
                    for item in data:
                        n = item.get("Name")
                        app_id = item.get("AppID")
                        if n and app_id:
                            clean_key = n.lower().strip()
                            apps[clean_key] = {
                                "name": n,
                                "key": clean_key,
                                "target": f"shell:AppsFolder\\{app_id}",
                                "type": "uwp_or_start_app",
                                "source": "get_startapps"
                            }
            except Exception:
                pass

        elif self.system == "darwin":
            # macOS /Applications
            app_dirs = ["/Applications", os.path.expanduser("~/Applications"), "/System/Applications"]
            for adir in app_dirs:
                if os.path.isdir(adir):
                    for item in os.listdir(adir):
                        if item.endswith(".app"):
                            name = os.path.splitext(item)[0]
                            apps[name.lower()] = {
                                "name": name,
                                "key": name.lower(),
                                "target": os.path.join(adir, item),
                                "type": "darwin_app",
                                "source": "applications"
                            }

        else:
            # Linux .desktop files
            desk_dirs = ["/usr/share/applications", os.path.expanduser("~/.local/share/applications")]
            for ddir in desk_dirs:
                if os.path.isdir(ddir):
                    for item in os.listdir(ddir):
                        if item.endswith(".desktop"):
                            name = os.path.splitext(item)[0]
                            apps[name.lower()] = {
                                "name": name,
                                "key": name.lower(),
                                "target": os.path.join(ddir, item),
                                "type": "linux_desktop",
                                "source": "xdg_desktop"
                            }

        self.cached_apps = apps
        self.last_scan_time = now
        return apps

    def resolve(self, query: str) -> Optional[Tuple[str, str, str, Optional[str]]]:
        """
        Fuzzy resolves an application query to a concrete launch target.
        Returns: (display_name, launch_target, launch_mode, web_fallback_url)
        """
        clean = query.lower().strip()
        clean = re.sub(r'^(?:open|launch|start|run|switch to)\s+', '', clean).strip()

        # Check blocked commands
        if any(b in clean for b in BLOCKED_COMMANDS):
            return None

        apps = self.scan_installed_apps()

        # 1. Exact Match in Registry / Catalog
        if clean in apps:
            app = apps[clean]
            return self._build_resolution(app)

        # 2. Check Catalog Aliases
        for key, entry in CANONICAL_APP_CATALOG.items():
            if clean == key or clean in entry.get("aliases", []):
                # Try finding if installed under name
                if key in apps:
                    return self._build_resolution(apps[key])
                return (entry["display"], entry.get("uris", [""])[0] or entry.get("web", ""), "uri" if entry.get("uris") else "web", entry.get("web"))

        # 3. Substring / Word Match across all indexed apps
        clean_condensed = re.sub(r"[\s\-_]+", "", clean)
        best_match = None
        best_score = 0

        for name_key, entry in apps.items():
            entry_condensed = re.sub(r"[\s\-_]+", "", name_key)
            # Exact condensed match
            if clean_condensed == entry_condensed:
                return self._build_resolution(entry)
            
            # Starts with or contains
            if name_key.startswith(clean) or entry_condensed.startswith(clean_condensed):
                score = 90 - len(name_key)
                if score > best_score:
                    best_score = score
                    best_match = entry
            elif clean in name_key or clean_condensed in entry_condensed:
                score = 70 - len(name_key)
                if score > best_score:
                    best_score = score
                    best_match = entry

        if best_match:
            return self._build_resolution(best_match)

        # 4. Check system PATH
        path_exec = shutil.which(clean) or shutil.which(f"{clean}.exe") or shutil.which(f"{clean}.cmd")
        if path_exec:
            return (clean.title(), path_exec, "startfile" if self.system == "windows" else "posix", None)

        # 5. Check if query is a direct protocol or website
        if clean.endswith(":") or clean.endswith("://"):
            return (clean.title(), clean, "uri", None)

        return None

    def _build_resolution(self, entry: Dict[str, Any]) -> Tuple[str, str, str, Optional[str]]:
        disp = entry.get("name", "Application")
        web = entry.get("web")

        if entry.get("target"):
            t = entry["target"]
            if str(t).startswith("shell:AppsFolder"):
                return (disp, t, "uwp", web)
            if str(t).endswith((".lnk", ".url", ".exe", ".cmd", ".bat")):
                return (disp, t, "startfile", web)
            if str(t).endswith(".app"):
                return (disp, t, "darwin_app", web)
            return (disp, t, "startfile", web)

        if entry.get("targets"):
            for cand in entry["targets"]:
                if os.path.isabs(cand) and os.path.exists(cand):
                    return (disp, cand, "startfile", web)
                if cand.endswith(":") or cand.endswith("://"):
                    return (disp, cand, "uri", web)
                which = shutil.which(cand)
                if which:
                    return (disp, which, "startfile", web)

        if entry.get("uris"):
            return (disp, entry["uris"][0], "uri", web)

        if web:
            return (disp, web, "web", web)

        return (disp, entry.get("key", "app"), "startfile", web)


app_registry = UniversalAppRegistry.get_instance()


def extract_device_and_app(query: str) -> Tuple[str, str]:
    """
    Extracts target device ('pc', 'phone', 'all') and cleaned app target.
    Examples:
      'open insta on phone' -> ('phone', 'insta')
      'launch telegram on pc' -> ('pc', 'telegram')
      'open spotify everywhere' -> ('all', 'spotify')
      'open calculator' -> ('default', 'calculator')
    """
    low = query.lower().strip()
    low = re.sub(r'^(?:hey\s+void|void|can you|could you|please|kindly|i want void to|i want you to)\s*,?\s*', '', low)

    # Detect Device Specifier
    device = "default"
    if re.search(r'\b(?:on (?:my )?(?:phone|mobile|android|adb)|in phone)\b', low):
        device = "phone"
        low = re.sub(r'\b(?:on (?:my )?(?:phone|mobile|android|adb)|in phone)\b', '', low).strip()
    elif re.search(r'\b(?:on (?:my )?(?:pc|computer|laptop|desktop|windows)|in pc)\b', low):
        device = "pc"
        low = re.sub(r'\b(?:on (?:my )?(?:pc|computer|laptop|desktop|windows)|in pc)\b', '', low).strip()
    elif re.search(r'\b(?:on all devices|on both|everywhere|across devices)\b', low):
        device = "all"
        low = re.sub(r'\b(?:on all devices|on both|everywhere|across devices)\b', '', low).strip()

    # Extract clean target
    m = re.search(r'\b(?:open|launch|start|run|switch to)\s+([a-zA-Z0-9\+\#\s\.\-_]+)', low)
    if m:
        target = m.group(1).strip()
    else:
        target = low.replace("open", "").replace("launch", "").replace("start", "").replace("run", "").strip()

    target = re.split(r'\b(?:and|for|to|with|in|at|then|please)\b', target)[0].strip()
    return device, target


def extract_app_target(query: str) -> str:
    """Extracts application target name from query string."""
    _, target = extract_device_and_app(query)
    return target


def is_app_launch_request(query: str) -> bool:
    """
    Determines if user query is an explicit request to launch an application.
    """
    low = query.lower().strip()
    trigger_words = ["open ", "launch ", "start ", "run ", "switch to "]
    if any(low.startswith(w) or f" {w}" in low for w in trigger_words):
        _, target = extract_device_and_app(query)
        if target and len(target) >= 2:
            non_app_words = ["what", "how", "why", "who", "where", "when", "the", "source", "link", "website", "question", "file", "document"]
            if target in non_app_words:
                return False
            return True
    return False


def launch_application_on_host(app_target: str) -> Tuple[bool, str, str]:
    """
    Launches an application natively on the Host PC (Windows/macOS/Linux).
    Returns (success, display_name, message)
    """
    resolved = app_registry.resolve(app_target)
    if not resolved:
        return False, app_target, f"Could not find '{app_target}' on Host PC."

    display_name, launch_path, launch_mode, web_fallback = resolved

    try:
        sys_name = platform.system().lower()
        if sys_name == "windows":
            import ctypes
            if launch_mode == "uwp":
                # UWP / Windows Store App via explorer shell:AppsFolder
                subprocess.Popen(["explorer.exe", str(launch_path)])
            elif launch_mode == "web":
                webbrowser.open(str(launch_path))
            elif launch_mode == "uri":
                ret = ctypes.windll.shell32.ShellExecuteW(None, "open", str(launch_path), None, None, 1)
                if ret <= 32:
                    if web_fallback:
                        webbrowser.open(web_fallback)
                    else:
                        os.startfile(str(launch_path))
            else:
                ret = ctypes.windll.shell32.ShellExecuteW(None, "open", str(launch_path), None, None, 1)
                if ret <= 32:
                    if os.path.exists(str(launch_path)):
                        os.startfile(str(launch_path))
                    elif web_fallback:
                        webbrowser.open(web_fallback)
                    else:
                        subprocess.Popen([str(launch_path)], shell=True)

        elif sys_name == "darwin":
            if launch_mode == "web":
                webbrowser.open(str(launch_path))
            elif launch_mode == "darwin_app":
                subprocess.Popen(["open", "-a", str(launch_path)])
            elif launch_mode == "uri":
                subprocess.Popen(["open", str(launch_path)])
            else:
                subprocess.Popen([str(launch_path)])

        else: # Linux
            if launch_mode == "web":
                webbrowser.open(str(launch_path))
            elif launch_mode == "uri":
                subprocess.Popen(["xdg-open", str(launch_path)])
            else:
                subprocess.Popen([str(launch_path)])

        return True, display_name, f"Launched **{display_name}** (`{os.path.basename(str(launch_path)) if not str(launch_path).endswith(':') else launch_path}`)"

    except Exception as e:
        if web_fallback:
            try:
                webbrowser.open(web_fallback)
                return True, display_name, f"Launched **{display_name}** Web Application ({web_fallback})"
            except Exception:
                pass
        return False, display_name, str(e)


def launch_application(query_or_name: str) -> str:
    """
    Universal Multi-Device Application Launcher:
    Parses intent, resolves target device (PC / Phone / All Devices), and executes launch.
    """
    device_target, app_target = extract_device_and_app(query_or_name)
    if not app_target:
        app_target = query_or_name.strip()

    # Import phone controller safely
    phone_available = False
    phone_ctrl = None
    try:
        from void_phone.phone_controller import phone_controller
        phone_ctrl = phone_controller
        phone_available = phone_ctrl.bridge.is_connected()
    except Exception:
        pass

    results: List[str] = []

    # 1. Target: Explicit Phone
    if device_target == "phone":
        if not phone_available or not phone_ctrl:
            return f"📱 **Android Phone Notice**: Cannot launch **'{app_target}'** — No Android device connected via ADB."
        res = phone_ctrl.launch_app(app_target)
        return res

    # 2. Target: All Devices (Both PC and Phone)
    if device_target == "all":
        # Launch PC
        pc_ok, pc_name, pc_msg = launch_application_on_host(app_target)
        if pc_ok:
            results.append(f"💻 **Host PC**: {pc_msg}")
        else:
            results.append(f"💻 **Host PC**: ⚠️ {pc_msg}")

        # Launch Phone
        if phone_available and phone_ctrl:
            phone_res = phone_ctrl.launch_app(app_target)
            results.append(f"📱 **Android Phone**: {phone_res}")
        else:
            results.append(f"📱 **Android Phone**: ⚠️ No phone connected via ADB.")

        return "\n\n".join(results)

    # 3. Default Target: Host PC First, with Phone Cross-Device Coordination
    pc_ok, pc_name, pc_msg = launch_application_on_host(app_target)

    if pc_ok:
        report = f"🚀 **User Authorized**: Successfully launched **{pc_name}** on your screen.\n\n📍 Target: `{pc_msg}`"
        # If user has phone connected, optionally inform
        if phone_available and device_target == "phone":
            report += f"\n📱 *Tip: To open on your connected phone instead, say `Open {app_target} on phone`.*"
        return report

    # If PC launch failed but phone is connected, attempt phone launch
    if phone_available and phone_ctrl:
        phone_res = phone_ctrl.launch_app(app_target)
        if "🚀 Launched" in phone_res:
            return f"💻 *Host PC*: App not installed locally.\n📱 **Android Phone**: {phone_res}"

    # Complete fallback
    return (
        f"⚠️ Could not find or launch **'{app_target}'** on this device.\n\n"
        f"💡 *Tip: Ensure the application is installed, or try `Open {app_target} on phone` or open via browser.*"
    )


def get_local_system_stats() -> str:
    """
    Reads local hardware metrics (CPU, RAM, Disk, OS) offline.
    """
    try:
        cpu_usage = psutil.cpu_percent(interval=0.2)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        mem_used_gb = round(memory.used / (1024**3), 2)
        mem_total_gb = round(memory.total / (1024**3), 2)
        disk_free_gb = round(disk.free / (1024**3), 2)
        disk_total_gb = round(disk.total / (1024**3), 2)

        os_info = f"{platform.system()} {platform.release()} ({platform.architecture()[0]})"

        return (
            f"📊 **Local System Metrics**:\n"
            f"• **OS**: {os_info}\n"
            f"• **CPU Load**: {cpu_usage}%\n"
            f"• **RAM Usage**: {memory.percent}% ({mem_used_gb} GB / {mem_total_gb} GB)\n"
            f"• **Disk Space Free**: {disk_free_gb} GB / {disk_total_gb} GB"
        )
    except Exception as e:
        return f"System Info: {platform.system()} {platform.release()}"


def analyze_local_document(filepath: str) -> str:
    """
    Parses and summarizes local text/PDF documents offline.
    """
    clean_path = filepath.strip().strip('"').strip("'")
    if not os.path.exists(clean_path):
        return f"❌ File not found at local path: {clean_path}"

    ext = os.path.splitext(clean_path)[1].lower()

    try:
        if ext == ".pdf":
            try:
                from pdf_utils import pdf_to_text
                text = pdf_to_text(clean_path)
            except Exception:
                text = ""
        else:
            with open(clean_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()

        if not text.strip():
            return f"📄 Document '{os.path.basename(clean_path)}' is empty or could not be read."

        preview = text[:1200].strip()
        total_chars = len(text)
        return f"📄 **Local Document Analysis** [{os.path.basename(clean_path)} ({total_chars} chars)]:\n\n{preview}"
    except Exception as e:
        return f"❌ Failed to parse local document: {str(e)}"


def is_system_power_request(query: str) -> Tuple[bool, str]:
    """Detects if user is asking to shut down, restart, sleep, or abort shutdown."""
    low = query.lower().strip()
    
    # Abort / Cancel
    if any(k in low for k in ["abort shutdown", "cancel shutdown", "stop shutdown", "don't shutdown", "cancel restart"]):
        return True, "abort"
        
    # Restart / Reboot
    if any(k in low for k in [
        "restart the pc", "restart this laptop", "restart the laptop", "restart the computer",
        "restart pc", "restart laptop", "restart computer",
        "reboot the pc", "reboot this laptop", "reboot the computer", "reboot computer", "reboot pc", "reboot laptop"
    ]):
        return True, "restart"
        
    # Shutdown / Power Off / Turn Off
    if any(k in low for k in [
        "shutdown this laptop", "shutdown the laptop", "shutdown this pc", "shutdown the pc", 
        "shutdown this computer", "shutdown the computer", "shutdown computer", "shutdown laptop", "shutdown pc",
        "turn off this laptop", "turn off the laptop", "turn off the pc", "turn off this pc", 
        "turn off the computer", "turn off computer", "turn off laptop", "turn off pc",
        "power off this laptop", "power off the laptop", "power off the pc", "power off computer", "power off laptop",
        "switch off the laptop", "switch off the pc", "switch off computer", "switch off laptop",
        "shut down this laptop", "shut down the laptop", "shut down this pc", "shut down the pc",
        "shut down this computer", "shut down the computer", "shut down computer", "shut down laptop", "shut down pc"
    ]):
        return True, "shutdown"
        
    return False, ""


def execute_system_power(action: str, delay_seconds: int = 15) -> str:
    """Safely executes OS power actions (shutdown, restart, abort) with a grace delay."""
    sys_type = platform.system()
    
    if action == "abort":
        if sys_type == "Windows":
            try:
                res = subprocess.run(["shutdown", "/a"], capture_output=True, text=True)
                if res.returncode == 0:
                    return "✅ **Pending shutdown/restart cancelled successfully.** The system will remain online."
                return "ℹ️ No pending shutdown timer was active."
            except Exception as e:
                return f"❌ Error cancelling shutdown: {e}"
        else:
            subprocess.run(["shutdown", "-c"], capture_output=True)
            return "✅ **Pending shutdown cancelled.**"
            
    elif action == "shutdown":
        if sys_type == "Windows":
            try:
                cmd = ["shutdown", "/s", "/t", str(delay_seconds), "/c", f"V.O.I.D. Power Down ({delay_seconds}s timer)"]
                subprocess.Popen(cmd)
                return (
                    f"🛑 **Initiating System Shutdown in {delay_seconds} seconds...**\n\n"
                    f"⚠️ *To cancel before power off, say:* `cancel shutdown` *or run:* `shutdown /a` in terminal."
                )
            except Exception as e:
                return f"❌ Failed to initiate shutdown: {e}"
        else:
            subprocess.Popen(["shutdown", "-h", f"+{max(1, delay_seconds // 60)}"])
            return f"🛑 **System shutdown scheduled in {delay_seconds}s.** Run `shutdown -c` to cancel."
            
    elif action == "restart":
        if sys_type == "Windows":
            try:
                cmd = ["shutdown", "/r", "/t", str(delay_seconds), "/c", f"V.O.I.D. System Reboot ({delay_seconds}s timer)"]
                subprocess.Popen(cmd)
                return (
                    f"🔄 **Initiating System Restart in {delay_seconds} seconds...**\n\n"
                    f"⚠️ *To cancel before reboot, say:* `cancel shutdown` *or run:* `shutdown /a` in terminal."
                )
            except Exception as e:
                return f"❌ Failed to initiate restart: {e}"
        else:
            subprocess.Popen(["shutdown", "-r", f"+{max(1, delay_seconds // 60)}"])
            return f"🔄 **System reboot scheduled in {delay_seconds}s.**"
            
    return f"❓ Unrecognized system power action: {action}"
