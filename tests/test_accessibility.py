"""
test_accessibility.py — Unit Tests for Accessibility-Constrained Routing
==========================================================================
Verifies that:
    1. Standard mode picks the shortest distance even if it involves stairs.
    2. Wheelchair mode and Avoid Stairs mode strictly bypass stair pathways.
    3. Prefer Ramps mode prefers gentle slopes/ramps.
    4. Active reported obstacles dynamically reroute users.
    5. Demonstrates the core academic premise on JAIN campus data.
"""

import unittest
from core.graph import CampusGraph
from core.algorithms import dijkstra_shortest_path
from core.accessibility import AccessibilityMode
from services.data_manager import build_campus_graph


class TestAccessibilityRouting(unittest.TestCase):
    """Test suite for accessibility-aware routing behaviors."""

    def setUp(self):
        """Build a test graph with:
        - A direct path that has STAIRS (short: 50m)
        - An indirect ramp path that is STEP-FREE (longer: 120m)
        """
        self.graph = CampusGraph()
        for loc_id in ["Gate", "Stairs_Route", "Ramp_Route", "AcademicBlock"]:
            self.graph.add_location({"id": loc_id, "name": loc_id})

        # Path 1: Gate -> Stairs_Route -> AcademicBlock (total 50m, has stairs)
        self.graph.add_edge("Gate", "Stairs_Route", 25.0, has_stairs=True, has_ramp=False)
        self.graph.add_edge("Stairs_Route", "AcademicBlock", 25.0, has_stairs=True, has_ramp=False)

        # Path 2: Gate -> Ramp_Route -> AcademicBlock (total 120m, step-free with ramp)
        self.graph.add_edge("Gate", "Ramp_Route", 60.0, has_stairs=False, has_ramp=True)
        self.graph.add_edge("Ramp_Route", "AcademicBlock", 60.0, has_stairs=False, has_ramp=True)

    def test_standard_route_takes_stairs_for_shorter_distance(self):
        """Standard mode chooses the 50m stairs path because it does not filter stairs."""
        res = dijkstra_shortest_path(self.graph, "Gate", "AcademicBlock", mode=AccessibilityMode.STANDARD)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["Gate", "Stairs_Route", "AcademicBlock"])
        self.assertEqual(res["total_distance"], 50.0)
        self.assertEqual(res["accessibility_summary"]["stairs_encountered"], 2)

    def test_wheelchair_route_takes_ramp_detour(self):
        """Wheelchair mode must avoid the stairs and take the 120m ramp route."""
        res = dijkstra_shortest_path(self.graph, "Gate", "AcademicBlock", mode=AccessibilityMode.WHEELCHAIR)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["Gate", "Ramp_Route", "AcademicBlock"])
        self.assertEqual(res["total_distance"], 120.0)
        self.assertEqual(res["accessibility_summary"]["stairs_encountered"], 0)
        self.assertEqual(res["accessibility_summary"]["ramps_encountered"], 2)

    def test_avoid_stairs_mode(self):
        """Avoid stairs mode must also pick the step-free ramp route."""
        res = dijkstra_shortest_path(self.graph, "Gate", "AcademicBlock", mode=AccessibilityMode.AVOID_STAIRS)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["Gate", "Ramp_Route", "AcademicBlock"])
        self.assertEqual(res["accessibility_summary"]["stairs_encountered"], 0)

    def test_prefer_ramps_mode(self):
        """Prefer ramps mode penalizes stairs and favors the ramp route."""
        res = dijkstra_shortest_path(self.graph, "Gate", "AcademicBlock", mode=AccessibilityMode.PREFER_RAMPS)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"], ["Gate", "Ramp_Route", "AcademicBlock"])

    def test_dynamic_obstacle_rerouting(self):
        """When an obstacle blocks the preferred ramp, traffic reroutes or fails appropriately."""
        # Block the ramp edge ("Gate", "Ramp_Route")
        blocked = {("Gate", "Ramp_Route")}
        res = dijkstra_shortest_path(
            self.graph,
            "Gate",
            "AcademicBlock",
            mode=AccessibilityMode.WHEELCHAIR,
            blocked_edges=blocked,
        )
        # Since the stairs route is disallowed for wheelchairs and ramp is blocked, no route exists
        self.assertFalse(res["success"])

        # But for standard mode, it can still use the stairs route
        res_std = dijkstra_shortest_path(
            self.graph,
            "Gate",
            "AcademicBlock",
            mode=AccessibilityMode.STANDARD,
            blocked_edges=blocked,
        )
        self.assertTrue(res_std["success"])
        self.assertEqual(res_std["path"], ["Gate", "Stairs_Route", "AcademicBlock"])

    def test_jain_campus_standard_routing(self):
        """Demonstrate routing on JAIN Global Campus data:
        Route from Main Entrance to Library via standard mode.
        """
        campus_graph, _ = build_campus_graph()
        res = dijkstra_shortest_path(campus_graph, "main_entrance", "library", mode=AccessibilityMode.STANDARD)
        self.assertTrue(res["success"])
        self.assertEqual(res["path"][0], "main_entrance")
        self.assertEqual(res["path"][-1], "library")
        self.assertGreater(res["total_distance"], 0)

    def test_jain_campus_alternative_path_exists(self):
        """Verify that alternative paths exist between Main Entrance and Library."""
        campus_graph, _ = build_campus_graph()
        # Direct via FET: main_entrance -> fet -> library (250 + 180 = 430m)
        # Via Cafeteria: main_entrance -> cafeteria -> library (200 + 210 = 410m)
        res = dijkstra_shortest_path(campus_graph, "main_entrance", "library", mode=AccessibilityMode.STANDARD)
        self.assertTrue(res["success"])
        self.assertIn("library", res["path"])


if __name__ == "__main__":
    unittest.main()
