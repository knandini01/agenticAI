import pyautogui
import time
import ctypes

# Enable Windows Per-Monitor DPI Awareness so screen coordinates match 1:1
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

# Safely configure PyAutoGUI - smooth and responsive
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05

def launch_app(app_name: str) -> str:
    """Instantly open any Windows application via Start menu search and launch it directly."""
    try:
        pyautogui.press('win')
        time.sleep(0.3)
        pyautogui.typewrite(app_name, interval=0.01)
        time.sleep(0.3)
        pyautogui.press('enter')
        time.sleep(1.0)
        return f"Launched application: '{app_name}'"
    except Exception as e:
        return f"Error launching app: {e}"

def click(x: int, y: int) -> str:
    """Smoothly moves the mouse to coordinates (x, y) with natural deceleration and clicks."""
    try:
        screen_w, screen_h = pyautogui.size()
        target_x = max(0, min(int(x), screen_w - 1))
        target_y = max(0, min(int(y), screen_h - 1))
        
        # Smooth natural curve to target
        pyautogui.moveTo(target_x, target_y, duration=0.35, tween=pyautogui.easeOutQuad)
        time.sleep(0.08)  # Let browser hover effects settle
        pyautogui.click()
        return f"Smoothly clicked at ({target_x}, {target_y})"
    except Exception as e:
        return f"Error clicking: {e}"

def double_click(x: int, y: int) -> str:
    """Smoothly moves the mouse to coordinates (x, y) and double clicks."""
    try:
        screen_w, screen_h = pyautogui.size()
        target_x = max(0, min(int(x), screen_w - 1))
        target_y = max(0, min(int(y), screen_h - 1))
        
        pyautogui.moveTo(target_x, target_y, duration=0.35, tween=pyautogui.easeOutQuad)
        time.sleep(0.08)
        pyautogui.doubleClick()
        return f"Smoothly double clicked at ({target_x}, {target_y})"
    except Exception as e:
        return f"Error double clicking: {e}"

def type_text(text: str, press_enter: bool = False) -> str:
    """Type the given string of text. If press_enter is True, presses the Enter key immediately after typing."""
    try:
        pyautogui.typewrite(text, interval=0.01)
        if press_enter:
            time.sleep(0.2)
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

def open_url(url: str, browser: str = "chrome") -> str:
    """Open a URL directly in Chrome or default browser. Can open YouTube searches directly."""
    import subprocess
    import webbrowser
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url
    try:
        subprocess.Popen(f'start {browser} "{url}"', shell=True)
        time.sleep(2.0)
        return f"Opened in {browser}: {url}"
    except Exception:
        webbrowser.open(url)
        time.sleep(2.0)
        return f"Opened in browser: {url}"

def focus_address_bar() -> str:
    """Presses Ctrl+L to immediately focus and highlight the browser address bar."""
    try:
        pyautogui.hotkey('ctrl', 'l')
        time.sleep(0.3)
        return "Focused browser address bar with Ctrl+L"
    except Exception as e:
        return f"Error focusing address bar: {e}"

def check_window_title_contains(keyword: str) -> str:
    """Checks whether any open window contains the keyword in its title."""
    import pygetwindow as gw
    try:
        matches = [t for t in gw.getAllTitles() if keyword.lower() in t.lower()]
        if matches:
            return f"VERIFIED: Window found with title: '{matches[0]}'"
        return f"NOT FOUND: No open window title matching '{keyword}'"
    except Exception as e:
        return f"Error checking window title: {e}"

def maximize_window() -> str:
    """Maximizes the active window (Win + Up Arrow) so browser coordinates are standard full screen."""
    try:
        pyautogui.hotkey('win', 'up')
        time.sleep(0.4)
        return "Maximized active window"
    except Exception as e:
        return f"Error maximizing window: {e}"

def click_first_video() -> str:
    """Clicks the first video result card on YouTube search results and starts playback."""
    try:
        # First video thumbnail center in full screen YouTube is around (480, 270)
        screen_w, screen_h = pyautogui.size()
        target_x = int(screen_w * 0.25) if screen_w < 1920 else 490
        target_y = int(screen_h * 0.26) if screen_h < 1080 else 275
        
        pyautogui.moveTo(target_x, target_y, duration=0.4, tween=pyautogui.easeOutQuad)
        time.sleep(0.1)
        pyautogui.click()
        time.sleep(1.5)
        return f"Clicked first video result at ({target_x}, {target_y})"
    except Exception as e:
        return f"Error clicking first video: {e}"

def done(message: str = "Task completed") -> str:
    """Call this when the objective is achieved."""
    return f"Done: {message}"
