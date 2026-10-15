"""
test_obstacle_manager.py — Unit Tests for Accessibility Obstacle Management
=============================================================================
Tests creating, loading, filtering active obstacles, computing blocked edges,
and resolving obstacles using isolated temporary files.
"""

import unittest
import tempfile
import json
from pathlib import Path

from services.obstacle_manager import ObstacleManager


class TestObstacleManager(unittest.TestCase):
    """Test suite for ObstacleManager service."""

    def setUp(self):
        """Create a temporary directory and file for isolated testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_file = Path(self.temp_dir.name) / "test_obstacles.json"
        self.mgr = ObstacleManager(file_path=self.temp_file)

    def tearDown(self):
        """Clean up temporary test directory."""
        self.temp_dir.cleanup()

    def test_initial_empty_file_creation(self):
        """When initialized with a new path, an empty obstacles file should be created."""
        self.assertTrue(self.temp_file.is_file())
        self.assertEqual(self.mgr.load_all_obstacles(), [])
        self.assertEqual(self.mgr.get_active_obstacles(), [])
        self.assertEqual(self.mgr.get_blocked_edges(), set())

    def test_report_obstacle(self):
        """Reporting an obstacle should record all fields and persist to disk."""
        obs = self.mgr.report_obstacle(
            source="main_entrance",
            destination="fet_block",
            obstacle_type="ramp_broken",
            description="Wheelchair ramp under maintenance near FET",
            reported_by="Campus Marshal"
        )
        self.assertTrue(obs["id"].startswith("obs_1_"))
        self.assertEqual(obs["source"], "main_entrance")
        self.assertEqual(obs["destination"], "fet_block")
        self.assertEqual(obs["obstacle_type"], "ramp_broken")
        self.assertEqual(obs["status"], "active")

        # Verify persistence on disk
        persisted = self.mgr.load_all_obstacles()
        self.assertEqual(len(persisted), 1)
        self.assertEqual(persisted[0]["id"], obs["id"])

    def test_get_blocked_edges_bidirectional(self):
        """Active obstacles should generate bidirectional blocked edges for routing."""
        self.mgr.report_obstacle("library", "auditorium", "construction", "Pavement repaving")
        blocked = self.mgr.get_blocked_edges()
        self.assertIn(("library", "auditorium"), blocked)
        self.assertIn(("auditorium", "library"), blocked)

    def test_resolve_obstacle(self):
        """Resolving an obstacle should change status to 'resolved' and clear blocked edge."""
        obs = self.mgr.report_obstacle("library", "auditorium", "puddle", "Water leak")
        obs_id = obs["id"]

        self.assertEqual(len(self.mgr.get_active_obstacles()), 1)
        self.assertEqual(len(self.mgr.get_blocked_edges()), 2)

        resolved = self.mgr.resolve_obstacle(obs_id)
        self.assertTrue(resolved)
        self.assertEqual(len(self.mgr.get_active_obstacles()), 0)
        self.assertEqual(len(self.mgr.get_blocked_edges()), 0)

        # But all obstacles still contains the historical record
        all_obs = self.mgr.load_all_obstacles()
        self.assertEqual(len(all_obs), 1)
        self.assertEqual(all_obs[0]["status"], "resolved")
        self.assertIn("resolved_at", all_obs[0])

    def test_resolve_nonexistent_obstacle(self):
        """Attempting to resolve a non-existent obstacle should return False."""
        self.assertFalse(self.mgr.resolve_obstacle("non_existent_id"))

    def test_clear_all_obstacles(self):
        """Clearing obstacles resets the file to empty."""
        self.mgr.report_obstacle("hostel", "cafeteria", "debris", "Tree branch fallen")
        self.assertEqual(len(self.mgr.load_all_obstacles()), 1)
        self.mgr.clear_all_obstacles()
        self.assertEqual(len(self.mgr.load_all_obstacles()), 0)


if __name__ == "__main__":
    unittest.main()
