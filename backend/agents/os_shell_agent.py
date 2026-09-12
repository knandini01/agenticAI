"""
OS Shell & Process Specialist Agent.
Executes PowerShell commands, starts and manages processes, checks system health,
and adheres strictly to safety evaluation.
"""

import time
import logging
from typing import Dict, Any, List, Optional

from tools.shell_tools import (
    execute_powershell, list_processes, list_top_processes, start_process,
    kill_process, get_system_resources, open_browser
)
from safety.os_safety import assess_shell_risk, assess_process_kill_risk
from agents.os_state import OSAutomationState

logger = logging.getLogger("os_shell_agent")

class OSShellAgent:
    name = "OS_Shell_Agent"
    role = "Executes command-line scripts, manages OS processes, and monitors system resources."

    def run_command(self, command: str, timeout: int = 30) -> Dict[str, Any]:
        """Assess safety risk and execute command."""
        risk = assess_shell_risk(command)
        if not risk["allowed"]:
            return {
                "status": "blocked",
                "risk_assessment": risk,
                "message": f"Command execution blocked by safety policy: {risk['reason']}"
            }

        result = execute_powershell(command, timeout_seconds=timeout)
        result["risk_assessment"] = risk
        return result

    def launch_app(self, executable: str, args: Optional[List[str]] = None) -> Dict[str, Any]:
        """Launch an application."""
        return start_process(executable, args)

    def terminate_process(self, pid: int, proc_name: str = "") -> Dict[str, Any]:
        """Terminate a running process with safety check."""
        risk = assess_process_kill_risk(proc_name, pid)
        if not risk["allowed"]:
            return {
                "status": "blocked",
                "risk_assessment": risk,
                "message": f"Process termination blocked: {risk['reason']}"
            }
        return kill_process(pid)

    def get_diagnostics(self) -> Dict[str, Any]:
        """Query system CPU, RAM, Disk, and Battery."""
        return get_system_resources()

    def open_web_url(self, url: str, browser: str = "chrome") -> Dict[str, Any]:
        """Launch web browser with target URL."""
        return open_browser(url=url, browser=browser)

    def process_step(self, step: Dict[str, Any], state: OSAutomationState) -> Dict[str, Any]:
        """Execute a step designated for the Shell Agent."""
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "execute_command":
            cmd = params.get("command", "")
            return self.run_command(cmd, timeout=params.get("timeout", 30))
        elif action == "launch_app":
            exe = params.get("executable", "")
            args = params.get("args")
            return self.launch_app(exe, args)
        elif action == "open_browser":
            url = params.get("url", "https://www.youtube.com")
            browser = params.get("browser", "chrome")
            return self.open_web_url(url=url, browser=browser)
        elif action == "terminate_process":
            pid = params.get("pid")
            name = params.get("name", "")
            return self.terminate_process(pid, name)
        elif action == "get_diagnostics":
            return self.get_diagnostics()
        elif action == "list_processes":
            filter_name = params.get("filter_name")
            return {"status": "success", "processes": list_processes(filter_name=filter_name)}
        elif action == "list_top_processes":
            sort_by = params.get("sort_by", "memory")
            limit = params.get("limit", 10)
            return {"status": "success", "processes": list_top_processes(sort_by=sort_by, limit=limit)}
        else:
            return {"status": "error", "message": f"Unknown shell action: {action}"}
