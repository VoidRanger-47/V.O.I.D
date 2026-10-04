"""
vision/camera/camera_manager.py
Thread-safe, high-efficiency camera manager for V.O.I.D.
Provides zero-leak hardware resource acquisition and release, dynamic FPS control,
device switching, and MJPEG streaming generator.
"""

import cv2
import time
import threading
import logging
import numpy as np
from typing import Optional, Generator, Dict, Any, Tuple

from vision.camera.device_manager import DeviceManager
from vision.camera.frame_processor import FrameProcessor

logger = logging.getLogger("void.vision.camera_manager")


class CameraManager:
    """
    Centralized, thread-safe camera hardware controller.
    Ensures safe access, dynamic FPS pacing, and immediate hardware release.
    """
    
    # Performance Modes and target FPS
    FPS_MODES = {
        "ECO": 15,
        "BALANCED": 30,
        "TURBO": 60
    }

    def __init__(self, default_index: int = 0, default_mode: str = "BALANCED"):
        self.device_index = default_index
        self.mode = default_mode.upper() if default_mode.upper() in self.FPS_MODES else "BALANCED"
        self.target_fps = self.FPS_MODES[self.mode]

        self._cap: Optional[cv2.VideoCapture] = None
        self._lock = threading.RLock()
        self._frame_lock = threading.Lock()
        self._new_frame_event = threading.Event()
        self._hud_provider = None
        self._detection_fps_provider = None

        self._is_running = False
        self._capture_thread: Optional[threading.Thread] = None

        self._latest_frame: Optional[np.ndarray] = None
        self._latest_annotated_frame: Optional[np.ndarray] = None
        self._prev_gray_frame: Optional[np.ndarray] = None

        self._actual_fps = 0.0
        self._frame_count = 0
        self._last_fps_calc_time = time.time()
        self._fps_counter = 0

        self._last_motion_score = 0.0
        self._last_brightness = 0.0
        self._last_frame_time = 0.0

    @property
    def is_active(self) -> bool:
        return self._is_running and self._cap is not None and self._cap.isOpened()

    def set_mode(self, mode_name: str) -> str:
        """Change FPS performance mode: ECO, BALANCED, or TURBO."""
        clean_mode = mode_name.upper().strip()
        if clean_mode in self.FPS_MODES:
            self.mode = clean_mode
            self.target_fps = self.FPS_MODES[clean_mode]
            logger.info(f"Vision performance mode set to {self.mode} ({self.target_fps} FPS)")
            return self.mode
        return self.mode

    def set_hud_provider(self, provider_fn):
        """Register a callback returning HUD telemetry and detections for real-time overlay."""
        self._hud_provider = provider_fn

    def set_detection_fps_provider(self, provider_fn):
        """Register a callback returning background detection inference FPS."""
        self._detection_fps_provider = provider_fn

    def start(self, device_index: Optional[int] = None) -> bool:
        """
        Start the background camera capture thread.
        Safely acquires the camera device with fallback to available indices.
        """
        with self._lock:
            if self._is_running and self._cap is not None and self._cap.isOpened():
                if device_index is not None and device_index != self.device_index:
                    self.switch_camera(device_index)
                return True

            if device_index is not None:
                self.device_index = device_index

            # Open hardware capture
            self._cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
            if not self._cap.isOpened():
                self._cap.release()
                self._cap = cv2.VideoCapture(self.device_index)
            
            # Fallback if primary device failed
            if not self._cap.isOpened() and self.device_index != 0:
                logger.warning(f"Failed to open camera index {self.device_index}, attempting index 0...")
                self.device_index = 0
                self._cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
                if not self._cap.isOpened():
                    self._cap.release()
                    self._cap = cv2.VideoCapture(0)

            if not self._cap.isOpened():
                logger.error(f"Could not open any webcam hardware.")
                self._cap = None
                self._is_running = False
                return False

            # Set hardware properties for high-speed streaming
            try:
                # Use MJPG FourCC for high throughput bandwidth over USB / DirectShow
                self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*'MJPG'))
            except Exception:
                pass
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self._cap.set(cv2.CAP_PROP_FPS, self.target_fps)

            self._is_running = True
            self._frame_count = 0
            self._fps_counter = 0
            self._last_fps_calc_time = time.time()
            self._new_frame_event.clear()

            self._capture_thread = threading.Thread(
                target=self._capture_loop,
                name="VOID-CameraCaptureThread",
                daemon=True
            )
            self._capture_thread.start()
            logger.info(f"Camera manager started on device {self.device_index} at target {self.target_fps} FPS.")
            return True

    def stop(self) -> bool:
        """
        Stop camera capture and completely release the hardware device.
        Webcam LED will turn off immediately.
        """
        with self._lock:
            self._is_running = False
            self._new_frame_event.set()
            
            if self._capture_thread and self._capture_thread.is_alive():
                self._capture_thread.join(timeout=2.0)
            self._capture_thread = None

            cap = self._cap
            self._cap = None
            if cap is not None:
                try:
                    cap.release()
                except Exception as e:
                    logger.warning(f"Exception during camera release: {e}")

            with self._frame_lock:
                self._latest_frame = None
                self._latest_annotated_frame = None
                self._prev_gray_frame = None
                self._actual_fps = 0.0

            logger.info("Camera manager stopped and hardware released.")
            return True

    def switch_camera(self, new_index: int) -> bool:
        """Switch active camera to another device index safely."""
        with self._lock:
            was_running = self._is_running
            if was_running:
                self.stop()
            self.device_index = new_index
            if was_running:
                return self.start(new_index)
            return True

    def _capture_loop(self):
        """Dedicated background capture loop with high-throughput frame grabbing."""
        metric_interval = 6
        frame_idx = 0

        while self._is_running and self._cap is not None:
            loop_start = time.time()

            try:
                ret, frame = self._cap.read()
                if ret and frame is not None:
                    frame_idx += 1

                    # Compute motion & brightness periodically on a small thumbnail to save CPU
                    if frame_idx % metric_interval == 0:
                        thumb = cv2.resize(frame, (160, 120), interpolation=cv2.INTER_NEAREST)
                        gray = cv2.cvtColor(thumb, cv2.COLOR_BGR2GRAY)
                        motion_score, _ = FrameProcessor.compute_motion(self._prev_gray_frame, gray)
                        brightness = FrameProcessor.calculate_brightness(thumb)
                        self._prev_gray_frame = gray
                    else:
                        motion_score = self._last_motion_score
                        brightness = self._last_brightness

                    with self._frame_lock:
                        self._latest_frame = frame
                        self._last_motion_score = motion_score
                        self._last_brightness = brightness
                        self._last_frame_time = time.time()
                        self._frame_count += 1
                        self._fps_counter += 1

                    # Notify waiting streaming generators that a new frame is ready
                    self._new_frame_event.set()

                    # Calculate actual FPS every 1 second
                    now = time.time()
                    if now - self._last_fps_calc_time >= 1.0:
                        self._actual_fps = self._fps_counter / (now - self._last_fps_calc_time)
                        self._fps_counter = 0
                        self._last_fps_calc_time = now
                else:
                    time.sleep(0.005)
            except Exception as e:
                logger.error(f"Error in camera capture loop: {e}")
                time.sleep(0.02)

            # Cap frame rate only if target_fps is below native hardware rate (e.g. ECO mode)
            if self.target_fps < 30:
                interval = 1.0 / self.target_fps
                elapsed = time.time() - loop_start
                sleep_time = interval - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

    def capture_frame(self, auto_open: bool = False) -> Optional[np.ndarray]:
        """
        Get the most recent frame. If auto_open is True and camera is inactive,
        temporarily opens camera to take a snapshot and releases it.
        """
        with self._frame_lock:
            if self.is_active and self._latest_frame is not None:
                return self._latest_frame.copy()

        if auto_open:
            logger.info("Camera inactive; taking single frame on-demand snapshot...")
            cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                cap = cv2.VideoCapture(self.device_index)
            
            if cap.isOpened():
                # Allow auto-exposure to settle for 2 frames
                for _ in range(2):
                    cap.read()
                ret, frame = cap.read()
                cap.release()
                if ret and frame is not None:
                    return frame
        return None

    def update_annotated_frame(self, annotated: np.ndarray):
        """Store HUD annotated frame for backward compatibility."""
        with self._frame_lock:
            self._latest_annotated_frame = annotated

    def get_stream_frame(self, use_hud: bool = True) -> Optional[np.ndarray]:
        """Get the frame to display in the live video stream with real-time HUD."""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            frame = self._latest_frame.copy()

        if use_hud and self._hud_provider is not None:
            try:
                hud_data = self._hud_provider()
                if hud_data:
                    return FrameProcessor.draw_hud_overlay(
                        frame=frame,
                        objects=hud_data.get("objects", []),
                        faces=hud_data.get("faces", []),
                        scene_info=hud_data.get("scene", {}),
                        fps=self._actual_fps,
                        mode=self.mode,
                        hardware_info=hud_data.get("hardware", {}),
                        gestures=hud_data.get("gestures", []),
                        detection_fps=hud_data.get("detection_fps", 0.0)
                    )
            except Exception as e:
                logger.debug(f"Error drawing HUD overlay: {e}")
        elif use_hud and self._latest_annotated_frame is not None:
            return self._latest_annotated_frame.copy()

        return frame

    def generate_mjpeg_stream(self, use_hud: bool = True) -> Generator[bytes, None, None]:
        """Generator yielding MJPEG multipart chunks for smooth, high-FPS HTTP streaming."""
        last_yield_time = 0.0
        min_interval = 1.0 / max(1, self.target_fps)

        while self.is_active:
            # Low latency frame wake-up (5ms timeout to prevent frame dropping)
            self._new_frame_event.wait(timeout=0.005)
            self._new_frame_event.clear()

            if not self.is_active:
                break

            with self._frame_lock:
                frame = self._latest_frame.copy() if self._latest_frame is not None else None

            if frame is None:
                continue

            # Render HUD overlay directly on fresh frame (<0.5ms)
            if use_hud and self._hud_provider is not None:
                try:
                    hud_data = self._hud_provider()
                    if hud_data:
                        frame = FrameProcessor.draw_hud_overlay(
                            frame=frame,
                            objects=hud_data.get("objects", []),
                            faces=hud_data.get("faces", []),
                            scene_info=hud_data.get("scene", {}),
                            fps=self._actual_fps,
                            mode=self.mode,
                            hardware_info=hud_data.get("hardware", {}),
                            gestures=hud_data.get("gestures", []),
                            detection_fps=hud_data.get("detection_fps", 0.0)
                        )
                except Exception as e:
                    logger.debug(f"Error drawing HUD overlay on stream: {e}")
            elif use_hud and self._latest_annotated_frame is not None:
                frame = self._latest_annotated_frame.copy()

            jpeg_bytes = FrameProcessor.to_jpeg_bytes(frame, quality=72)
            if jpeg_bytes:
                yield (b"--frame\r\n"
                       b"Content-Type: image/jpeg\r\n\r\n" + jpeg_bytes + b"\r\n")

            # Soft pacing to respect target FPS if needed
            now = time.time()
            elapsed = now - last_yield_time
            if elapsed < min_interval:
                time.sleep(min_interval - elapsed)
            last_yield_time = time.time()

    def get_telemetry(self) -> Dict[str, Any]:
        """Get camera status and hardware performance metrics."""
        det_fps = 0.0
        if self._detection_fps_provider:
            try:
                det_fps = self._detection_fps_provider()
            except Exception:
                det_fps = 0.0

        return {
            "active": self.is_active,
            "device_index": self.device_index,
            "mode": self.mode,
            "target_fps": self.target_fps,
            "actual_fps": round(self._actual_fps, 1),
            "detection_fps": round(det_fps, 1),
            "frame_count": self._frame_count,
            "last_motion_score": round(self._last_motion_score, 4),
            "last_brightness": round(self._last_brightness, 2),
            "last_frame_age_ms": round((time.time() - self._last_frame_time) * 1000, 1) if self._last_frame_time > 0 else None
        }
