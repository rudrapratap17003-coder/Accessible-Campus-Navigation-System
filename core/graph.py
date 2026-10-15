"""
graph.py — Campus Graph Data Structure
========================================
Represents the campus as a weighted, undirected graph using an adjacency list.

Each node represents a campus facility, building, or junction point.
Each edge represents a walkway, road, or corridor with distance and accessibility attributes.

Learning Objectives Demonstrated:
    - Object-Oriented Programming (Classes, Methods, Encapsulation)
    - Graph Data Structure using Adjacency List (Dictionaries & Lists)
    - Clean API design for graph traversal
"""


class CampusGraph:
    """Weighted undirected graph representing the campus map and walkway network."""

    def __init__(self):
        """Initialize an empty campus graph."""
        # adjacency_list maps: location_id -> list of edge dictionaries
        # Each edge dictionary: {"target": neighbor_id, "distance_meters": int, ...attributes}
        self.adjacency_list = {}

        # location_info maps: location_id -> full location metadata dictionary
        self.location_info = {}

    def add_location(self, location_data):
        """Add a location (node) to the campus graph.

        Args:
            location_data (dict): Dictionary containing location details.
                                  Must include an 'id' field.

        Raises:
            ValueError: If 'id' is missing from location_data.
        """
        if not isinstance(location_data, dict) or "id" not in location_data:
            raise ValueError("Location data must be a dictionary with an 'id' field.")

        loc_id = location_data["id"]
        self.location_info[loc_id] = dict(location_data)

        # Initialize empty adjacency list for this node if not already present
        if loc_id not in self.adjacency_list:
            self.adjacency_list[loc_id] = []

    def add_edge(self, from_node, to_node, distance_meters, bidirectional=True, **attributes):
        """Add a path (edge) connecting two campus locations.

        Args:
            from_node (str): ID of the starting location.
            to_node (str): ID of the destination location.
            distance_meters (float/int): Estimated walking distance in meters.
            bidirectional (bool): If True, path can be traversed both ways (default).
            **attributes: Additional attributes (e.g. has_stairs, has_ramp, surface).

        Raises:
            KeyError: If either from_node or to_node has not been added to the graph.
            ValueError: If distance_meters is non-positive.
        """
        if from_node not in self.location_info:
            raise KeyError(f"Starting location '{from_node}' does not exist in graph.")
        if to_node not in self.location_info:
            raise KeyError(f"Destination location '{to_node}' does not exist in graph.")
        if distance_meters <= 0:
            raise ValueError("Distance must be a positive number.")

        # Construct edge payload for forward direction
        forward_edge = {
            "from": from_node,
            "target": to_node,
            "distance_meters": float(distance_meters),
            **attributes
        }
        self.adjacency_list[from_node].append(forward_edge)

        # If bidirectional, add reverse edge
        if bidirectional:
            reverse_edge = {
                "from": to_node,
                "target": from_node,
                "distance_meters": float(distance_meters),
                **attributes
            }
            self.adjacency_list[to_node].append(reverse_edge)

    def get_location(self, location_id):
        """Retrieve metadata for a specific location.

        Args:
            location_id (str): The ID of the location.

        Returns:
            dict or None: Location dictionary if found, None otherwise.
        """
        return self.location_info.get(location_id)

    def get_all_locations(self):
        """Return a dictionary of all registered locations."""
        return self.location_info

    def get_neighbors(self, location_id):
        """Get all outgoing edges from a given location.

        Args:
            location_id (str): The ID of the location.

        Returns:
            list: List of edge dictionaries connecting to neighbors.
        """
        return self.adjacency_list.get(location_id, [])

    def get_edge(self, u, v):
        """Find the edge data between two directly connected locations u and v.

        Args:
            u (str): Source node ID.
            v (str): Destination node ID.

        Returns:
            dict or None: Edge dictionary if connected, None otherwise.
        """
        for edge in self.get_neighbors(u):
            if edge["target"] == v:
                return edge
        return None

    def has_location(self, location_id):
        """Check if a location exists in the graph."""
        return location_id in self.location_info

    def has_edge(self, u, v):
        """Check if a direct edge exists between u and v."""
        return self.get_edge(u, v) is not None

    @property
    def node_count(self):
        """Total number of locations in the graph."""
        return len(self.location_info)

    @property
    def edge_count(self):
        """Total number of unique undirected edges in the graph."""
        seen = set()
        count = 0
        for u, edges in self.adjacency_list.items():
            for edge in edges:
                v = edge["target"]
                pair = tuple(sorted([u, v]))
                if pair not in seen:
                    seen.add(pair)
                    count += 1
        return count

    def clear(self):
        """Clear all locations and edges from the graph."""
        self.adjacency_list.clear()
        self.location_info.clear()

    def __repr__(self):
        return f"<CampusGraph: {self.node_count} locations, {self.edge_count} edges>"
