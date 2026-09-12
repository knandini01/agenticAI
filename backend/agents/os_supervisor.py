"""
Dynamic Multi-Agent Orchestrator & Supervisor for Laptop Automation.
Dispatches specialized agents (Shell, File, Vision/GUI) based on user goal,
coordinates cross-agent workflows, verifies post-step states, and handles errors dynamically.
"""

import time
import uuid
import logging
from typing import Dict, Any, List, Optional

from agents.os_state import OSAutomationState, ActionRecord
from agents.os_shell_agent import OSShellAgent
from agents.os_file_agent import OSFileAgent
from agents.os_vision_agent import OSVisionAgent
from agents.os_verifier import OSVerifierAgent
from safety.os_safety import assess_shell_risk

logger = logging.getLogger("os_supervisor")

class OSSupervisor:
    def __init__(self):
        self.shell_agent = OSShellAgent()
        self.file_agent = OSFileAgent()
        self.vision_agent = OSVisionAgent()
        self.verifier = OSVerifierAgent()

    def decompose_goal(self, user_goal: str) -> Dict[str, Any]:
        """
        Decompose a high-level user goal into an ordered multi-agent plan.
        Detects required agents and action sequence.
        """
        goal_lower = user_goal.lower()
        plan: List[Dict[str, Any]] = []
        required_agents = set()

        # Pattern 1: Diagnostics / System Resource check
        if any(w in goal_lower for w in ["battery", "cpu", "resource", "ram", "memory", "specs", "health"]):
            required_agents.add("OS_Shell_Agent")
            plan.append({
                "step_id": len(plan) + 1,
                "agent": "OS_Shell_Agent",
                "description": "Inspect CPU, Memory, Disk, and Battery diagnostics",
                "action": "get_diagnostics",
                "params": {},
                "verification": {"type": "action_status"}
            })

        # Pattern 2: Process audit or management
        if any(w in goal_lower for w in ["top process", "high ram", "high cpu", "memory hog", "heavy process"]):
            required_agents.add("OS_Shell_Agent")
            plan.append({
                "step_id": len(plan) + 1,
                "agent": "OS_Shell_Agent",
                "description": "Identify top memory and CPU consuming processes",
                "action": "list_top_processes",
                "params": {"sort_by": "cpu" if "cpu" in goal_lower else "memory", "limit": 10},
                "verification": {"type": "action_status"}
            })
        elif "process" in goal_lower or "list app" in goal_lower or "running" in goal_lower:
            required_agents.add("OS_Shell_Agent")
            plan.append({
                "step_id": len(plan) + 1,
                "agent": "OS_Shell_Agent",
                "description": "Query running processes matching criteria",
                "action": "list_processes",
                "params": {"limit": 15},
                "verification": {"type": "action_status"}
            })

        # Pattern 2.5: Browser & YouTube Automation (Search & Play)
        if any(w in goal_lower for w in ["chrome", "browser", "youtube", "yt", "open site", "url", "website", "web", "play"]):
            is_youtube = any(w in goal_lower for w in ["youtube", "yt"]) or ("play" in goal_lower and not any(k in goal_lower for k in ["game", "sport"]))
            
            if is_youtube:
                import urllib.parse
                import re

                # Extract specific search query if provided
                query = None
                m = re.search(r'(?:search for|search|play|watch|listen to)\s+["\']?([^"\']+)["\']?\s+(?:on|in|using)\s+(?:youtube|yt|chrome)', goal_lower)
                if m:
                    query = m.group(1).strip()

                if not query:
                    m = re.search(r'(?:youtube|yt|chrome)[^a-z0-9]+(?:and\s+)?(?:search for|search|play|watch|listen to)\s+["\']?([^"\']+)["\']?', goal_lower)
                    if m:
                        cand = m.group(1).strip()
                        cand = re.sub(r'\s+(using chrome|in chrome|on chrome|please|okay|bro)$', '', cand).strip()
                        if cand:
                            query = cand

                if not query:
                    m = re.search(r'(?:search for|search|play|find)\s+(.+)', goal_lower)
                    if m:
                        cand = m.group(1).strip()
                        cand = re.sub(r'\s+(on youtube|in youtube|on yt|in yt|using chrome|in chrome|okay|bro|please)$', '', cand).strip()
                        if cand and cand not in ["youtube", "yt", "chrome", "browser", "video"]:
                            query = cand

                # Default fallback query if user simply asked to open YouTube or play
                if not query:
                    query = "lofi hip hop radio beats to relax"

                target_url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
                browser_name = "chrome" if "chrome" in goal_lower else "default"

                required_agents.add("OS_Shell_Agent")
                required_agents.add("OS_Vision_GUI_Agent")

                # Step 1: Open Chrome to YouTube search results
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_Shell_Agent",
                    "description": f"Open YouTube search for '{query}' in Google Chrome",
                    "action": "open_browser",
                    "params": {"url": target_url, "browser": browser_name},
                    "verification": {
                        "type": "process_running",
                        "process_name": "chrome.exe",
                        "expected": True
                    }
                })

                # Step 2: Focus the browser window and wait for results
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_Vision_GUI_Agent",
                    "description": "Focus Google Chrome window and allow YouTube search results to load",
                    "action": "focus_app",
                    "params": {"title": "YouTube"},
                    "verification": {"type": "action_status"}
                })

                # Step 3: Click first video and trigger playback
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_Vision_GUI_Agent",
                    "description": f"Click the top video result to start playing '{query}'",
                    "action": "play_youtube_video",
                    "params": {"query": query},
                    "verification": {"type": "action_status"}
                })

            else:
                target_url = "https://www.google.com"
                if "github" in goal_lower:
                    target_url = "https://github.com"
                for token in user_goal.split():
                    if token.startswith("http://") or token.startswith("https://"):
                        target_url = token
                        break

                browser_name = "chrome" if "chrome" in goal_lower else "default"
                required_agents.add("OS_Shell_Agent")
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_Shell_Agent",
                    "description": f"Open '{target_url}' using Google Chrome",
                    "action": "open_browser",
                    "params": {"url": target_url, "browser": browser_name},
                    "verification": {
                        "type": "process_running",
                        "process_name": "chrome.exe",
                        "expected": True
                    }
                })

        # Pattern 3: Launch Notepad or text editor & optionally write
        if "notepad" in goal_lower and any(w in goal_lower for w in ["open", "launch", "start", "write", "note"]):
            required_agents.add("OS_Shell_Agent")
            plan.append({
                "step_id": len(plan) + 1,
                "agent": "OS_Shell_Agent",
                "description": "Launch Notepad process",
                "action": "launch_app",
                "params": {"executable": "notepad.exe"},
                "verification": {
                    "type": "process_running",
                    "process_name": "notepad.exe",
                    "expected": True
                }
            })
            if any(w in goal_lower for w in ["write", "type", "put", "text"]):
                required_agents.add("OS_Vision_GUI_Agent")
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_Vision_GUI_Agent",
                    "description": "Type automated notes into active window",
                    "action": "type",
                    "params": {"text": "Agentic AI Desktop Copilot: Automation task executed successfully.\n", "press_enter": True},
                    "verification": {"type": "action_status"}
                })

        # Pattern 4: Screen capture / observation
        if any(w in goal_lower for w in ["screenshot", "screen", "see", "look", "observe"]):
            required_agents.add("OS_Vision_GUI_Agent")
            plan.append({
                "step_id": len(plan) + 1,
                "agent": "OS_Vision_GUI_Agent",
                "description": "Capture screen and active window context",
                "action": "observe_screen",
                "params": {"add_grid": True},
                "verification": {"type": "action_status"}
            })

        # Pattern 5: File search or organization across common folders
        if any(w in goal_lower for w in ["organize", "find file", "search file", "clean download", "file", "folder"]):
            import os
            from tools.shell_tools import get_user_folders
            user_dirs = get_user_folders()
            
            # Resolve target directory
            target_dir = "."
            if "download" in goal_lower:
                target_dir = user_dirs["downloads"]
            elif "desktop" in goal_lower:
                target_dir = user_dirs["desktop"]
            elif "document" in goal_lower:
                target_dir = user_dirs["documents"]

            required_agents.add("OS_File_Agent")
            if any(w in goal_lower for w in ["organize", "clean", "sort"]):
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_File_Agent",
                    "description": f"Organize files in '{target_dir}' into categorized folders",
                    "action": "organize_directory",
                    "params": {"directory": target_dir},
                    "verification": {"type": "action_status"}
                })
            else:
                pattern = "*.pdf" if "pdf" in goal_lower else ("*.csv" if "csv" in goal_lower else "*")
                plan.append({
                    "step_id": len(plan) + 1,
                    "agent": "OS_File_Agent",
                    "description": f"Search for files matching '{pattern}' in '{target_dir}'",
                    "action": "find_files",
                    "params": {"directory": target_dir, "pattern": pattern},
                    "verification": {"type": "action_status"}
                })

        # Fallback if no specific template matched: shell command or generic perception
        if not plan:
            required_agents.add("OS_Shell_Agent")
            plan.append({
                "step_id": 1,
                "agent": "OS_Shell_Agent",
                "description": "Execute requested command via PowerShell",
                "action": "execute_command",
                "params": {"command": user_goal},
                "verification": {"type": "action_status"}
            })

        return {
            "plan": plan,
            "required_agents": list(required_agents)
        }

    def execute_custom_plan(self, user_goal: str, plan: Optional[List[Dict[str, Any]]] = None) -> OSAutomationState:
        """
        Executes a dynamic multi-agent plan with closed-loop verification.
        """
        task_id = str(uuid.uuid4())[:8]
        if plan is None:
            decomp = self.decompose_goal(user_goal)
            plan = decomp["plan"]
            required_agents = decomp["required_agents"]
        else:
            required_agents = list({s.get("agent") for s in plan if s.get("agent")})

        state: OSAutomationState = {
            "task_id": task_id,
            "user_goal": user_goal,
            "required_agents": required_agents,
            "plan": plan,
            "current_step_index": 0,
            "active_agent": "Supervisor",
            "actions_history": [],
            "trace_log": [],
            "risk_score": 0.0,
            "risk_level": "LOW",
            "hitl_required": False,
            "is_completed": False,
            "final_summary": ""
        }

        state["trace_log"].append({
            "timestamp": time.time(),
            "agent": "Supervisor",
            "event": "Task initiated",
            "details": f"Goal: {user_goal} | Agents selected: {', '.join(required_agents)}"
        })

        for idx, step in enumerate(plan):
            state["current_step_index"] = idx
            target_agent = step.get("agent")
            state["active_agent"] = target_agent

            state["trace_log"].append({
                "timestamp": time.time(),
                "agent": target_agent,
                "event": f"Executing Step {idx + 1}/{len(plan)}",
                "details": step.get("description", "")
            })

            # Dispatch to appropriate agent
            start_time = time.time()
            if target_agent == "OS_Shell_Agent":
                result = self.shell_agent.process_step(step, state)
            elif target_agent == "OS_File_Agent":
                result = self.file_agent.process_step(step, state)
            elif target_agent == "OS_Vision_GUI_Agent":
                result = self.vision_agent.process_step(step, state)
            else:
                result = {"status": "error", "message": f"Unsupported agent: {target_agent}"}

            # Closed-loop verification
            verification = self.verifier.verify_step_result(step, result)
            is_verified = verification.get("status") == "VERIFIED"

            # Record action
            record: ActionRecord = {
                "agent": target_agent,
                "action_type": step.get("action", "unknown"),
                "command_or_target": str(step.get("params", {})),
                "result": result,
                "status": "VERIFIED" if is_verified else "FAILED",
                "timestamp": time.time()
            }
            state["actions_history"].append(record)

            state["trace_log"].append({
                "timestamp": time.time(),
                "agent": "OS_Verifier_Agent",
                "event": f"Step {idx + 1} Verification: {verification.get('status')}",
                "details": verification.get("reason", "")
            })

            # If an action was blocked by safety policy
            if result.get("status") == "blocked":
                state["risk_score"] = 0.95
                state["risk_level"] = "CRITICAL"
                state["hitl_required"] = True
                state["error"] = result.get("message")
                state["is_completed"] = False
                state["final_summary"] = f"Workflow halted: {result.get('message')}"
                return state

        state["is_completed"] = True
        state["final_summary"] = f"Successfully orchestrated {len(plan)} steps across agents: {', '.join(required_agents)}."
        state["trace_log"].append({
            "timestamp": time.time(),
            "agent": "Supervisor",
            "event": "Workflow Completed",
            "details": state["final_summary"]
        })

        return state
