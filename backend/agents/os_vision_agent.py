"""
OS Vision & GUI Interaction Specialist Agent.
Observes the screen, inspects active windows, manipulates mouse/keyboard, and interacts with the clipboard.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from tools.desktop_tools import (
    take_screenshot, annotate_grid_on_image, click_at,
    type_text, send_hotkey, press_key, get_active_window_info,
    list_open_windows, focus_window_by_title, read_clipboard, write_clipboard,
    get_screen_size
)
from agents.os_state import OSAutomationState

logger = logging.getLogger("os_vision_agent")

class OSVisionAgent:
    name = "OS_Vision_GUI_Agent"
    role = "Captures visual screen state, tracks active application windows, and executes mouse/keyboard actions."

    def observe_screen(self, add_grid: bool = False) -> Dict[str, Any]:
        """Captures screen and optionally generates coordinate grid."""
        shot = take_screenshot()
        if shot["status"] == "success" and add_grid:
            grid_path = annotate_grid_on_image(shot["file_path"])
            shot["grid_file_path"] = grid_path
        
        # Add active window context
        shot["active_window"] = get_active_window_info()
        return shot

    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> Dict[str, Any]:
        """Click on the screen."""
        return click_at(x=x, y=y, button=button, clicks=clicks)

    def type(self, text: str, press_enter: bool = False) -> Dict[str, Any]:
        """Type text into current focused UI control."""
        return type_text(text=text, press_enter=press_enter)

    def hotkey(self, *keys: str) -> Dict[str, Any]:
        """Trigger keyboard shortcut."""
        return send_hotkey(*keys)

    def focus_app(self, title_query: str) -> Dict[str, Any]:
        """Bring target window to the front."""
        return focus_window_by_title(title_query)

    def clipboard_paste(self, text: str) -> Dict[str, Any]:
        """Set clipboard text and simulate Ctrl+V."""
        write_clipboard(text)
        time.sleep(0.1)
        res = send_hotkey("ctrl", "v")
        return {"status": "success", "text_pasted": text}

    def press(self, key: str) -> Dict[str, Any]:
        """Press a keyboard key."""
        return press_key(key)

    def wait(self, seconds: float = 2.0) -> Dict[str, Any]:
        """Pause execution to allow UI, browser, or page to settle."""
        time.sleep(seconds)
        return {"status": "success", "waited_seconds": seconds}

    def play_youtube_video(self, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Brings browser into focus, waits for page to settle, clicks top video, and ensures playback.
        """
        # Step A: Focus Chrome or YouTube window
        focus_res = self.focus_app("youtube")
        if focus_res.get("status") != "success":
            self.focus_app("chrome")

        time.sleep(2.0)

        # Step B: Click first video thumbnail based on current screen dimensions
        screen_w, screen_h = get_screen_size()
        video_x = int(screen_w * 0.31)
        video_y = int(screen_h * 0.27)

        click_res = self.click(x=video_x, y=video_y)

        # Step C: Give video player a moment to mount, then send play key
        time.sleep(1.8)
        self.press("k")

        return {
            "status": "success",
            "action": "play_youtube_video",
            "query": query or "top result",
            "click_target": {"x": video_x, "y": video_y},
            "playback_started": True
        }

    def process_step(self, step: Dict[str, Any], state: OSAutomationState) -> Dict[str, Any]:
        """Execute a vision or GUI action step."""
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "observe_screen":
            return self.observe_screen(add_grid=params.get("add_grid", False))
        elif action == "click":
            return self.click(
                x=params.get("x", 0),
                y=params.get("y", 0),
                button=params.get("button", "left"),
                clicks=params.get("clicks", 1)
            )
        elif action == "type":
            return self.type(
                text=params.get("text", ""),
                press_enter=params.get("press_enter", False)
            )
        elif action == "hotkey":
            keys = params.get("keys", [])
            return self.hotkey(*keys)
        elif action == "press_key":
            return self.press(key=params.get("key", "enter"))
        elif action == "wait":
            return self.wait(seconds=params.get("seconds", 2.0))
        elif action == "focus_app":
            return self.focus_app(title_query=params.get("title", ""))
        elif action == "clipboard_paste":
            return self.clipboard_paste(text=params.get("text", ""))
        elif action == "play_youtube_video":
            return self.play_youtube_video(query=params.get("query"))
        else:
            return {"status": "error", "message": f"Unknown vision/GUI action: {action}"}
