"""
test_algorithms.py — Unit Tests for BFS and Dijkstra's Pathfinding
===================================================================
Tests correctness of BFS (fewest hops) and Dijkstra (shortest distance),
including edge cases like disconnected graphs, identical start/goal,
and real campus navigation scenarios.
"""

import unittest
from core.graph import CampusGraph
from core.algorithms import bfs_shortest_path, dijkstra_shortest_path
from core.accessibility import AccessibilityMode
from services.data_manager import build_campus_graph


class TestAlgorithms(unittest.TestCase):
    """Test suite comparing BFS and Dijkstra algorithms on controlled graphs."""

    def setUp(self):
        """Build a controlled test graph with two distinct paths:

        Path 1: A -> B (1 hop, distance 200m)
        Path 2: A -> C -> D -> B (3 hops, distances 30m + 30m + 30m = 90m)

        BFS should select Path 1 (fewest hops: 1 hop).
        Dijkstra should select Path 2 (shortest weighted distance: 90m).
        """
        self.toy_graph = CampusGraph()
        for node in ["A", "B", "C", "D", "Isolated"]:
            self.toy_graph.add_location({"id": node, "name": f"Node {node}"})

        # Path 1: 1 hop, long distance
        self.toy_graph.add_edge("A", "B", 200.0, has_stairs=False, has_ramp=True)

        # Path 2: 3 hops, short total distance
        self.toy_graph.add_edge("A", "C", 30.0, has_stairs=False, has_ramp=True)
        self.toy_graph.add_edge("C", "D", 30.0, has_stairs=False, has_ramp=True)
        self.toy_graph.add_edge("D", "B", 30.0, has_stairs=False, has_ramp=True)

    def test_bfs_selects_fewest_hops(self):
        """BFS must choose the 1-hop path (A -> B) even though it is longer (200m)."""
        result = bfs_shortest_path(self.toy_graph, "A", "B")
        self.assertTrue(result["success"])
        self.assertEqual(result["path"], ["A", "B"])
        self.assertEqual(result["hop_count"], 1)
        self.assertEqual(result["total_distance"], 200.0)

    def test_dijkstra_selects_shortest_distance(self):
        """Dijkstra must choose the 90m path (A -> C -> D -> B) over the 200m direct path."""
        result = dijkstra_shortest_path(self.toy_graph, "A", "B")
        self.assertTrue(result["success"])
        self.assertEqual(result["path"], ["A", "C", "D", "B"])
        self.assertEqual(result["total_distance"], 90.0)
        self.assertEqual(len(result["steps"]), 3)
        self.assertGreater(result["estimated_time"], 0)

    def test_same_start_and_destination(self):
        """Searching from a node to itself should succeed immediately with 0 distance."""
        bfs_res = bfs_shortest_path(self.toy_graph, "A", "A")
        self.assertTrue(bfs_res["success"])
        self.assertEqual(bfs_res["path"], ["A"])
        self.assertEqual(bfs_res["total_distance"], 0.0)

        dijkstra_res = dijkstra_shortest_path(self.toy_graph, "A", "A")
        self.assertTrue(dijkstra_res["success"])
        self.assertEqual(dijkstra_res["path"], ["A"])
        self.assertEqual(dijkstra_res["total_distance"], 0.0)

    def test_disconnected_node_returns_failure(self):
        """When destination is unreachable, algorithms must report success=False."""
        bfs_res = bfs_shortest_path(self.toy_graph, "A", "Isolated")
        self.assertFalse(bfs_res["success"])
        self.assertEqual(bfs_res["path"], [])

        dijkstra_res = dijkstra_shortest_path(self.toy_graph, "A", "Isolated")
        self.assertFalse(dijkstra_res["success"])
        self.assertEqual(dijkstra_res["path"], [])

    def test_invalid_node_id_handling(self):
        """Non-existent start or goal IDs must return a clean error without crashing."""
        bfs_res = bfs_shortest_path(self.toy_graph, "NonExistent", "B")
        self.assertFalse(bfs_res["success"])

        dijkstra_res = dijkstra_shortest_path(self.toy_graph, "A", "NonExistent")
        self.assertFalse(dijkstra_res["success"])

    def test_real_jain_campus_routing(self):
        """Test routing on the actual JAIN Global Campus graph."""
        campus_graph, _ = build_campus_graph()

        # Route from Main Entrance to Library
        result = dijkstra_shortest_path(campus_graph, "main_entrance", "library")
        self.assertTrue(result["success"])
        self.assertEqual(result["path"][0], "main_entrance")
        self.assertEqual(result["path"][-1], "library")
        self.assertGreater(result["total_distance"], 0)

        # Route from Hostel to Sports Complex
        result_sports = dijkstra_shortest_path(campus_graph, "hostel", "sports")
        self.assertTrue(result_sports["success"])
        self.assertEqual(result_sports["path"], ["hostel", "sports"])
        self.assertEqual(result_sports["total_distance"], 210.0)


if __name__ == "__main__":
    unittest.main()
