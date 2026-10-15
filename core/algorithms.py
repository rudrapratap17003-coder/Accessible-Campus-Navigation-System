"""
algorithms.py — Graph Search & Pathfinding Algorithms
======================================================
Implements:
    1. Breadth-First Search (BFS)
       - Finds the route with the fewest number of turns / hops (unweighted).
       - Implemented using collections.deque.
    2. Dijkstra's Algorithm
       - Finds the optimal weighted shortest path taking distances and
         accessibility preferences into account.
       - Implemented using a min-heap priority queue via heapq.

Learning Objectives:
    - Queue-based graph traversal vs. Priority Queue shortest-path finding.
    - Path reconstruction from predecessor parent maps.
    - Integration of domain-specific constraints (accessibility filtering).
    - Clear exception handling and corner cases (disconnection, self-loop).
"""

from collections import deque
import heapq

from core.accessibility import (
    AccessibilityMode,
    is_edge_allowed,
    calculate_edge_weight,
    estimate_travel_time,
)


def bfs_shortest_path(graph, start_id, goal_id, mode=AccessibilityMode.STANDARD, blocked_edges=None):
    """Find the path with the fewest hops using Breadth-First Search.

    Args:
        graph (CampusGraph): The campus graph instance.
        start_id (str): Source location ID.
        goal_id (str): Target location ID.
        mode (str): Accessibility mode filter.
        blocked_edges (set or None): Set of blocked edge tuples.

    Returns:
        dict: Result dictionary containing:
            - success (bool)
            - path (list of str)
            - total_distance (float)
            - hop_count (int)
            - edges (list of dict)
            - message (str)
    """
    # 1. Input validation
    if not graph.has_location(start_id):
        return {
            "success": False,
            "path": [],
            "total_distance": 0.0,
            "hop_count": 0,
            "edges": [],
            "message": f"Start location '{start_id}' does not exist.",
            "algorithm": "BFS (Fewest Hops)",
        }

    if not graph.has_location(goal_id):
        return {
            "success": False,
            "path": [],
            "total_distance": 0.0,
            "hop_count": 0,
            "edges": [],
            "message": f"Goal location '{goal_id}' does not exist.",
            "algorithm": "BFS (Fewest Hops)",
        }

    # Trivial case: already at destination
    if start_id == goal_id:
        return {
            "success": True,
            "path": [start_id],
            "total_distance": 0.0,
            "hop_count": 0,
            "edges": [],
            "message": "Start and destination are the same location.",
            "algorithm": "BFS (Fewest Hops)",
        }

    # 2. Queue for BFS: holds (current_node, [path_nodes], [edges_traversed])
    queue = deque([(start_id, [start_id], [])])
    visited = {start_id}

    while queue:
        current_node, path, edges_traversed = queue.popleft()

        # Check neighbors
        for edge in graph.get_neighbors(current_node):
            neighbor = edge["target"]

            # Filter edge based on accessibility mode and active obstacles
            if not is_edge_allowed(edge, mode, blocked_edges):
                continue

            if neighbor == goal_id:
                final_path = path + [neighbor]
                final_edges = edges_traversed + [edge]
                total_dist = sum(e["distance_meters"] for e in final_edges)
                return {
                    "success": True,
                    "path": final_path,
                    "total_distance": round(total_dist, 1),
                    "hop_count": len(final_edges),
                    "edges": final_edges,
                    "message": f"Route found with {len(final_edges)} hops.",
                    "algorithm": "BFS (Fewest Hops)",
                }

            if neighbor not in visited:
                visited.add(neighbor)
                queue.append((neighbor, path + [neighbor], edges_traversed + [edge]))

    # If queue empties without reaching goal
    return {
        "success": False,
        "path": [],
        "total_distance": 0.0,
        "hop_count": 0,
        "edges": [],
        "message": f"No accessible route found between '{start_id}' and '{goal_id}' under {mode} mode.",
        "algorithm": "BFS (Fewest Hops)",
    }


def dijkstra_shortest_path(graph, start_id, goal_id, mode=AccessibilityMode.STANDARD, blocked_edges=None):
    """Find the optimal shortest accessible path using Dijkstra's Algorithm.

    Uses a min-heap priority queue. Edge weights are computed according to the
    selected accessibility mode (e.g. ramp preference discounts, stair penalties).

    Args:
        graph (CampusGraph): The campus graph instance.
        start_id (str): Source location ID.
        goal_id (str): Target location ID.
        mode (str): Accessibility mode filter.
        blocked_edges (set or None): Set of blocked edge tuples.

    Returns:
        dict: Detailed result dictionary containing:
            - success (bool)
            - path (list of str)
            - total_distance (float)
            - estimated_time (float, in minutes)
            - steps (list of dict)
            - accessibility_summary (dict)
            - message (str)
    """
    # 1. Input validation
    if not graph.has_location(start_id):
        return _empty_dijkstra_result(f"Start location '{start_id}' does not exist.")

    if not graph.has_location(goal_id):
        return _empty_dijkstra_result(f"Goal location '{goal_id}' does not exist.")

    if start_id == goal_id:
        loc = graph.get_location(start_id)
        name = loc["name"] if loc else start_id
        return {
            "success": True,
            "path": [start_id],
            "total_distance": 0.0,
            "estimated_time": 0.0,
            "steps": [],
            "accessibility_summary": {"ramps": 0, "stairs": 0, "elevators": 0, "covered": 0},
            "message": f"Already at destination ({name}).",
            "algorithm": "Dijkstra's Algorithm",
            "mode": mode,
        }

    # 2. Priority Queue & bookkeeping
    # distances maps node -> best known algorithmic cost from start
    distances = {node: float("inf") for node in graph.get_all_locations()}
    distances[start_id] = 0.0

    # predecessor maps node -> (parent_node, connecting_edge_dict)
    predecessors = {}

    # Priority queue stores tuples: (current_cost, counter, current_node)
    # Counter prevents comparison between node strings if costs are identical
    counter = 0
    pq = [(0.0, counter, start_id)]

    visited = set()

    while pq:
        curr_cost, _, current_node = heapq.heappop(pq)

        if current_node in visited:
            continue
        visited.add(current_node)

        # Early termination when destination is settled
        if current_node == goal_id:
            break

        # Check all neighboring edges
        for edge in graph.get_neighbors(current_node):
            neighbor = edge["target"]

            if neighbor in visited:
                continue

            # Verify accessibility compatibility
            if not is_edge_allowed(edge, mode, blocked_edges):
                continue

            # Calculate edge cost (accounting for ramps or stair penalties)
            edge_weight = calculate_edge_weight(edge, mode)
            new_cost = curr_cost + edge_weight

            if new_cost < distances[neighbor]:
                distances[neighbor] = new_cost
                predecessors[neighbor] = (current_node, edge)
                counter += 1
                heapq.heappush(pq, (new_cost, counter, neighbor))

    # 3. Path reconstruction
    if goal_id not in predecessors:
        return _empty_dijkstra_result(
            f"No accessible route found between '{start_id}' and '{goal_id}' under {mode} mode.",
            mode=mode,
        )

    path = []
    edges_in_path = []
    curr = goal_id

    while curr in predecessors:
        parent, edge = predecessors[curr]
        path.append(curr)
        edges_in_path.append(edge)
        curr = parent
    path.append(start_id)

    # Reverse to get start-to-goal order
    path.reverse()
    edges_in_path.reverse()

    # 4. Compute metrics and summary
    total_physical_distance = sum(e["distance_meters"] for e in edges_in_path)
    est_time = estimate_travel_time(total_physical_distance, mode)

    # Build human-readable step-by-step instructions
    steps = []
    ramps_count = 0
    stairs_count = 0
    elevators_count = 0
    covered_count = 0

    for idx, edge in enumerate(edges_in_path, 1):
        u_info = graph.get_location(edge["from"])
        v_info = graph.get_location(edge["target"])
        u_name = u_info.get("short_name", u_info.get("name", edge["from"])) if u_info else edge["from"]
        v_name = v_info.get("short_name", v_info.get("name", edge["target"])) if v_info else edge["target"]

        features = []
        if edge.get("has_ramp"):
            features.append("Ramp")
            ramps_count += 1
        if edge.get("has_stairs"):
            features.append("Stairs")
            stairs_count += 1
        if edge.get("has_elevator"):
            features.append("Elevator")
            elevators_count += 1
        if edge.get("is_covered"):
            features.append("Covered walkway")
            covered_count += 1

        feature_str = f" [{', '.join(features)}]" if features else ""

        step_desc = (
            f"Step {idx}: Walk from {u_name} to {v_name} "
            f"({int(edge['distance_meters'])} m, {edge.get('surface', 'paved')}){feature_str}"
        )
        steps.append({
            "step_number": idx,
            "from_id": edge["from"],
            "to_id": edge["target"],
            "from_name": u_name,
            "to_name": v_name,
            "distance_meters": edge["distance_meters"],
            "instruction": step_desc,
            "features": features,
        })

    summary = {
        "ramps_encountered": ramps_count,
        "stairs_encountered": stairs_count,
        "elevators_encountered": elevators_count,
        "covered_segments": covered_count,
        "total_segments": len(edges_in_path),
    }

    return {
        "success": True,
        "path": path,
        "total_distance": round(total_physical_distance, 1),
        "estimated_time": est_time,
        "steps": steps,
        "accessibility_summary": summary,
        "message": f"Found accessible route ({round(total_physical_distance, 1)} m, ~{est_time} min).",
        "algorithm": "Dijkstra's Algorithm",
        "mode": mode,
    }


def _empty_dijkstra_result(message, mode=AccessibilityMode.STANDARD):
    """Helper to return an unsuccessful Dijkstra query result."""
    return {
        "success": False,
        "path": [],
        "total_distance": 0.0,
        "estimated_time": 0.0,
        "steps": [],
        "accessibility_summary": {
            "ramps_encountered": 0,
            "stairs_encountered": 0,
            "elevators_encountered": 0,
            "covered_segments": 0,
            "total_segments": 0,
        },
        "message": message,
        "algorithm": "Dijkstra's Algorithm",
        "mode": mode,
    }
