"""
OS File & Document Specialist Agent.
Handles searching, organizing, reading, and managing files across the local drive.
"""

import os
import shutil
import logging
from typing import Dict, Any, List, Optional

from tools.shell_tools import search_files, organize_directory_by_extension
from agents.os_state import OSAutomationState

logger = logging.getLogger("os_file_agent")

class OSFileAgent:
    name = "OS_File_Agent"
    role = "Searches, organizes, reads, and restructures files and directories."

    def find_files(self, directory: str, pattern: str = "*", recursive: bool = True) -> Dict[str, Any]:
        """Search directory for files."""
        files = search_files(directory, pattern=pattern, recursive=recursive)
        return {
            "status": "success",
            "count": len(files),
            "files": files
        }

    def organize_directory(self, directory: str) -> Dict[str, Any]:
        """Group files into organized categories."""
        return organize_directory_by_extension(directory)

    def read_file_preview(self, file_path: str, max_chars: int = 2000) -> Dict[str, Any]:
        """Read text snippet from a document."""
        if not os.path.exists(file_path):
            return {"status": "error", "message": "File does not exist"}

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(max_chars)
            return {
                "status": "success",
                "file_path": file_path,
                "preview": content,
                "length": len(content)
            }
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def create_or_write_file(self, file_path: str, content: str) -> Dict[str, Any]:
        """Write content to a file."""
        try:
            os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return {"status": "success", "file_path": file_path, "bytes_written": len(content)}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def process_step(self, step: Dict[str, Any], state: OSAutomationState) -> Dict[str, Any]:
        """Execute a file manipulation step."""
        action = step.get("action", "")
        params = step.get("params", {})

        if action == "find_files":
            return self.find_files(
                directory=params.get("directory", "."),
                pattern=params.get("pattern", "*"),
                recursive=params.get("recursive", True)
            )
        elif action == "organize_directory":
            return self.organize_directory(directory=params.get("directory", "."))
        elif action == "read_file":
            return self.read_file_preview(file_path=params.get("file_path", ""))
        elif action == "write_file":
            return self.create_or_write_file(
                file_path=params.get("file_path", ""),
                content=params.get("content", "")
            )
        else:
            return {"status": "error", "message": f"Unknown file action: {action}"}
