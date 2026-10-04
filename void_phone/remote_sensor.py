# void_phone/remote_sensor.py
"""
V.O.I.D. Mobile Remote Perception & Sensor Engine.
Extracts real-time phone telemetry (battery, display state, top app, network, storage)
and captures high-speed screen frames via ADB for multimodal AI comprehension.
"""

from __future__ import annotations

import base64
import io
import logging
import re
from typing import Any, Dict, Optional, Tuple

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from void_phone.adb_bridge import ADBBridge, DeviceInfo

logger = logging.getLogger("VOID.PhoneSensors")


class PhoneSensorManager:
    """
    Manages telemetry sensing and screen capture from connected Android devices.
    """
    _instance: Optional[PhoneSensorManager] = None

    def __init__(self, bridge: Optional[ADBBridge] = None):
        self.bridge = bridge or ADBBridge.get_instance()

    @classmethod
    def get_instance(cls) -> PhoneSensorManager:
        if cls._instance is None:
            cls._instance = PhoneSensorManager()
        return cls._instance

    def is_device_connected(self, serial: Optional[str] = None) -> bool:
        """Check if target or any device is currently online."""
        return self.bridge.is_connected(serial)

    def get_telemetry(self, serial: Optional[str] = None) -> Dict[str, Any]:
        """
        Gathers comprehensive live telemetry from the phone:
        - Battery level, temperature, charging state
        - Display power and resolution
        - Current foreground app & activity
        - Network interfaces (IP address, WiFi)
        - Storage usage
        """
        target = self.bridge.get_active_device_serial(serial)
        if not target or not self.bridge.is_connected(target):
            return {
                "success": False,
                "error": "No Android device connected. Please connect via USB or Wi-Fi (adb connect <ip>:5555)."
            }

        dev_info = self.bridge.get_device_info(target) or DeviceInfo(
            serial=target,
            state="device",
            connection_type="tcpip" if ":" in target else "usb"
        )

        telemetry: Dict[str, Any] = {
            "success": True,
            "serial": target,
            "connection_type": dev_info.connection_type,
            "device": {
                "model": dev_info.model,
                "manufacturer": dev_info.manufacturer,
                "android_version": dev_info.android_version,
                "sdk_version": dev_info.sdk_version,
            },
            "battery": self._parse_battery(target),
            "display": self._parse_display(target),
            "foreground_app": self._parse_foreground_app(target),
            "network": self._parse_network(target),
            "storage": self._parse_storage(target),
        }
        return telemetry

    def _parse_battery(self, serial: str) -> Dict[str, Any]:
        """Parses detailed battery metrics from dumpsys battery."""
        code, out, _ = self.bridge.shell("dumpsys battery", serial=serial, timeout=5.0)
        battery: Dict[str, Any] = {
            "level": None,
            "scale": 100,
            "status": "Unknown",
            "plugged": "None",
            "temperature_c": None,
            "voltage_mv": None,
            "health": "Good"
        }
        if code != 0:
            return battery

        status_map = {
            1: "Unknown", 2: "Charging", 3: "Discharging",
            4: "Not Charging", 5: "Full"
        }
        plugged_map = {
            0: "Battery (Unplugged)", 1: "AC Charger",
            2: "USB Port", 4: "Wireless Charging", 8: "Dock"
        }

        for line in out.splitlines():
            line = line.strip()
            if line.startswith("level:"):
                m = re.search(r"(\d+)", line)
                if m:
                    battery["level"] = int(m.group(1))
            elif line.startswith("scale:"):
                m = re.search(r"(\d+)", line)
                if m:
                    battery["scale"] = int(m.group(1))
            elif line.startswith("status:"):
                m = re.search(r"(\d+)", line)
                if m:
                    battery["status"] = status_map.get(int(m.group(1)), "Unknown")
            elif "USB powered: true" in line:
                battery["plugged"] = "USB Port"
            elif "AC powered: true" in line:
                battery["plugged"] = "AC Charger"
            elif "Wireless powered: true" in line:
                battery["plugged"] = "Wireless Charging"
            elif line.startswith("plugged:"):
                m = re.search(r"(\d+)", line)
                if m:
                    battery["plugged"] = plugged_map.get(int(m.group(1)), "None")
            elif line.startswith("temperature:"):
                m = re.search(r"(\d+)", line)
                if m:
                    battery["temperature_c"] = round(int(m.group(1)) / 10.0, 1)
            elif line.startswith("voltage:"):
                m = re.search(r"(\d+)", line)
                if m:
                    battery["voltage_mv"] = int(m.group(1))

        return battery

    def _parse_display(self, serial: str) -> Dict[str, Any]:
        """Parses screen resolution, orientation, and power state."""
        width, height = self.bridge.get_display_size(serial)

        # Power state
        code, out, _ = self.bridge.shell(
            "dumpsys display | grep -E 'mHoldingDisplaySuspendBlocker|mDisplayState'",
            serial=serial, timeout=4.0
        )
        is_on = "true" in out.lower() or "state=on" in out.lower()
        if not is_on:
            code2, out2, _ = self.bridge.shell("dumpsys power | grep 'Display Power:'", serial=serial, timeout=3.0)
            is_on = "ON" in out2.upper()

        return {
            "width": width,
            "height": height,
            "is_screen_on": is_on,
            "orientation": "portrait" if height >= width else "landscape"
        }

    def _parse_foreground_app(self, serial: str) -> Dict[str, Any]:
        """Detects the current package and active window in focus."""
        code, out, _ = self.bridge.shell(
            "dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'",
            serial=serial, timeout=5.0
        )
        package = "Unknown"
        activity = "Unknown"

        if code == 0 and out:
            # Matches: u0 com.android.chrome/com.google.android.apps.chrome.Main
            m = re.search(r"([a-zA-Z0-9_\.]+)/([a-zA-Z0-9_\.]+)", out)
            if m:
                package = m.group(1)
                activity = m.group(2)

        if package == "Unknown":
            # Fallback for newer Android 13/14 dumpsys activity
            _, out2, _ = self.bridge.shell(
                "dumpsys activity activities | grep -E 'topResumedActivity|mResumedActivity'",
                serial=serial, timeout=4.0
            )
            m2 = re.search(r"([a-zA-Z0-9_\.]+)/([a-zA-Z0-9_\.]+)", out2)
            if m2:
                package = m2.group(1)
                activity = m2.group(2)

        return {
            "package": package,
            "activity": activity,
            "is_home": "launcher" in package.lower() or "home" in package.lower()
        }

    def _parse_network(self, serial: str) -> Dict[str, Any]:
        """Finds IP address on wlan0 and WiFi connection info."""
        _, ip_out, _ = self.bridge.shell("ip -f inet addr show wlan0", serial=serial, timeout=4.0)
        ip_match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", ip_out)
        ip_addr = ip_match.group(1) if ip_match else None

        wifi_connected = ip_addr is not None
        ssid = None

        if wifi_connected:
            _, wifi_out, _ = self.bridge.shell("dumpsys wifi | grep -E 'mWifiInfo|SSID:'", serial=serial, timeout=4.0)
            ssid_match = re.search(r"SSID:\s*\"?([^\",\n]+)\"?", wifi_out)
            if ssid_match:
                ssid = ssid_match.group(1).strip()

        return {
            "ip_address": ip_addr,
            "wifi_connected": wifi_connected,
            "ssid": ssid or "Connected" if wifi_connected else "Disconnected"
        }

    def _parse_storage(self, serial: str) -> Dict[str, Any]:
        """Parses internal storage usage on /data."""
        code, out, _ = self.bridge.shell("df -h /data", serial=serial, timeout=4.0)
        storage = {"total": "Unknown", "used": "Unknown", "free": "Unknown", "percent": "Unknown"}
        if code == 0:
            lines = out.splitlines()
            if len(lines) >= 2:
                parts = lines[1].split()
                if len(parts) >= 5:
                    storage["total"] = parts[1]
                    storage["used"] = parts[2]
                    storage["free"] = parts[3]
                    storage["percent"] = parts[4]
        return storage

    def capture_screen_bytes(self, serial: Optional[str] = None) -> Tuple[bool, bytes, str]:
        """
        Executes low-latency binary screen capture via adb exec-out.
        Returns (success, png_bytes, error_message).
        """
        target = self.bridge.get_active_device_serial(serial)
        if not target or not self.bridge.is_connected(target):
            return False, b"", "No Android device connected over ADB."

        # Modern Android method: exec-out screencap -p
        args = ["-s", target, "exec-out", "screencap", "-p"] if target else ["exec-out", "screencap", "-p"]
        code, raw_bytes, err = self.bridge.run_adb_command_raw(args, timeout=12.0)

        # Verify PNG signature: \x89PNG\r\n\x1a\n
        png_sig = b"\x89PNG\r\n\x1a\n"
        if code == 0 and raw_bytes.startswith(png_sig):
            return True, raw_bytes, ""

        # Normalize potential Windows CRLF artifacts (\r\n -> \n)
        if b"\x89PNG" in raw_bytes:
            normalized = raw_bytes.replace(b"\r\n", b"\n")
            if normalized.startswith(png_sig):
                return True, normalized, ""

        # Fallback: Capture to device file and pull
        logger.debug("Falling back to /sdcard/screencap.png pull method...")
        sd_path = "/sdcard/_void_screencap.png"
        self.bridge.shell(f"screencap -p {sd_path}", serial=target, timeout=8.0)
        pull_args = ["-s", target, "exec-out", "cat", sd_path] if target else ["exec-out", "cat", sd_path]
        p_code, p_bytes, _ = self.bridge.run_adb_command_raw(pull_args, timeout=8.0)
        self.bridge.shell(f"rm {sd_path}", serial=target, timeout=3.0)

        if p_bytes.startswith(png_sig):
            return True, p_bytes, ""

        norm_p = p_bytes.replace(b"\r\n", b"\n")
        if norm_p.startswith(png_sig):
            return True, norm_p, ""

        return False, b"", f"Screen capture failed: {err.decode('utf-8', errors='ignore') or 'Invalid PNG bytes returned'}"

    def capture_screen_image(
        self,
        serial: Optional[str] = None,
        max_dimension: Optional[int] = None
    ) -> Optional[Any]:
        """
        Captures screen and returns a PIL.Image object, optionally downscaled.
        """
        if not PIL_AVAILABLE:
            logger.error("PIL/Pillow is required for capture_screen_image.")
            return None

        success, data, err = self.capture_screen_bytes(serial)
        if not success or not data:
            logger.warning(f"Failed to capture screen image: {err}")
            return None

        try:
            image = Image.open(io.BytesIO(data))
            if max_dimension and max(image.size) > max_dimension:
                scale = max_dimension / float(max(image.size))
                new_size = (int(image.width * scale), int(image.height * scale))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
            return image
        except Exception as e:
            logger.error(f"Failed to decode PIL image from screencap: {e}")
            return None

    def capture_screen_base64(
        self,
        serial: Optional[str] = None,
        max_dimension: Optional[int] = 1080
    ) -> Dict[str, Any]:
        """
        Captures phone screen and returns base64 PNG data suitable for web UI streaming & LLMs.
        """
        image = self.capture_screen_image(serial=serial, max_dimension=max_dimension)
        if image is None:
            # If PIL isn't available or failed, try raw bytes fallback
            success, raw_bytes, err = self.capture_screen_bytes(serial)
            if success and raw_bytes:
                b64 = base64.b64encode(raw_bytes).decode("ascii")
                return {
                    "success": True,
                    "base64": b64,
                    "data_url": f"data:image/png;base64,{b64}",
                    "width": 1080,
                    "height": 2400
                }
            return {"success": False, "error": err or "Failed to capture phone screen"}

        buf = io.BytesIO()
        image.save(buf, format="PNG", optimize=True)
        raw = buf.getvalue()
        b64_str = base64.b64encode(raw).decode("ascii")
        return {
            "success": True,
            "base64": b64_str,
            "data_url": f"data:image/png;base64,{b64_str}",
            "width": image.width,
            "height": image.height
        }


# Global Singleton Instance
phone_sensors = PhoneSensorManager.get_instance()
