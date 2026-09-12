import argparse
import os
import sys
from agent import DesktopAgent

def main():
    parser = argparse.ArgumentParser(description="Desktop Automation Agent powered by Gemini")
    parser.add_argument("goal", type=str, help="The goal you want the agent to accomplish.")
    
    args = parser.parse_args()

    if not os.environ.get("GEMINI_API_KEY"):
        from pathlib import Path
        env_file = Path(__file__).parent / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith("GEMINI_API_KEY="):
                    os.environ["GEMINI_API_KEY"] = line.split("=", 1)[1].strip().strip('"').strip("'")
                    break

    if not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY environment variable is not set.")
        print("Please set it using: set GEMINI_API_KEY=your_key or in a .env file")
        sys.exit(1)

    print("Running in fully autonomous mode. Move mouse to any screen corner to abort.")
    agent = DesktopAgent()
    agent.run(args.goal)

if __name__ == "__main__":
    main()
