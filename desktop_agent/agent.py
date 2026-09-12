import time
from PIL import Image
import mss
import tools
from llm_client import LLMClient

class DesktopAgent:
    def __init__(self):
        self.client = LLMClient()
        self.history = []

    def capture_screen(self) -> Image.Image:
        """Captures the primary monitor."""
        try:
            from PIL import ImageGrab
            img = ImageGrab.grab()
            if img:
                return img
        except Exception:
            pass

        with mss.mss() as sct:
            monitor = sct.monitors[1]
            sct_img = sct.grab(monitor)
            return Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")

    def run(self, goal: str):
        print(f"Starting agent with goal: '{goal}'")
        print("Press Ctrl+C to abort at any time. Failsafe enabled (move mouse to a corner to abort).")
        
        while True:
            print("\nCapturing screen...")
            screenshot = self.capture_screen()
            
            print("Thinking...")
            action = self.client.get_action(goal, screenshot, self.history)
            
            name = action.get('name')
            args = action.get('args', {})
            
            print(f"\nModel decided to call: {name}({args})")
            
            if name == 'message':
                print(f"Message from model: {args.get('text')}")
                self.history.append(f"Model message: {args.get('text')}")
                continue
            elif name == 'error':
                print(f"Error: {args.get('message')}")
                break

            # Execute directly without confirmation

            # Execute
            result = ""
            if name == 'click':
                result = tools.click(args.get('x'), args.get('y'))
            elif name == 'double_click':
                result = tools.double_click(args.get('x'), args.get('y'))
            elif name == 'type_text':
                result = tools.type_text(args.get('text'), press_enter=args.get('press_enter', False))
            elif name == 'press_key':
                result = tools.press_key(args.get('key'))
            elif name == 'hotkey':
                result = tools.hotkey(args.get('keys', []))
            elif name == 'wait':
                result = tools.wait(args.get('seconds', 1.0))
            elif name == 'check_app_opened':
                result = tools.check_app_opened(args.get('app_name', ''))
            elif name == 'open_browser':
                result = tools.open_browser(args.get('url', 'https://www.google.com'))
            elif name == 'browser_navigate':
                result = tools.browser_navigate(args.get('url', ''))
            elif name == 'browser_new_tab':
                result = tools.browser_new_tab(args.get('url', ''))
            elif name == 'browser_close_tab':
                result = tools.browser_close_tab()
            elif name == 'click_and_type':
                result = tools.click_and_type(
                    x=args.get('x'),
                    y=args.get('y'),
                    text=args.get('text', ''),
                    clear_first=args.get('clear_first', True),
                    press_enter=args.get('press_enter', False)
                )
            elif name == 'browser_scroll':
                result = tools.browser_scroll(
                    direction=args.get('direction', 'down'),
                    amount=args.get('amount', 400)
                )
            elif name == 'done':
                # Automated verification safeguard for "open" goals
                goal_lower = goal.lower()
                detected_app = None
                for app in ['notepad', 'calculator', 'calc', 'chrome', 'msedge', 'edge', 'cmd', 'powershell', 'word', 'excel', 'settings']:
                    if app in goal_lower:
                        detected_app = 'calculator' if app == 'calc' else app
                        break

                if detected_app:
                    status = tools.check_app_opened(detected_app)
                    print(f"Self-verification check for '{detected_app}': {status}")
                    if "NOT RUNNING" in status:
                        print(f"Warning: '{detected_app}' is not yet running! Pressing Enter and waiting to launch...")
                        tools.press_key('enter')
                        tools.wait(2.0)
                        status_retry = tools.check_app_opened(detected_app)
                        if "NOT RUNNING" in status_retry:
                            self.history.append(f"Verification: '{detected_app}' is not running yet. Make sure to press Enter or click the result.")
                            continue

                result = tools.done(args.get('message', ''))
                print(f"Goal verified and achieved: {result}")
                break
            else:
                result = f"Unknown tool: {name}"

            print(f"Action result: {result}")
            self.history.append(f"{name}({args}) -> {result}")

            # Pause briefly to let UI update before next screen capture
            time.sleep(0.4)
