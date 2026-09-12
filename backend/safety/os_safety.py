"""
OS Safety & Guardrail System for Laptop Automation.
Evaluates safety risks before executing OS actions (shell commands, process terminations, file deletions).
Prevents catastrophic accidents and enforces Human-in-the-Loop (HITL) authorization for critical operations.
"""

import re
import os
from typing import Dict, Any, List, Tuple

# Critical Windows system processes that must NEVER be terminated by agents
CRITICAL_WINDOWS_PROCESSES = {
    "csrss.exe", "wininit.exe", "winlogon.exe", "services.exe", "lsass.exe",
    "smss.exe", "svchost.exe", "system", "system idle process", "explorer.exe",
    "dwm.exe", "taskmgr.exe"
}

# High-risk command patterns (regexes)
HIGH_RISK_SHELL_PATTERNS = [
    r"format\s+[a-zA-Z]:",                         # Drive formatting
    r"rmdir\s+/[sS]",                              # Recursive directory deletion (cmd)
    r"del\s+/[fF]\s+/[sS]\s+/[qQ]\s+[a-zA-Z]:\\", # Root drive purge
    r"Remove-Item.*-Recurse.*(-Force)?.*[C-Z]:\\", # Recursive root PowerShell wipe
    r"Clear-Disk",                                 # PowerShell disk clearing
    r"reg\s+(delete|add)\s+hklm",                  # Registry modifications to HKLM
    r"Set-ExecutionPolicy\s+Unrestricted",         # Disabling script execution restrictions
    r"bcdedit",                                    # Boot configuration edits
    r"takeown",                                    # Permission hijacking
    r"icacls.*grant.*everyone"                     # Mass security permission changes
]

# Sensitive directories that should not be touched
PROTECTED_DIRECTORIES = [
    os.environ.get("SystemRoot", "C:\\Windows").lower(),
    os.environ.get("ProgramFiles", "C:\\Program Files").lower(),
    os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)").lower(),
]


def assess_shell_risk(command: str) -> Dict[str, Any]:
    """
    Evaluates the safety and risk level of a shell command before execution.
    Returns risk score (0.0 to 1.0), risk level (LOW/MEDIUM/HIGH/CRITICAL),
    and whether Human-in-the-Loop (HITL) authorization is mandatory.
    """
    cmd_lower = command.lower().strip()

    # 1. Critical pattern match
    for pattern in HIGH_RISK_SHELL_PATTERNS:
        if re.search(pattern, cmd_lower, re.IGNORECASE):
            return {
                "risk_score": 0.98,
                "risk_level": "CRITICAL",
                "hitl_required": True,
                "reason": f"Command matches dangerous pattern: {pattern}",
                "allowed": False
            }

    # 2. Protected system directory check
    for sys_dir in PROTECTED_DIRECTORIES:
        if sys_dir in cmd_lower and any(act in cmd_lower for act in ["delete", "remove", "del ", "rmdir", "erase"]):
            return {
                "risk_score": 0.95,
                "risk_level": "CRITICAL",
                "hitl_required": True,
                "reason": f"Attempting to modify protected system directory: {sys_dir}",
                "allowed": False
            }

    # 3. Medium risk patterns (software installations, process kills)
    if any(k in cmd_lower for k in ["kill", "stop-process", "taskkill"]):
        return {
            "risk_score": 0.55,
            "risk_level": "MEDIUM",
            "hitl_required": False,
            "reason": "Process termination command",
            "allowed": True
        }

    if any(k in cmd_lower for k in ["pip install", "npm install", "choco install", "winget install"]):
        return {
            "risk_score": 0.40,
            "risk_level": "MEDIUM",
            "hitl_required": False,
            "reason": "Software package installation",
            "allowed": True
        }

    # Standard safe read/diagnostic operations
    return {
        "risk_score": 0.05,
        "risk_level": "LOW",
        "hitl_required": False,
        "reason": "Safe read-only or standard user operation",
        "allowed": True
    }


def assess_process_kill_risk(proc_name: str, pid: int) -> Dict[str, Any]:
    """
    Checks if a target process is safe to terminate.
    """
    name_lower = proc_name.lower().strip()
    if name_lower in CRITICAL_WINDOWS_PROCESSES:
        return {
            "risk_score": 1.0,
            "risk_level": "CRITICAL",
            "hitl_required": True,
            "reason": f"Target process '{proc_name}' is a protected Windows core system process.",
            "allowed": False
        }

    if pid <= 4:
        return {
            "risk_score": 1.0,
            "risk_level": "CRITICAL",
            "hitl_required": True,
            "reason": f"PID {pid} is Windows Kernel or System process.",
            "allowed": False
        }

    return {
        "risk_score": 0.30,
        "risk_level": "LOW",
        "hitl_required": False,
        "reason": f"Process '{proc_name}' (PID: {pid}) is safe to manage.",
        "allowed": True
    }
