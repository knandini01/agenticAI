"""
Integration tests for FastAPI OS Automation endpoints.
"""

import os
import sys
import unittest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from main import app

class TestOSAPIEndpoints(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)

    def test_health_check(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "healthy")

    def test_os_diagnostics_endpoint(self):
        response = self.client.get("/os/diagnostics")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cpu_percent", data)
        self.assertIn("memory", data)
        self.assertIn("disk_c", data)
        print(f"[API TEST PASS] /os/diagnostics returned CPU={data['cpu_percent']}%, Memory={data['memory']['percent']}%")

    def test_os_windows_endpoint(self):
        response = self.client.get("/os/windows")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("active_window", data)
        self.assertIn("open_windows", data)
        print(f"[API TEST PASS] /os/windows returned {len(data['open_windows'])} open windows")

    def test_os_screenshot_endpoint(self):
        response = self.client.post("/os/screenshot")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "success")
        self.assertIn("grid_path", data)
        print(f"[API TEST PASS] /os/screenshot returned image {data['width']}x{data['height']}")

    def test_os_automate_endpoint(self):
        response = self.client.post(
            "/os/automate",
            json={"goal": "Check system diagnostics and memory health"}
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["is_completed"])
        self.assertIn("OS_Shell_Agent", data["required_agents"])
        self.assertGreaterEqual(len(data["actions_history"]), 1)
        print(f"[API TEST PASS] /os/automate completed task {data['task_id']} with summary: {data['final_summary']}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
