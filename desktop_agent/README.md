# Desktop & Browser Automation Agent

A Python-based autonomous agent that uses the Gemini multimodal LLM to "see" your Windows desktop and browser, performing actions (clicking, typing, navigating, scrolling, tab management) to accomplish complex multi-step goals.

## Setup

The dependencies have already been installed in the `.venv` folder. Your API key has been saved in the helper scripts.

## Usage

Run the agent and specify your goal using `run.bat` (or `.\run.ps1` in PowerShell):

### Desktop Example:
```cmd
run.bat "Open the start menu, search for Notepad, and open it."
```

### Multi-Step Browser Automation Example:
```cmd
run.bat "Open browser to Wikipedia, search for Quantum Computing, scroll down to read the overview, and open a new tab with NASA"
```

### Browser Capabilities:
- `open_browser(url)`: Instantly opens your default browser (Chrome/Edge) to any website.
- `browser_navigate(url)`: Focuses address bar and navigates to new URLs.
- `click_and_type(x, y, text, press_enter=True)`: Clicks web input fields, clears placeholder text, types queries, and submits.
- `browser_scroll(direction='down')`: Scrolls up or down web pages to view more content.
- `browser_new_tab(url)`: Opens new tabs with Ctrl+T.
- `browser_close_tab()`: Closes tabs with Ctrl+W.

### Safety Failsafe
`pyautogui.FAILSAFE = True` is enabled. If the agent goes rogue, quickly move your physical mouse to any of the 4 corners of your screen to abort the script immediately.
