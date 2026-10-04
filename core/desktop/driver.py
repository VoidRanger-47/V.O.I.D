# core/desktop/driver.py
"""
V.O.I.D. Native Windows Desktop GUI Automation Driver.
Provides precision OS window management, cursor manipulation, unicode keyboard input,
and visual grounding with emergency corner failsafe guards.
"""

import os
import sys
import time
import math
import ctypes
import logging
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("VOID.DesktopDriver")

# Windows APIs
try:
    import win32gui
    import win32con
    import win32api
    import win32process
    import psutil
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False
    logger.warning("pywin32 not found. Native Windows desktop features will operate in fallback mode.")

try:
    from PIL import Image, ImageGrab
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


class FailsafeTriggeredError(Exception):
    """Raised when user triggers emergency failsafe (e.g. mouse in screen corner)."""
    pass


class DesktopDriver:
    """
    High-precision Desktop GUI Driver for Windows OS.
    Executes controlled window manipulation, cursor actions, keyboard input, and screen captures.
    """
    _instance: Optional['DesktopDriver'] = None

    # Virtual key mapping for standard keyboard shortcuts
    VK_MAPPING: Dict[str, int] = {
        "enter": 0x0D,
        "return": 0x0D,
        "esc": 0x1B,
        "escape": 0x1B,
        "tab": 0x09,
        "space": 0x20,
        "backspace": 0x08,
        "delete": 0x2E,
        "del": 0x2E,
        "up": 0x26,
        "down": 0x28,
        "left": 0x25,
        "right": 0x27,
        "home": 0x24,
        "end": 0x23,
        "pageup": 0x21,
        "pagedown": 0x22,
        "ctrl": 0x11,
        "control": 0x11,
        "alt": 0x12,
        "shift": 0x10,
        "win": 0x5B,
        "windows": 0x5B,
        "f1": 0x70, "f2": 0x71, "f3": 0x72, "f4": 0x73,
        "f5": 0x74, "f6": 0x75, "f7": 0x76, "f8": 0x77,
        "f9": 0x78, "f10": 0x79, "f11": 0x7A, "f12": 0x7B
    }

    def __init__(self, enable_failsafe: bool = True):
        self.enable_failsafe = enable_failsafe
        self._attach_desktop()
        self._setup_dpi_awareness()

    @classmethod
    def get_instance(cls) -> 'DesktopDriver':
        if cls._instance is None:
            cls._instance = DesktopDriver()
        return cls._instance

    def _attach_desktop(self):
        """Attaches current thread to user's interactive 'default' desktop on WinSta0."""
        if WIN32_AVAILABLE:
            try:
                user32 = ctypes.windll.user32
                DESKTOP_ALL = 0x01FF
                h_default = user32.OpenDesktopW("default", 0, False, DESKTOP_ALL)
                if h_default:
                    user32.SetThreadDesktop(h_default)
            except Exception as e:
                logger.debug(f"Could not switch thread desktop: {e}")

    def _setup_dpi_awareness(self):
        """Ensures coordinates align with actual physical screen pixels under Windows DPI scaling."""
        if WIN32_AVAILABLE:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
            except Exception:
                try:
                    ctypes.windll.user32.SetProcessDPIAware()
                except Exception:
                    pass

    def check_failsafe(self):
        """Emergency guard: Checks if the mouse cursor is at the upper-left (0, 0) corner."""
        if not self.enable_failsafe or not WIN32_AVAILABLE:
            return
        x, y = win32api.GetCursorPos()
        if x <= 5 and y <= 5:
            raise FailsafeTriggeredError(f"Emergency Failsafe triggered: Cursor detected at ({x}, {y}) corner.")

    # =========================================================================
    # SCREEN INFORMATION & CAPTURE
    # =========================================================================

    def get_screen_size(self) -> Tuple[int, int]:
        """Returns (width, height) of the primary display."""
        if WIN32_AVAILABLE:
            user32 = ctypes.windll.user32
            return user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        return (1920, 1080)

    def capture_screen(self, region: Optional[Tuple[int, int, int, int]] = None) -> Optional[Any]:
        """
        Captures screenshot of the entire screen or a specific region (left, top, right, bottom).
        Returns a PIL Image or None.
        """
        if not PIL_AVAILABLE:
            return None
        self._attach_desktop()
        try:
            if region:
                return ImageGrab.grab(bbox=region, all_screens=True)
            return ImageGrab.grab(all_screens=True)
        except Exception as e:
            logger.debug(f"Direct ImageGrab failed, trying primary screen: {e}")
            try:
                return ImageGrab.grab()
            except Exception as ex:
                logger.error(f"Screenshot capture failed: {ex}")
                return None

    # =========================================================================
    # WINDOW MANAGEMENT
    # =========================================================================

    def list_windows(self, visible_only: bool = True) -> List[Dict[str, Any]]:
        """
        Enumerates top-level desktop windows.
        Filters out invisible/zero-dimension auxiliary handles.
        """
        if not WIN32_AVAILABLE:
            return []

        self._attach_desktop()
        windows: List[Dict[str, Any]] = []

        def enum_handler(hwnd, extra):
            if visible_only and not win32gui.IsWindowVisible(hwnd):
                return True

            title = win32gui.GetWindowText(hwnd).strip()
            if visible_only and not title:
                return True

            # Ignore tooltips, menus, and hidden utility frames
            rect = win32gui.GetWindowRect(hwnd)
            width = rect[2] - rect[0]
            height = rect[3] - rect[1]
            if visible_only and (width <= 10 or height <= 10):
                return True

            # Get process info
            pid = 0
            process_name = "unknown"
            try:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid > 0:
                    p = psutil.Process(pid)
                    process_name = p.name()
            except Exception:
                pass

            # Filter common system invisible background overlays
            if process_name.lower() in ["shellexperiencehost.exe", "searchhost.exe"] and not title:
                return True

            windows.append({
                "hwnd": hwnd,
                "title": title,
                "process_name": process_name,
                "pid": pid,
                "rect": {
                    "left": rect[0],
                    "top": rect[1],
                    "right": rect[2],
                    "bottom": rect[3],
                    "width": width,
                    "height": height
                },
                "is_minimized": win32gui.IsIconic(hwnd) != 0,
                "is_foreground": hwnd == win32gui.GetForegroundWindow()
            })
            return True

        win32gui.EnumWindows(enum_handler, None)
        return windows

    def find_window(self, query: str) -> Optional[Dict[str, Any]]:
        """Finds a window by title keyword, process name, or HWND integer."""
        windows = self.list_windows(visible_only=True)
        query_str = str(query).strip().lower()

        # Check HWND exact match
        if query_str.isdigit():
            target_hwnd = int(query_str)
            for w in windows:
                if w["hwnd"] == target_hwnd:
                    return w

        # Search by exact or partial title
        for w in windows:
            if query_str in w["title"].lower():
                return w

        # Search by process name
        for w in windows:
            if query_str in w["process_name"].lower():
                return w

        return None

    def focus_window(self, target: str) -> bool:
        """Brings the designated window to the foreground and restores it if minimized."""
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        win = self.find_window(target)
        if not win:
            logger.warning(f"Window matching '{target}' was not found.")
            return False

        hwnd = win["hwnd"]
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            else:
                win32gui.ShowWindow(hwnd, win32con.SW_SHOW)

            # Windows requires special key hook or foreground unlock if calling from background thread
            ctypes.windll.user32.AllowSetForegroundWindow(win32process.GetWindowThreadProcessId(hwnd)[1])
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.1)
            return True
        except Exception as e:
            logger.error(f"Failed to focus window {hwnd}: {e}")
            return False

    def minimize_window(self, target: str) -> bool:
        """Minimizes the requested window."""
        win = self.find_window(target)
        if not win or not WIN32_AVAILABLE:
            return False
        win32gui.ShowWindow(win["hwnd"], win32con.SW_MINIMIZE)
        return True

    def maximize_window(self, target: str) -> bool:
        """Maximizes the requested window."""
        win = self.find_window(target)
        if not win or not WIN32_AVAILABLE:
            return False
        win32gui.ShowWindow(win["hwnd"], win32con.SW_MAXIMIZE)
        return True

    def close_window(self, target: str) -> bool:
        """Sends a gentle WM_CLOSE message to close the application window."""
        win = self.find_window(target)
        if not win or not WIN32_AVAILABLE:
            return False
        win32gui.PostMessage(win["hwnd"], win32con.WM_CLOSE, 0, 0)
        return True

    # =========================================================================
    # MOUSE CONTROLS
    # =========================================================================

    def get_cursor_position(self) -> Tuple[int, int]:
        """Returns the current mouse cursor (x, y) coordinates."""
        if WIN32_AVAILABLE:
            return win32api.GetCursorPos()
        return (0, 0)

    def mouse_move(self, x: int, y: int, smooth: bool = False, steps: int = 15) -> bool:
        """Moves cursor to (x, y) position."""
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        if not smooth:
            win32api.SetCursorPos((int(x), int(y)))
            return True

        cur_x, cur_y = self.get_cursor_position()
        for i in range(1, steps + 1):
            self.check_failsafe()
            t = i / steps
            # Smooth ease-in-out curve
            ease = 0.5 - 0.5 * math.cos(math.pi * t)
            nx = int(cur_x + (x - cur_x) * ease)
            ny = int(cur_y + (y - cur_y) * ease)
            win32api.SetCursorPos((nx, ny))
            time.sleep(0.01)

        win32api.SetCursorPos((int(x), int(y)))
        return True

    def mouse_click(self, x: Optional[int] = None, y: Optional[int] = None, button: str = "left") -> bool:
        """Clicks at (x, y) or the current cursor position."""
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        if x is not None and y is not None:
            self.mouse_move(x, y)
            time.sleep(0.05)

        btn = button.lower()
        if btn == "left":
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            time.sleep(0.03)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif btn == "right":
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            time.sleep(0.03)
            win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
        elif btn in ["double", "double_left"]:
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
            time.sleep(0.08)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
            win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        elif btn == "middle":
            win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
            time.sleep(0.03)
            win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
        return True

    def mouse_drag(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.3) -> bool:
        """Drags mouse from start coordinates to end coordinates."""
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        self.mouse_move(start_x, start_y)
        time.sleep(0.05)

        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        self.mouse_move(end_x, end_y, smooth=True, steps=max(10, int(duration * 40)))
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True

    def mouse_scroll(self, clicks: int, direction: str = "down") -> bool:
        """Scrolls mouse wheel by designated click units."""
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        delta = -120 * clicks if direction.lower() == "down" else 120 * clicks
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        return True

    # =========================================================================
    # KEYBOARD CONTROLS
    # =========================================================================

    def _get_vk_code(self, key: str) -> Optional[int]:
        """Resolves key string to Windows Virtual Key (VK) code."""
        key_clean = key.lower().strip()
        if key_clean in self.VK_MAPPING:
            return self.VK_MAPPING[key_clean]
        if len(key_clean) == 1:
            # Alphabetic / numeric
            char = key_clean.upper()
            return ord(char)
        return None

    def key_down(self, key: str) -> bool:
        """Holds a key down."""
        if not WIN32_AVAILABLE:
            return False
        vk = self._get_vk_code(key)
        if vk is not None:
            win32api.keybd_event(vk, 0, 0, 0)
            return True
        return False

    def key_up(self, key: str) -> bool:
        """Releases a key."""
        if not WIN32_AVAILABLE:
            return False
        vk = self._get_vk_code(key)
        if vk is not None:
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)
            return True
        return False

    def press_key(self, key: str) -> bool:
        """Presses and releases a single key."""
        self.check_failsafe()
        res = self.key_down(key)
        time.sleep(0.03)
        self.key_up(key)
        return res

    def hotkey(self, keys: List[str]) -> bool:
        """
        Executes a keyboard combination in sequence (e.g. ["ctrl", "c"] or ["win", "r"]).
        """
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        pressed = []
        try:
            for k in keys:
                if self.key_down(k):
                    pressed.append(k)
                    time.sleep(0.02)
            time.sleep(0.05)
        finally:
            # Always release keys in reverse order
            for k in reversed(pressed):
                self.key_up(k)
                time.sleep(0.02)
        return True

    def type_text(self, text: str, delay_ms: int = 15) -> bool:
        """
        Types Unicode text accurately using Windows SendInput unicode events.
        Does not pollute the user's clipboard.
        """
        if not WIN32_AVAILABLE:
            return False

        self.check_failsafe()
        user32 = ctypes.windll.user32

        # Setup ctypes structures for SendInput
        PUL = ctypes.POINTER(ctypes.c_ulong)
        class KEYBDINPUT(ctypes.Structure):
            _fields_ = [
                ("wVk", ctypes.c_ushort),
                ("wScan", ctypes.c_ushort),
                ("dwFlags", ctypes.c_ulong),
                ("time", ctypes.c_ulong),
                ("dwExtraInfo", PUL)
            ]

        class INPUT(ctypes.Structure):
            class _INPUT(ctypes.Union):
                _fields_ = [("ki", KEYBDINPUT)]
            _anonymous_ = ("_input",)
            _fields_ = [
                ("type", ctypes.c_ulong),
                ("_input", _INPUT)
            ]

        KEYEVENTF_UNICODE = 0x0004
        KEYEVENTF_KEYUP = 0x0002
        INPUT_KEYBOARD = 1

        for char in text:
            self.check_failsafe()
            code = ord(char)
            
            # Key down
            inp_down = INPUT()
            inp_down.type = INPUT_KEYBOARD
            inp_down.ki.wVk = 0
            inp_down.ki.wScan = code
            inp_down.ki.dwFlags = KEYEVENTF_UNICODE
            user32.SendInput(1, ctypes.byref(inp_down), ctypes.sizeof(inp_down))

            # Key up
            inp_up = INPUT()
            inp_up.type = INPUT_KEYBOARD
            inp_up.ki.wVk = 0
            inp_up.ki.wScan = code
            inp_up.ki.dwFlags = KEYEVENTF_UNICODE | KEYEVENTF_KEYUP
            user32.SendInput(1, ctypes.byref(inp_up), ctypes.sizeof(inp_up))

            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)

        return True


# Global Singleton Driver
desktop_driver = DesktopDriver.get_instance()
