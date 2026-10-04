"""
ADB Bridge for V.O.I.D.
Provides low-level Android Debug Bridge lifecycle management, device discovery,
USB and TCP/IP connection handling, and robust shell command execution.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    import adbutils
    from adbutils import AdbClient, AdbDevice
    ADBUTILS_AVAILABLE = True
except ImportError:
    ADBUTILS_AVAILABLE = False


@dataclass
class DeviceInfo:
    serial: str
    state: str  # 'device', 'offline', 'unauthorized', 'unknown'
    connection_type: str  # 'usb', 'tcpip'
    model: str = "Unknown"
    manufacturer: str = "Unknown"
    android_version: str = "Unknown"
    sdk_version: str = "Unknown"
    battery_level: Optional[int] = None
    screen_resolution: Optional[Tuple[int, int]] = None
    is_screen_on: Optional[bool] = None
    ip_address: Optional[str] = None


class ADBBridge:
    """
    Manages ADB connections, daemon lifecycle, and command execution across USB and TCP/IP.
    """
    _instance: Optional[ADBBridge] = None

    def __init__(self, preferred_serial: Optional[str] = None):
        self._preferred_serial = preferred_serial
        self._adb_path = self._locate_adb_binary()
        self._client: Optional[Any] = None
        if ADBUTILS_AVAILABLE:
            try:
                self._client = adbutils.adb
            except Exception as e:
                print(f"[ADBBridge] AdbClient init warning: {e}")

    @classmethod
    def get_instance(cls, preferred_serial: Optional[str] = None) -> ADBBridge:
        if cls._instance is None:
            cls._instance = ADBBridge(preferred_serial)
        return cls._instance

    def _locate_adb_binary(self) -> str:
        """Find the ADB executable from adbutils, PATH, or Android SDK paths."""
        # 1. Check adbutils bundled binary
        if ADBUTILS_AVAILABLE:
            try:
                path = adbutils.adb_path()
                if path and os.path.exists(path):
                    return path
            except Exception:
                pass

        # 2. Check system PATH
        path_which = shutil.which("adb")
        if path_which:
            return path_which

        # 3. Check common Android SDK platform-tools locations on Windows
        sdk_candidates = [
            os.path.expandvars(r"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Android\platform-tools\adb.exe"),
            os.path.expandvars(r"%PROGRAMFILES(X86)%\Android\platform-tools\adb.exe"),
            r"C:\platform-tools\adb.exe",
            r"C:\Android\platform-tools\adb.exe",
        ]
        for candidate in sdk_candidates:
            if os.path.exists(candidate):
                return candidate

        return "adb"  # Fallback to plain command name

    @property
    def adb_path(self) -> str:
        return self._adb_path

    def run_adb_command(self, args: List[str], timeout: float = 15.0) -> Tuple[int, str, str]:
        """Execute a raw ADB command via subprocess."""
        cmd = [self._adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", f"Command timed out after {timeout}s: {' '.join(cmd)}"
        except FileNotFoundError:
            return -1, "", f"ADB binary not found at '{self._adb_path}'"
        except Exception as e:
            return -1, "", f"Failed to execute ADB command: {str(e)}"

    def run_adb_command_raw(self, args: List[str], timeout: float = 15.0) -> Tuple[int, bytes, bytes]:
        """Execute a raw ADB command returning binary bytes (e.g. for screencap or file stream)."""
        cmd = [self._adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=False,
                timeout=timeout,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            return res.returncode, res.stdout, res.stderr
        except subprocess.TimeoutExpired:
            return -1, b"", f"Command timed out after {timeout}s: {' '.join(cmd)}".encode("utf-8")
        except FileNotFoundError:
            return -1, b"", f"ADB binary not found at '{self._adb_path}'".encode("utf-8")
        except Exception as e:
            return -1, b"", f"Failed to execute ADB command: {str(e)}".encode("utf-8")

    def start_server(self) -> bool:
        """Start the ADB server daemon."""
        code, stdout, stderr = self.run_adb_command(["start-server"])
        return code == 0

    def kill_server(self) -> bool:
        """Kill the ADB server daemon."""
        code, stdout, stderr = self.run_adb_command(["kill-server"])
        return code == 0

    def list_devices(self) -> List[DeviceInfo]:
        """List all connected ADB devices with detailed status."""
        self.start_server()
        devices: List[DeviceInfo] = []

        code, stdout, stderr = self.run_adb_command(["devices", "-l"])
        if code != 0:
            return devices

        for line in stdout.splitlines():
            line = line.strip()
            if not line or line.startswith("List of devices attached") or line.startswith("*"):
                continue

            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]
                conn_type = "tcpip" if ":" in serial else "usb"

                model = "Unknown"
                manufacturer = "Unknown"
                for part in parts[2:]:
                    if part.startswith("model:"):
                        model = part.split(":", 1)[1].replace("_", " ")
                    elif part.startswith("device:"):
                        manufacturer = part.split(":", 1)[1]

                dev_info = DeviceInfo(
                    serial=serial,
                    state=state,
                    connection_type=conn_type,
                    model=model,
                    manufacturer=manufacturer
                )
                devices.append(dev_info)

        return devices

    def get_active_device_serial(self, target_serial: Optional[str] = None) -> Optional[str]:
        """Resolve the active device serial from target, preferred, or first online device."""
        if target_serial:
            return target_serial
        if self._preferred_serial:
            return self._preferred_serial

        devices = self.list_devices()
        online = [d.serial for d in devices if d.state == "device"]
        if online:
            return online[0]
        if devices:
            return devices[0].serial
        return None

    def is_connected(self, serial: Optional[str] = None) -> bool:
        """Check if at least one authorized Android device is connected."""
        target = self.get_active_device_serial(serial)
        if not target:
            return False
        devices = self.list_devices()
        return any(d.serial == target and d.state == "device" for d in devices)

    def connect_tcp(self, host: str, port: int = 5555) -> Tuple[bool, str]:
        """Connect to an Android device over WiFi / TCP/IP."""
        addr = f"{host}:{port}"
        code, stdout, stderr = self.run_adb_command(["connect", addr], timeout=10.0)
        output = stdout or stderr
        if "connected to" in output.lower() and "cannot" not in output.lower() and "failed" not in output.lower():
            self._preferred_serial = addr
            return True, f"Successfully connected to {addr}"
        return False, f"Failed to connect to {addr}: {output}"

    def disconnect_tcp(self, host: Optional[str] = None, port: int = 5555) -> Tuple[bool, str]:
        """Disconnect from TCP/IP Android device."""
        args = ["disconnect"]
        if host:
            args.append(f"{host}:{port}")
        code, stdout, stderr = self.run_adb_command(args, timeout=5.0)
        return code == 0, stdout or stderr

    def enable_tcpip_mode(self, port: int = 5555, serial: Optional[str] = None) -> Tuple[bool, str]:
        """Switch a USB-connected phone to listen for ADB over TCP/IP on the specified port."""
        target = self.get_active_device_serial(serial)
        args = ["-s", target, "tcpip", str(port)] if target else ["tcpip", str(port)]
        code, stdout, stderr = self.run_adb_command(args, timeout=8.0)
        if code == 0 or "restarting in tcp mode" in (stdout + stderr).lower():
            return True, f"Device restarting in TCP mode on port {port}. You can now disconnect USB and run 'connect_tcp'."
        return False, f"Failed to enable TCP/IP: {stdout or stderr}"

    def shell(self, cmd: str, serial: Optional[str] = None, timeout: float = 12.0) -> Tuple[int, str, str]:
        """Execute an ADB shell command on the target device."""
        target = self.get_active_device_serial(serial)
        if not target:
            return -1, "", "No Android device connected. Please connect via USB or WiFi."

        args = ["-s", target, "shell", cmd]
        return self.run_adb_command(args, timeout=timeout)

    def get_device_info(self, serial: Optional[str] = None) -> Optional[DeviceInfo]:
        """Fetch comprehensive device telemetry and hardware details."""
        target = self.get_active_device_serial(serial)
        if not target:
            return None

        # Base listing
        devices = self.list_devices()
        dev_match = next((d for d in devices if d.serial == target), None)
        state = dev_match.state if dev_match else "unknown"
        conn_type = "tcpip" if ":" in target else "usb"

        info = DeviceInfo(
            serial=target,
            state=state,
            connection_type=conn_type
        )

        if state != "device":
            return info

        # 1. Properties
        _, prop_out, _ = self.shell("getprop ro.product.model; getprop ro.product.manufacturer; getprop ro.build.version.release; getprop ro.build.version.sdk", serial=target)
        prop_lines = [p.strip() for p in prop_out.splitlines() if p.strip()]
        if len(prop_lines) >= 1:
            info.model = prop_lines[0]
        if len(prop_lines) >= 2:
            info.manufacturer = prop_lines[1]
        if len(prop_lines) >= 3:
            info.android_version = f"Android {prop_lines[2]}"
        if len(prop_lines) >= 4:
            info.sdk_version = f"SDK {prop_lines[3]}"

        # 2. Battery
        _, batt_out, _ = self.shell("dumpsys battery | grep level", serial=target)
        match = re.search(r"level:\s*(\d+)", batt_out)
        if match:
            info.battery_level = int(match.group(1))

        # 3. Screen Resolution
        _, wm_out, _ = self.shell("wm size", serial=target)
        wm_match = re.search(r"(\d+)x(\d+)", wm_out)
        if wm_match:
            info.screen_resolution = (int(wm_match.group(1)), int(wm_match.group(2)))

        # 4. Screen Power State
        _, pwr_out, _ = self.shell("dumpsys display | grep mHoldingDisplaySuspendBlocker", serial=target)
        if "true" in pwr_out.lower():
            info.is_screen_on = True
        else:
            _, pwr_out2, _ = self.shell("dumpsys power | grep 'Display Power: state='", serial=target)
            info.is_screen_on = "ON" in pwr_out2.upper()

        # 5. IP Address (wlan0)
        _, ip_out, _ = self.shell("ip -f inet addr show wlan0", serial=target)
        ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", ip_out)
        if ip_match:
            info.ip_address = ip_match.group(1)

        return info

    def get_display_size(self, serial: Optional[str] = None) -> Tuple[int, int]:
        """Get the physical screen dimensions (width, height), defaulting to (1080, 2400)."""
        target = self.get_active_device_serial(serial)
        _, wm_out, _ = self.shell("wm size", serial=target)
        wm_match = re.search(r"(\d+)x(\d+)", wm_out)
        if wm_match:
            return int(wm_match.group(1)), int(wm_match.group(2))
        return (1080, 2400)


# Global singleton instance
adb_bridge = ADBBridge.get_instance()
