"""
vision/camera/device_manager.py
Device discovery and management for connected video capture hardware.
Supports DirectShow (Windows), MSMF, and standard video indices.
"""

import cv2
import logging
from typing import List, Dict, Any

logger = logging.getLogger("void.vision.device_manager")

class DeviceManager:
    """
    Scans and manages available camera hardware devices without hanging the application.
    """
    
    @staticmethod
    def list_devices(max_check: int = 4) -> List[Dict[str, Any]]:
        """
        Probe available camera indexes quickly and return their capabilities.
        """
        available = []
        for index in range(max_check):
            # Try DirectShow first on Windows for fast non-blocking probe
            cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
            if not cap.isOpened():
                cap.release()
                # Fallback to default backend
                cap = cv2.VideoCapture(index)
            
            if cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None:
                    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)) or frame.shape[1]
                    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)) or frame.shape[0]
                    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                    available.append({
                        "index": index,
                        "name": f"Camera {index}" + (" (Default Webcam)" if index == 0 else f" (External/Aux #{index})"),
                        "width": width,
                        "height": height,
                        "fps": round(fps, 1),
                        "status": "available"
                    })
                cap.release()
        
        if not available:
            logger.info("No physical cameras opened during probe.")
            
        return available

    @staticmethod
    def verify_device(index: int) -> bool:
        """Verify if a specific camera index can be opened."""
        cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(index)
        opened = cap.isOpened()
        if opened:
            cap.release()
        return opened
