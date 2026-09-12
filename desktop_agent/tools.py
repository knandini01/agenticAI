import pyautogui
import time

# Safely configure PyAutoGUI
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.1

def click(x: int, y: int) -> str:
    """Move the mouse to coordinates (x, y) and click."""
    try:
        pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.click()
        return f"Clicked at ({x}, {y})"
    except Exception as e:
        return f"Error clicking: {e}"

def double_click(x: int, y: int) -> str:
    """Move the mouse to coordinates (x, y) and double click."""
    try:
        pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.doubleClick()
        return f"Double clicked at ({x}, {y})"
    except Exception as e:
        return f"Error double clicking: {e}"

def type_text(text: str, press_enter: bool = False) -> str:
    """Type the given string of text. If press_enter is True, presses the Enter key immediately after typing."""
    try:
        pyautogui.typewrite(text, interval=0.01)
        if press_enter:
            time.sleep(0.15)
            pyautogui.press('enter')
            return f"Typed '{text}' and pressed Enter"
        return f"Typed: '{text}'"
    except Exception as e:
        return f"Error typing text: {e}"

def press_key(key: str) -> str:
    """Press a specific keyboard key (e.g., 'enter', 'win', 'tab', 'escape', 'down', 'up')."""
    try:
        pyautogui.press(key)
        return f"Pressed key: '{key}'"
    except Exception as e:
        return f"Error pressing key: {e}"

def hotkey(keys: list[str]) -> str:
    """Press a combination of keys together (e.g., ['win', 'r'], ['ctrl', 'a'])."""
    try:
        pyautogui.hotkey(*keys)
        return f"Pressed hotkey: {keys}"
    except Exception as e:
        return f"Error pressing hotkey: {e}"

def wait(seconds: float = 1.0) -> str:
    """Wait for a specified number of seconds for windows to load or open."""
    try:
        time.sleep(seconds)
        return f"Waited {seconds}s"
    except Exception as e:
        return f"Error waiting: {e}"

def scroll(clicks: int) -> str:
    """Scroll the mouse wheel up (positive) or down (negative)."""
    try:
        pyautogui.scroll(clicks)
        return f"Scrolled {clicks} clicks"
    except Exception as e:
        return f"Error scrolling: {e}"

def open_browser(url: str = "https://www.google.com") -> str:
    """Opens the default web browser directly to the specified URL."""
    import webbrowser
    try:
        target_url = url if url.startswith("http") else f"https://{url}"
        webbrowser.open(target_url)
        time.sleep(2.0)  # Wait for browser window to launch and render
        return f"Opened browser to '{target_url}'"
    except Exception as e:
        return f"Error opening browser: {e}"

def browser_navigate(url: str) -> str:
    """Focuses the browser address bar (Ctrl+L), types the URL, and presses Enter."""
    try:
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.2)
        target_url = url if url.startswith("http") else f"https://{url}"
        pyautogui.typewrite(target_url, interval=0.01)
        time.sleep(0.15)
        pyautogui.press('enter')
        time.sleep(2.0)  # Wait for page to load
        return f"Navigated to '{target_url}'"
    except Exception as e:
        return f"Error navigating: {e}"

def browser_new_tab(url: str = "") -> str:
    """Opens a new browser tab with Ctrl+T and optionally navigates to a URL."""
    try:
        pyautogui.hotkey('ctrl', 't')
        time.sleep(0.4)
        if url:
            target_url = url if url.startswith("http") else f"https://{url}"
            pyautogui.typewrite(target_url, interval=0.01)
            time.sleep(0.1)
            pyautogui.press('enter')
            time.sleep(2.0)
            return f"Opened new tab and navigated to '{target_url}'"
        return "Opened new blank tab"
    except Exception as e:
        return f"Error opening new tab: {e}"

def browser_close_tab() -> str:
    """Closes the current browser tab with Ctrl+W."""
    try:
        pyautogui.hotkey('ctrl', 'w')
        time.sleep(0.3)
        return "Closed current tab"
    except Exception as e:
        return f"Error closing tab: {e}"

def click_and_type(x: int, y: int, text: str, clear_first: bool = True, press_enter: bool = False) -> str:
    """Clicks on an input field/search bar, optionally clears it, types text, and optionally presses Enter."""
    try:
        pyautogui.moveTo(x, y, duration=0.15)
        pyautogui.click()
        time.sleep(0.2)
        if clear_first:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.05)
            pyautogui.press('backspace')
        pyautogui.typewrite(text, interval=0.01)
        if press_enter:
            time.sleep(0.15)
            pyautogui.press('enter')
            time.sleep(1.5)  # Wait for search results or form submission
            return f"Clicked ({x}, {y}), typed '{text}', and pressed Enter"
        return f"Clicked ({x}, {y}) and typed '{text}'"
    except Exception as e:
        return f"Error in click_and_type: {e}"

def browser_scroll(direction: str = "down", amount: int = 400) -> str:
    """Scrolls the current web page up or down to reveal more content."""
    try:
        clicks = -abs(amount) if direction.lower() == "down" else abs(amount)
        pyautogui.scroll(clicks)
        time.sleep(0.5)
        return f"Scrolled page {direction} by {amount}"
    except Exception as e:
        return f"Error scrolling page: {e}"

def check_app_opened(app_name: str) -> str:
    """Checks whether an application process is running (e.g., 'notepad', 'calc', 'calculator', 'chrome', etc.)."""
    import subprocess
    try:
        out = subprocess.check_output(
            'tasklist', 
            text=True, 
            errors='ignore', 
            creationflags=subprocess.CREATE_NO_WINDOW if hasattr(subprocess, 'CREATE_NO_WINDOW') else 0
        )
        is_running = app_name.lower() in out.lower()
        if is_running:
            return f"VERIFIED: Application '{app_name}' is currently running."
        else:
            return f"NOT RUNNING: Application '{app_name}' is NOT running yet."
    except Exception as e:
        return f"Error checking process: {e}"

def done(message: str = "Task completed") -> str:
    """Call this when the objective is achieved."""
    return f"Done: {message}"
