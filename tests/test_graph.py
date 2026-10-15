"""
test_graph.py — Unit Tests for CampusGraph Data Structure
==========================================================
Verifies graph initialization, node/edge registration,
error handling, and loading from JAIN campus data.
"""

import unittest
from core.graph import CampusGraph
from services.data_manager import build_campus_graph


class TestCampusGraph(unittest.TestCase):
    """Test suite for the CampusGraph class."""

    def setUp(self):
        """Create a fresh graph instance before each test."""
        self.graph = CampusGraph()

    def test_empty_graph(self):
        """A new graph should have 0 nodes and 0 edges."""
        self.assertEqual(self.graph.node_count, 0)
        self.assertEqual(self.graph.edge_count, 0)
        self.assertEqual(self.graph.get_all_locations(), {})

    def test_add_location(self):
        """Adding a location should store metadata and create adjacency entry."""
        loc = {
            "id": "gate",
            "name": "Main Gate",
            "category": "entrance",
            "has_ramp": True,
        }
        self.graph.add_location(loc)
        self.assertEqual(self.graph.node_count, 1)
        self.assertTrue(self.graph.has_location("gate"))
        self.assertEqual(self.graph.get_location("gate")["name"], "Main Gate")
        self.assertEqual(self.graph.get_neighbors("gate"), [])

    def test_add_location_missing_id(self):
        """Adding a location without an 'id' must raise ValueError."""
        with self.assertRaises(ValueError):
            self.graph.add_location({"name": "No ID"})

    def test_add_edge_bidirectional(self):
        """Bidirectional edge should be present in both nodes' adjacency lists."""
        self.graph.add_location({"id": "A", "name": "Node A"})
        self.graph.add_location({"id": "B", "name": "Node B"})

        self.graph.add_edge("A", "B", 100, has_ramp=True, has_stairs=False)

        self.assertEqual(self.graph.edge_count, 1)
        self.assertTrue(self.graph.has_edge("A", "B"))
        self.assertTrue(self.graph.has_edge("B", "A"))

        edge_ab = self.graph.get_edge("A", "B")
        self.assertIsNotNone(edge_ab)
        self.assertEqual(edge_ab["distance_meters"], 100.0)
        self.assertTrue(edge_ab["has_ramp"])

        edge_ba = self.graph.get_edge("B", "A")
        self.assertIsNotNone(edge_ba)
        self.assertEqual(edge_ba["target"], "A")

    def test_add_edge_unknown_node_raises_keyerror(self):
        """Adding an edge with an unregistered node must raise KeyError."""
        self.graph.add_location({"id": "A", "name": "Node A"})
        with self.assertRaises(KeyError):
            self.graph.add_edge("A", "GhostNode", 50)
        with self.assertRaises(KeyError):
            self.graph.add_edge("GhostNode", "A", 50)

    def test_add_edge_invalid_distance(self):
        """Adding an edge with distance <= 0 must raise ValueError."""
        self.graph.add_location({"id": "A", "name": "Node A"})
        self.graph.add_location({"id": "B", "name": "Node B"})
        with self.assertRaises(ValueError):
            self.graph.add_edge("A", "B", 0)
        with self.assertRaises(ValueError):
            self.graph.add_edge("A", "B", -10)

    def test_load_real_jain_campus_data(self):
        """Test building the full graph from campus_data.json."""
        graph, metadata = build_campus_graph()
        self.assertEqual(graph.node_count, 15)
        self.assertEqual(graph.edge_count, 25)
        self.assertIn("JAIN", metadata["campus_name"])
        self.assertTrue(graph.has_location("main_entrance"))
        self.assertTrue(graph.has_location("fet"))
        self.assertTrue(graph.has_location("library"))


if __name__ == "__main__":
    unittest.main()
