import argparse
import os
import sys
from pathlib import Path
from agent import DesktopAgent

def load_api_key():
    if not os.environ.get("GEMINI_API_KEY"):
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.startswith("GEMINI_API_KEY="):
                    val = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if val:
                        os.environ["GEMINI_API_KEY"] = val
                        return

def main():
    # Ensure Windows DPI awareness so mouse coordinates match 1:1 with screenshots
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        pass

    load_api_key()
    parser = argparse.ArgumentParser(description="Desktop Automation Agent powered by Gemini")
    parser.add_argument("goal", type=str, help="The goal you want the agent to accomplish.")
    
    args = parser.parse_args()

    print("Running in fully autonomous mode. Move mouse to any screen corner to abort.")
    agent = DesktopAgent()
    agent.run(args.goal)

if __name__ == "__main__":
    main()
