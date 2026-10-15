"""
test_server.py — Unit and Integration Tests for Localhost Web Server
======================================================================
Tests all REST endpoints and static dashboard delivery of server.py
using Python standard library (http.server, urllib.request, unittest).
"""

import unittest
import threading
import urllib.request
import urllib.error
import urllib.parse
import json
import tempfile
from pathlib import Path
from http.server import HTTPServer

from server import CampusNavigatorHandler
from services.obstacle_manager import ObstacleManager


class TestServerEndpoints(unittest.TestCase):
    """Test suite for the built-in HTTP server REST API and web UI."""

    @classmethod
    def setUpClass(cls):
        """Start a test server on an ephemeral OS port (port 0) with isolated obstacles."""
        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_obs_file = Path(cls.temp_dir.name) / "test_obstacles.json"

        # Initialize handler services with isolated obstacles file
        CampusNavigatorHandler.initialize_services()
        CampusNavigatorHandler.obstacle_mgr = ObstacleManager(file_path=cls.temp_obs_file)

        # Port 0 lets OS assign a free port automatically
        cls.httpd = HTTPServer(("127.0.0.1", 0), CampusNavigatorHandler)
        cls.port = cls.httpd.server_port
        cls.base_url = f"http://127.0.0.1:{cls.port}"

        # Run server in a daemon thread
        cls.server_thread = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.server_thread.start()

    @classmethod
    def tearDownClass(cls):
        """Shutdown the test server cleanly."""
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.server_thread.join(timeout=2.0)
        cls.temp_dir.cleanup()

    def _get(self, path):
        """Helper to send a GET request and return (status, content_type, body_str)."""
        url = f"{self.base_url}{path}"
        req = urllib.request.Request(url)
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8")
                return status, content_type, body
        except urllib.error.HTTPError as e:
            with e:
                body = e.read().decode("utf-8")
                return e.code, e.headers.get("Content-Type", ""), body

    def _post_json(self, path, payload):
        """Helper to send a POST request with JSON and return (status, content_type, body_str)."""
        url = f"{self.base_url}{path}"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as resp:
                status = resp.status
                content_type = resp.headers.get("Content-Type", "")
                body = resp.read().decode("utf-8")
                return status, content_type, body
        except urllib.error.HTTPError as e:
            with e:
                body = e.read().decode("utf-8")
                return e.code, e.headers.get("Content-Type", ""), body

    def test_dashboard_index_html(self):
        """GET / should serve the single-page HTML dashboard."""
        status, ctype, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("text/html", ctype)
        self.assertIn("Accessible Campus Navigator", body)
        self.assertIn("JAIN Global Campus", body)

    def test_campus_data_endpoint(self):
        """GET /api/campus should return valid campus locations and connections."""
        status, ctype, body = self._get("/api/campus")
        self.assertEqual(status, 200)
        self.assertIn("application/json", ctype)
        data = json.loads(body)
        self.assertIn("locations", data)
        self.assertIn("connections", data)
        self.assertEqual(len(data["locations"]), 15)
        self.assertEqual(len(data["connections"]), 25)

    def test_route_dijkstra_endpoint(self):
        """GET /api/route should compute a valid route between campus facilities."""
        status, _, body = self._get("/api/route?start=main_entrance&goal=fet&mode=standard&algo=dijkstra")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["success"])
        self.assertEqual(data["primary"]["path"][0], "main_entrance")
        self.assertEqual(data["primary"]["path"][-1], "fet")
        self.assertGreater(data["primary"]["total_distance"], 0)
        self.assertIn("steps", data["primary"])

    def test_route_comparison_endpoint(self):
        """GET /api/route with algo=compare should return both Dijkstra and BFS solutions."""
        status, _, body = self._get("/api/route?start=main_entrance&goal=library&mode=standard&algo=compare")
        self.assertEqual(status, 200)
        data = json.loads(body)
        self.assertTrue(data["success"])
        self.assertIn("comparison", data)
        self.assertIsNotNone(data["comparison"])
        self.assertIn("dijkstra", data["comparison"])
        self.assertIn("bfs", data["comparison"])

    def test_route_missing_parameters_returns_400(self):
        """GET /api/route missing required start or goal should return HTTP 400."""
        status, _, body = self._get("/api/route?start=main_entrance")
        self.assertEqual(status, 400)
        data = json.loads(body)
        self.assertFalse(data["success"])

    def test_obstacles_reporting_and_resolving_cycle(self):
        """POST /api/obstacles and POST /api/obstacles/resolve lifecycle."""
        # 1. Initially no active obstacles
        status, _, body = self._get("/api/obstacles")
        self.assertEqual(status, 200)
        init_data = json.loads(body)
        self.assertEqual(len(init_data["active_obstacles"]), 0)

        # 2. Report a new obstacle
        payload = {
            "source": "main_entrance",
            "destination": "fet_block",
            "obstacle_type": "ramp_maintenance",
            "description": "Wheelchair ramp repair in progress",
            "reported_by": "Test Suite"
        }
        status, _, body = self._post_json("/api/obstacles", payload)
        self.assertEqual(status, 201)
        created = json.loads(body)
        obs_id = created["id"]
        self.assertEqual(created["status"], "active")

        # 3. Active obstacles list now has 1
        status, _, body = self._get("/api/obstacles")
        self.assertEqual(status, 200)
        active_data = json.loads(body)
        self.assertEqual(len(active_data["active_obstacles"]), 1)
        self.assertEqual(active_data["active_obstacles"][0]["id"], obs_id)

        # 4. Resolve the obstacle
        status, _, body = self._post_json("/api/obstacles/resolve", {"id": obs_id})
        self.assertEqual(status, 200)
        resolve_data = json.loads(body)
        self.assertTrue(resolve_data["success"])

        # 5. Active obstacles is now 0
        status, _, body = self._get("/api/obstacles")
        self.assertEqual(status, 200)
        final_data = json.loads(body)
        self.assertEqual(len(final_data["active_obstacles"]), 0)

    def test_campus_report_endpoint(self):
        """GET /api/report should return the plain text campus data audit report."""
        status, ctype, body = self._get("/api/report")
        self.assertEqual(status, 200)
        self.assertIn("text/plain", ctype)
        self.assertIn("JAIN GLOBAL CAMPUS", body)
        self.assertIn("ACCESSIBILITY DATA REPORT", body)

    def test_nonexistent_endpoint_returns_404(self):
        """Requesting an invalid path should return HTTP 404."""
        status, _, _ = self._get("/api/nonexistent")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
