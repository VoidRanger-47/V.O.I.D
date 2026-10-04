# skills/desktop_control.py
"""
V.O.I.D. Desktop Automation Skills.
Exposes high-level actions for window management, mouse navigation, keyboard input,
and automated multi-step desktop workflows.
"""

import time
import logging
from typing import Dict, Any, List, Optional
from core.desktop.driver import desktop_driver, FailsafeTriggeredError

logger = logging.getLogger("VOID.Skills.Desktop")


def list_desktop_windows(visible_only: bool = True) -> List[Dict[str, Any]]:
    """Returns a list of all currently open desktop windows with positions and processes."""
    return desktop_driver.list_windows(visible_only=visible_only)


def focus_desktop_window(target: str) -> Dict[str, Any]:
    """Brings a window to the foreground by partial title, process name, or HWND."""
    success = desktop_driver.focus_window(target)
    return {
        "success": success,
        "target": target,
        "message": f"Window '{target}' focused successfully." if success else f"Could not find or focus window '{target}'."
    }


def execute_desktop_action(action: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes a single desktop control action.
    Supported actions:
      - 'click': mouse_click(x, y, button)
      - 'move': mouse_move(x, y)
      - 'type': keyboard_type(text, delay_ms)
      - 'hotkey': keyboard_hotkey(keys)
      - 'press': press_key(key)
      - 'scroll': mouse_scroll(clicks, direction)
      - 'focus': focus_window(target)
      - 'minimize': minimize_window(target)
      - 'maximize': maximize_window(target)
      - 'close': close_window(target)
      - 'get_cursor': get_cursor_position()
      - 'screen_size': get_screen_size()
    """
    params = params or {}
    act = action.lower().strip()

    try:
        if act == "click":
            x = params.get("x")
            y = params.get("y")
            button = params.get("button", "left")
            res = desktop_driver.mouse_click(x, y, button=button)
            return {"success": res, "action": act, "coords": (x, y), "button": button}

        elif act == "move":
            x = int(params.get("x", 0))
            y = int(params.get("y", 0))
            smooth = bool(params.get("smooth", False))
            res = desktop_driver.mouse_move(x, y, smooth=smooth)
            return {"success": res, "action": act, "coords": (x, y)}

        elif act == "type":
            text = str(params.get("text", ""))
            delay = int(params.get("delay_ms", 15))
            res = desktop_driver.type_text(text, delay_ms=delay)
            return {"success": res, "action": act, "text_length": len(text)}

        elif act == "hotkey":
            keys = params.get("keys", [])
            if isinstance(keys, str):
                keys = [k.strip() for k in keys.split("+")]
            res = desktop_driver.hotkey(keys)
            return {"success": res, "action": act, "keys": keys}

        elif act == "press":
            key = str(params.get("key", "enter"))
            res = desktop_driver.press_key(key)
            return {"success": res, "action": act, "key": key}

        elif act == "scroll":
            clicks = int(params.get("clicks", 3))
            direction = str(params.get("direction", "down"))
            res = desktop_driver.mouse_scroll(clicks, direction=direction)
            return {"success": res, "action": act, "clicks": clicks, "direction": direction}

        elif act == "focus":
            target = str(params.get("target", ""))
            res = desktop_driver.focus_window(target)
            return {"success": res, "action": act, "target": target}

        elif act == "minimize":
            target = str(params.get("target", ""))
            res = desktop_driver.minimize_window(target)
            return {"success": res, "action": act, "target": target}

        elif act == "maximize":
            target = str(params.get("target", ""))
            res = desktop_driver.maximize_window(target)
            return {"success": res, "action": act, "target": target}

        elif act == "close":
            target = str(params.get("target", ""))
            res = desktop_driver.close_window(target)
            return {"success": res, "action": act, "target": target}

        elif act == "get_cursor":
            pos = desktop_driver.get_cursor_position()
            return {"success": True, "action": act, "cursor": {"x": pos[0], "y": pos[1]}}

        elif act == "screen_size":
            w, h = desktop_driver.get_screen_size()
            return {"success": True, "action": act, "screen": {"width": w, "height": h}}

        else:
            return {"success": False, "error": f"Unsupported desktop action '{action}'."}

    except FailsafeTriggeredError as e:
        logger.warning(f"Desktop action aborted: {e}")
        return {"success": False, "error": str(e), "failsafe_triggered": True}
    except Exception as e:
        logger.error(f"Desktop action '{action}' failed: {e}")
        return {"success": False, "error": str(e)}


def execute_desktop_macro(steps: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Executes a multi-step desktop workflow sequentially.
    Each step is a dict: {"action": "focus", "params": {"target": "notepad"}}
    Supports an optional "delay" key per step (in seconds).
    """
    results = []
    for idx, step in enumerate(steps):
        action = step.get("action", "")
        params = step.get("params", {})
        delay = float(step.get("delay", 0.1))

        res = execute_desktop_action(action, params)
        results.append({"step": idx + 1, "action": action, "result": res})

        if not res.get("success", False):
            # Abort macro on failure or failsafe
            return {
                "success": False,
                "completed_steps": idx,
                "total_steps": len(steps),
                "error": res.get("error", "Step failed"),
                "step_history": results
            }

        if delay > 0:
            time.sleep(delay)

    return {
        "success": True,
        "completed_steps": len(steps),
        "total_steps": len(steps),
        "step_history": results
    }
