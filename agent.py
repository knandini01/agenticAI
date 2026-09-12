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
            action_res = self.client.get_action(goal, screenshot, self.history)
            res_type = action_res.get('type')
            
            if res_type == 'message':
                msg = action_res.get('text')
                print(f"Message from model: {msg}")
                self.history.append(f"Model message: {msg}")
                continue
            elif res_type == 'error':
                print(f"Error: {action_res.get('message')}")
                break

            actions = action_res.get('actions', [])
            should_break = False

            for action in actions:
                name = action.get('name')
                args = action.get('args', {})
                print(f"\nExecuting action: {name}({args})")

                if name == 'open_url':
                    result = tools.open_url(args.get('url', ''), browser=args.get('browser', 'chrome'))
                elif name == 'maximize_window':
                    result = tools.maximize_window()
                elif name == 'click_first_video':
                    result = tools.click_first_video()
                elif name == 'focus_address_bar':
                    result = tools.focus_address_bar()
                elif name == 'check_window_title_contains':
                    result = tools.check_window_title_contains(args.get('keyword', ''))
                elif name == 'launch_app':
                    result = tools.launch_app(args.get('app_name', ''))
                elif name == 'click':
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
                    result = tools.wait(args.get('seconds', 0.5))
                elif name == 'check_app_opened':
                    result = tools.check_app_opened(args.get('app_name', ''))
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
                            print(f"Warning: '{detected_app}' is not yet running! Pressing Enter and waiting...")
                            tools.press_key('enter')
                            tools.wait(1.0)
                            status_retry = tools.check_app_opened(detected_app)
                            if "NOT RUNNING" in status_retry:
                                self.history.append(f"Verification: '{detected_app}' is not running yet.")
                                continue

                    result = tools.done(args.get('message', ''))
                    print(f"Goal verified and achieved: {result}")
                    should_break = True
                    break
                else:
                    result = f"Unknown tool: {name}"

                print(f"Action result: {result}")
                self.history.append(f"{name}({args}) -> {result}")

            if should_break:
                break

            # Snappy delay before next screen capture
            time.sleep(0.5)
