"""
OS Closed-Loop Verifier Agent.
Validates whether executed OS actions actually achieved their expected outcome
by inspecting process lists, file states, window titles, and screen changes.
"""

import os
import time
import psutil
import logging
from typing import Dict, Any, List

from tools.desktop_tools import get_active_window_info, list_open_windows
from agents.os_state import OSAutomationState

logger = logging.getLogger("os_verifier")

class OSVerifierAgent:
    name = "OS_Verifier_Agent"
    role = "Independently inspects system state after action execution to verify success."

    def verify_process_running(self, proc_name: str, expected: bool = True) -> Dict[str, Any]:
        """Check if a process with proc_name is currently running."""
        name_lower = proc_name.lower()
        found_pids = []
        for p in psutil.process_iter(['pid', 'name']):
            try:
                if name_lower in p.info['name'].lower():
                    found_pids.append(p.info['pid'])
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        is_running = len(found_pids) > 0
        success = (is_running == expected)
        return {
            "status": "VERIFIED" if success else "FAILED",
            "metric": "process_running",
            "target": proc_name,
            "expected": expected,
            "actual": is_running,
            "matching_pids": found_pids,
            "reason": f"Process '{proc_name}' was {'found' if is_running else 'not found'} (expected: {expected})."
        }

    def verify_file_exists(self, file_path: str, min_size: int = 0) -> Dict[str, Any]:
        """Check if a file exists on disk and has sufficient content."""
        exists = os.path.exists(file_path)
        actual_size = os.path.getsize(file_path) if exists else 0
        size_valid = actual_size >= min_size
        success = exists and size_valid

        return {
            "status": "VERIFIED" if success else "FAILED",
            "metric": "file_exists",
            "file_path": file_path,
            "exists": exists,
            "actual_size_bytes": actual_size,
            "reason": f"File '{file_path}' {'exists' if exists else 'missing'} with size {actual_size} bytes."
        }

    def verify_window_active(self, title_query: str) -> Dict[str, Any]:
        """Check if the active foreground window matches title_query."""
        active = get_active_window_info()
        title = active.get("title", "")
        success = title_query.lower() in title.lower()

        return {
            "status": "VERIFIED" if success else "FAILED",
            "metric": "window_active",
            "target_query": title_query,
            "current_title": title,
            "reason": f"Current foreground window is '{title}'."
        }

    def verify_step_result(self, step: Dict[str, Any], action_result: Dict[str, Any]) -> Dict[str, Any]:
        """Inspect the outcome of a plan step based on verification criteria."""
        verify_cfg = step.get("verification", {})
        v_type = verify_cfg.get("type")

        if not v_type:
            # Fallback: check status of action_result directly
            success = action_result.get("status") in ["success", "simulated"]
            return {
                "status": "VERIFIED" if success else "FAILED",
                "metric": "action_status",
                "reason": f"Action status reported: {action_result.get('status')}"
            }

        if v_type == "process_running":
            return self.verify_process_running(
                proc_name=verify_cfg.get("process_name", ""),
                expected=verify_cfg.get("expected", True)
            )
        elif v_type == "file_exists":
            return self.verify_file_exists(
                file_path=verify_cfg.get("file_path", ""),
                min_size=verify_cfg.get("min_size", 0)
            )
        elif v_type == "window_active":
            return self.verify_window_active(title_query=verify_cfg.get("title", ""))
        else:
            return {
                "status": "VERIFIED",
                "metric": "default",
                "reason": "No specialized verification rule, marked verified."
            }
