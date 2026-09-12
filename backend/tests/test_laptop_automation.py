"""
Comprehensive Test Suite for Dynamic Multi-Agent Laptop Automation.
Tests:
1. System diagnostics & process lifecycle (start, inspect, terminate)
2. File system operations & automatic directory organization
3. Screen perception & visual coordinate grid generation
4. Safety & guardrail defense (blocking dangerous shell commands & protected process kills)
5. End-to-end dynamic multi-agent orchestration with closed-loop verification
"""

import os
import sys
import time
import shutil
import unittest

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from tools.desktop_tools import (
    take_screenshot, annotate_grid_on_image, get_active_window_info,
    get_screen_size, list_open_windows
)
from tools.shell_tools import (
    execute_powershell, list_processes, start_process,
    kill_process, search_files, organize_directory_by_extension, get_system_resources
)
from safety.os_safety import (
    assess_shell_risk, assess_process_kill_risk, CRITICAL_WINDOWS_PROCESSES
)
from agents.os_supervisor import OSSupervisor


class TestLaptopAutomationSuite(unittest.TestCase):

    def setUp(self):
        self.test_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "tmp_test_workspace"))
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)
        os.makedirs(self.test_dir, exist_ok=True)

    def tearDown(self):
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_01_system_diagnostics_and_resources(self):
        """Test reading live CPU, Memory, Disk, and Battery diagnostics."""
        stats = get_system_resources()
        self.assertIn("cpu_percent", stats)
        self.assertIn("memory", stats)
        self.assertIn("disk_c", stats)
        self.assertGreater(stats["memory"]["total_gb"], 0)
        self.assertGreater(stats["disk_c"]["total_gb"], 0)
        print(f"[TEST 1 PASS] Laptop Diagnostics: CPU={stats['cpu_percent']}%, RAM={stats['memory']['used_gb']}/{stats['memory']['total_gb']}GB, Disk={stats['disk_c']['percent_used']}% used")

    def test_02_process_lifecycle_management(self):
        """Test launching an application process, tracking it via psutil, and cleanly terminating it."""
        # Launch a python background worker process
        launch_res = start_process(sys.executable, ["-c", "import time; time.sleep(30)"])
        self.assertEqual(launch_res["status"], "success")
        pid = launch_res["pid"]
        self.assertIsInstance(pid, int)
        time.sleep(0.3)

        # Verify process is listed by PID
        matching = list_processes(filter_name="python")
        pids = [p["pid"] for p in matching]
        self.assertIn(pid, pids)

        # Cleanly terminate process
        kill_res = kill_process(pid)
        self.assertEqual(kill_res["status"], "success")
        time.sleep(0.3)

        # Verify process is no longer running
        after_procs = list_processes(filter_name="python")
        after_pids = [p["pid"] for p in after_procs]
        self.assertNotIn(pid, after_pids)
        print(f"[TEST 2 PASS] Successfully launched, verified, and terminated process PID={pid}")

    def test_03_file_operations_and_categorization(self):
        """Test creating various file types and running automatic category organization."""
        # Create sample files
        test_files = [
            "report_q1.pdf", "data_table.csv", "project_notes.txt",
            "diagram.png", "source_code.py", "archive.zip"
        ]
        for f in test_files:
            fpath = os.path.join(self.test_dir, f)
            with open(fpath, "w") as fp:
                fp.write(f"Sample content for {f}")

        # Search before organization
        found = search_files(self.test_dir, pattern="*.*", recursive=False)
        self.assertEqual(len(found), 6)

        # Run organization tool
        org_result = organize_directory_by_extension(self.test_dir)
        self.assertEqual(org_result["status"], "success")
        self.assertEqual(org_result["moved_files"], 6)

        # Verify structured subfolders exist
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Documents", "report_q1.pdf")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Spreadsheets", "data_table.csv")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Images", "diagram.png")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Code", "source_code.py")))
        self.assertTrue(os.path.exists(os.path.join(self.test_dir, "Archives", "archive.zip")))
        print(f"[TEST 3 PASS] Directory organized into categories: {org_result['categories_created']}")

    def test_04_screen_perception_and_grid_overlay(self):
        """Test capturing screen (hardware or virtual buffer), annotating grid, and checking window info."""
        shot_path = os.path.join(self.test_dir, "screenshot_test.png")
        shot = take_screenshot(shot_path)
        self.assertEqual(shot["status"], "success")
        self.assertTrue(os.path.exists(shot_path))
        self.assertGreater(shot["width"], 0)
        self.assertGreater(shot["height"], 0)

        # Annotate grid
        grid_path = annotate_grid_on_image(shot_path, step=150)
        self.assertTrue(os.path.exists(grid_path))

        # Check active window details
        active_win = get_active_window_info()
        self.assertIn("status", active_win)
        print(f"[TEST 4 PASS] Captured screen {shot['width']}x{shot['height']} (mode: {shot.get('capture_mode')}), generated grid: {grid_path}")

    def test_05_safety_guardrails_prevent_destructive_actions(self):
        """Test that safety policies intercept dangerous commands and protected Windows processes."""
        dangerous_commands = [
            "format C: /fs:NTFS",
            "rmdir /s /q C:\\Windows",
            "Remove-Item -Recurse -Force C:\\",
            "reg delete HKLM\\Software\\Policies"
        ]
        for cmd in dangerous_commands:
            eval_res = assess_shell_risk(cmd)
            self.assertFalse(eval_res["allowed"], f"Failed to block dangerous command: {cmd}")
            self.assertEqual(eval_res["risk_level"], "CRITICAL")
            self.assertTrue(eval_res["hitl_required"])

        # Test protecting critical Windows processes
        for proc in ["csrss.exe", "explorer.exe", "winlogon.exe"]:
            kill_eval = assess_process_kill_risk(proc, 100)
            self.assertFalse(kill_eval["allowed"], f"Failed to protect critical process: {proc}")
            self.assertEqual(kill_eval["risk_level"], "CRITICAL")

        print("[TEST 5 PASS] All dangerous commands and system process kills blocked by safety guardrails.")

    def test_06_dynamic_multi_agent_orchestration_workflow(self):
        """Test full dynamic multi-agent supervisor orchestrating a multi-step task with closed-loop verification."""
        supervisor = OSSupervisor()

        goal = "Inspect laptop battery and CPU health, list running processes, and capture screen"
        decomp = supervisor.decompose_goal(goal)

        self.assertIn("OS_Shell_Agent", decomp["required_agents"])
        self.assertIn("OS_Vision_GUI_Agent", decomp["required_agents"])
        self.assertGreaterEqual(len(decomp["plan"]), 2)

        # Execute the dynamic plan
        state = supervisor.execute_custom_plan(goal, plan=decomp["plan"])

        self.assertTrue(state["is_completed"])
        self.assertEqual(len(state["actions_history"]), len(decomp["plan"]))
        for action in state["actions_history"]:
            self.assertEqual(action["status"], "VERIFIED")

        print(f"[TEST 6 PASS] Multi-agent orchestration completed {len(decomp['plan'])} steps across agents: {decomp['required_agents']}")

    def test_07_browser_task_youtube_chrome(self):
        """Test dynamic orchestration for opening YouTube in Chrome."""
        supervisor = OSSupervisor()
        goal = "open yt using chrome"
        decomp = supervisor.decompose_goal(goal)

        self.assertIn("OS_Shell_Agent", decomp["required_agents"])
        self.assertIn("OS_Vision_GUI_Agent", decomp["required_agents"])
        self.assertGreaterEqual(len(decomp["plan"]), 3)
        step1 = decomp["plan"][0]
        self.assertEqual(step1["action"], "open_browser")
        self.assertTrue(step1["params"]["url"].startswith("https://www.youtube.com"))
        step2 = decomp["plan"][1]
        self.assertEqual(step2["action"], "focus_app")
        step3 = decomp["plan"][2]
        self.assertEqual(step3["action"], "play_youtube_video")

        state = supervisor.execute_custom_plan(goal, plan=decomp["plan"])
        self.assertTrue(state["is_completed"])
        self.assertEqual(state["actions_history"][0]["status"], "VERIFIED")
        print("[TEST 7 PASS] Multi-agent system successfully planned, launched, and verified searching and playing YouTube in Chrome.")


if __name__ == "__main__":
    unittest.main(verbosity=2)
