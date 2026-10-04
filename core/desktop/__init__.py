# core/desktop/__init__.py
from core.desktop.driver import desktop_driver, DesktopDriver, FailsafeTriggeredError

__all__ = ["desktop_driver", "DesktopDriver", "FailsafeTriggeredError"]
