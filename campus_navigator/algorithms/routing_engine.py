"""Deterministic routing algorithms and explainability engine.

Implements:
1. find_route(start, destination, profile, graph) - Weighted Dijkstra (distance or time)
2. find_bfs_route(start, destination, profile, graph) - Unweighted BFS (minimum edge hops)
3. find_alternative_routes(start, destination, profile, graph) - Ranked alternative paths
4. recalculate_route(start, destination, profile, graph, new_obstacle) - Dynamic re-routing
5. explain_route(route_result, profile) - Comprehensive explainability audit

Key Theoretical Distinction:
- BFS (Breadth-First Search) minimizes the NUMBER OF EDGES (hops) in an unweighted graph.
  It does NOT account for edge distance (meters) or traversal time (seconds). Thus, a 2-hop
  path of 400 meters will be chosen by BFS over a 3-hop path of 90 meters.
- Dijkstra's algorithm computes the minimum non-negative cumulative weight (distance or time),
  finding optimal physical traversal efficiency under mandatory constraints.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple, Set
import networkx as nx
from collections import deque
from campus_navigator.models.core_models import (
    AccessibilityProfile,
    LocationNode,
    PathwayEdge,
    VerificationStatus,
)
from campus_navigator.algorithms.graph_builder import CampusGraph


@dataclass
class RouteStep:
    node_id: str
    node_name: str
    floor: Optional[int]
    is_indoor: bool
    transition_instruction: str = ""
    edge_taken: Optional[PathwayEdge] = None
    distance_segment_m: float = 0.0
    time_segment_sec: float = 0.0


@dataclass
class RouteResult:
    start_id: str
    destination_id: str
    algorithm: str
    success: bool
    path_nodes: List[str] = field(default_factory=list)
    steps: List[RouteStep] = field(default_factory=list)
    total_distance_m: float = 0.0
    estimated_travel_time_sec: float = 0.0
    floors_visited: List[int] = field(default_factory=list)
    floor_transitions_count: int = 0
    stairs_count: int = 0
    elevators_used_count: int = 0
    ramps_used_count: int = 0
    step_free_certified: bool = True
    all_segments_verified: bool = False
    provisional_segments_count: int = 0
    demonstration_segments_count: int = 0
    active_obstacles_encountered: List[str] = field(default_factory=list)
    unknown_attributes_flagged: List[str] = field(default_factory=list)
    rejection_explanations: List[str] = field(default_factory=list)
    failure_reason: str = ""
    route_eligibility: str = "ELIGIBLE"


class RoutingEngine:
    def __init__(self, campus_graph: Optional[CampusGraph] = None):
        self.cg = campus_graph or CampusGraph()

    def find_route(
        self,
        start_id: str,
        destination_id: str,
        profile: AccessibilityProfile,
        blocked_ids: Optional[Set[str]] = None
    ) -> RouteResult:
        """Find optimal route using Dijkstra based on profile optimization preference (distance vs time).
        Enforces hard constraints (stairs, step-free, obstacles, strictness) prior to path minimization.
        """
        if start_id not in self.cg.nodes:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="Dijkstra",
                success=False,
                failure_reason=f"Start location '{start_id}' does not exist in campus database.",
                route_eligibility="INELIGIBLE"
            )
        if destination_id not in self.cg.nodes:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="Dijkstra",
                success=False,
                failure_reason=f"Destination location '{destination_id}' does not exist in campus database.",
                route_eligibility="INELIGIBLE"
            )

        filtered_graph, rejections = self.cg.get_filtered_subgraph(profile, blocked_ids)

        if start_id not in filtered_graph:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="Dijkstra",
                success=False,
                rejection_explanations=rejections,
                failure_reason=f"Start point '{self.cg.nodes[start_id].name}' is currently unavailable due to active obstacles or mobility constraints.",
                route_eligibility="INELIGIBLE"
            )

        if destination_id not in filtered_graph:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="Dijkstra",
                success=False,
                rejection_explanations=rejections,
                failure_reason=f"Destination '{self.cg.nodes[destination_id].name}' cannot be reached under the constraints of '{profile.name}'.",
                route_eligibility="INELIGIBLE"
            )

        weight_field = "estimated_time_sec" if profile.optimize_for == "time" else "distance_m"

        try:
            path_nodes = nx.dijkstra_path(
                filtered_graph,
                source=start_id,
                target=destination_id,
                weight=weight_field
            )
            result = self._build_route_result(path_nodes, profile, "Dijkstra (Weighted)")
            result.rejection_explanations = rejections
            return result
        except nx.NetworkXNoPath:
            start_n = self.cg.nodes[start_id]
            dest_n = self.cg.nodes[destination_id]
            is_different_floor = (start_n.floor is not None and dest_n.floor is not None and start_n.floor != dest_n.floor)

            if is_different_floor and not profile.permit_stairs:
                fail_msg = "No verified step-free route to this floor is available in the current building dataset."
            elif profile.strict_mode:
                fail_msg = (
                    f"No path is available under strict verification policy. "
                    f"Potential routes traverse unverified or demonstration pathways that have not yet been surveyed on-site."
                )
            else:
                fail_msg = (
                    f"No path satisfies all mandatory accessibility constraints for '{profile.name}'. "
                    f"All prospective routes either require stairs, traverse blocked pathways, or lack verified elevator/step-free linkages."
                )

            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="Dijkstra",
                success=False,
                rejection_explanations=rejections,
                failure_reason=fail_msg,
                route_eligibility="INELIGIBLE"
            )

    def find_bfs_route(
        self,
        start_id: str,
        destination_id: str,
        profile: AccessibilityProfile,
        blocked_ids: Optional[Set[str]] = None
    ) -> RouteResult:
        """Find route using BFS for unweighted minimum-hop routing (educational / baseline comparison).
        
        NOTE: BFS minimizes the NUMBER OF GRAPH EDGES (hops), NOT distance or travel time.
        In accessibility navigation, Dijkstra with physical edge weights is preferred, but
        BFS is implemented to provide an explainable algorithmic baseline.
        """
        filtered_graph, rejections = self.cg.get_filtered_subgraph(profile, blocked_ids)

        if start_id not in self.cg.nodes or destination_id not in self.cg.nodes:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="BFS (Unweighted)",
                success=False,
                failure_reason="Start or destination does not exist in campus database.",
                route_eligibility="INELIGIBLE"
            )

        if start_id not in filtered_graph or destination_id not in filtered_graph:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="BFS (Unweighted)",
                success=False,
                rejection_explanations=rejections,
                failure_reason="Start or destination inaccessible under current accessibility filters.",
                route_eligibility="INELIGIBLE"
            )

        try:
            # Unweighted shortest path using BFS
            path_nodes = nx.shortest_path(filtered_graph, source=start_id, target=destination_id)
            result = self._build_route_result(path_nodes, profile, "BFS (Minimum Hops)")
            result.rejection_explanations = rejections
            return result
        except nx.NetworkXNoPath:
            return RouteResult(
                start_id=start_id,
                destination_id=destination_id,
                algorithm="BFS (Unweighted)",
                success=False,
                rejection_explanations=rejections,
                failure_reason="No path found using unweighted BFS.",
                route_eligibility="INELIGIBLE"
            )

    def compare_bfs_vs_dijkstra(
        self,
        start_id: str,
        destination_id: str,
        profile: AccessibilityProfile
    ) -> Dict[str, Any]:
        """Educational comparison demonstrating how unweighted BFS and weighted Dijkstra differ."""
        bfs_res = self.find_bfs_route(start_id, destination_id, profile)
        dijkstra_res = self.find_route(start_id, destination_id, profile)

        return {
            "start": self.cg.nodes[start_id].name if start_id in self.cg.nodes else start_id,
            "destination": self.cg.nodes[destination_id].name if destination_id in self.cg.nodes else destination_id,
            "profile": profile.name,
            "bfs": {
                "algorithm": "BFS (Unweighted Breadth-First Search)",
                "hops": len(bfs_res.path_nodes) - 1 if bfs_res.success else 0,
                "distance_m": bfs_res.total_distance_m if bfs_res.success else None,
                "time_sec": bfs_res.estimated_travel_time_sec if bfs_res.success else None,
                "success": bfs_res.success
            },
            "dijkstra": {
                "algorithm": f"Dijkstra (Weighted by {profile.optimize_for})",
                "hops": len(dijkstra_res.path_nodes) - 1 if dijkstra_res.success else 0,
                "distance_m": dijkstra_res.total_distance_m if dijkstra_res.success else None,
                "time_sec": dijkstra_res.estimated_travel_time_sec if dijkstra_res.success else None,
                "success": dijkstra_res.success
            },
            "analysis": (
                "BFS optimizes strictly for minimum edge transitions (hops), whereas Dijkstra minimizes "
                "actual physical travel cost (distance or time). Dijkstra is recommended for physical campus accessibility."
            )
        }

    def find_alternative_routes(
        self,
        start_id: str,
        destination_id: str,
        profile: AccessibilityProfile,
        max_alternatives: int = 3,
        blocked_ids: Optional[Set[str]] = None
    ) -> List[RouteResult]:
        """Find up to k distinct valid alternative routes ranked by the profile objective."""
        filtered_graph, rejections = self.cg.get_filtered_subgraph(profile, blocked_ids)
        if start_id not in filtered_graph or destination_id not in filtered_graph:
            return []

        weight_field = "estimated_time_sec" if profile.optimize_for == "time" else "distance_m"
        results = []

        try:
            generator = nx.shortest_simple_paths(
                filtered_graph,
                source=start_id,
                target=destination_id,
                weight=weight_field
            )
            for i, path in enumerate(generator):
                if i >= max_alternatives:
                    break
                route_res = self._build_route_result(path, profile, f"Route Option #{i+1}")
                route_res.rejection_explanations = rejections
                results.append(route_res)
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            pass

        return results

    def recalculate_route(
        self,
        start_id: str,
        destination_id: str,
        profile: AccessibilityProfile,
        new_blocked_id: str
    ) -> RouteResult:
        """Recalculate route after a newly reported obstacle."""
        blocked_ids = self.cg.obstacle_db.get_blocked_target_ids()
        blocked_ids.add(new_blocked_id)
        return self.find_route(start_id, destination_id, profile, blocked_ids)

    def _build_route_result(
        self,
        path_nodes: List[str],
        profile: AccessibilityProfile,
        algorithm_name: str
    ) -> RouteResult:
        """Assemble full route metrics, inspection data, and textual sequence."""
        steps: List[RouteStep] = []
        total_dist = 0.0
        total_time = 0.0
        floor_transitions = 0
        stairs_count = 0
        elevators_count = 0
        ramps_count = 0
        all_verified = True
        provisional_count = 0
        demonstration_count = 0
        unknowns = []
        floors_visited = set()

        for i, node_id in enumerate(path_nodes):
            node = self.cg.nodes[node_id]
            if node.floor is not None:
                floors_visited.add(node.floor)

            edge = None
            instruction = ""
            seg_dist = 0.0
            seg_time = 0.0

            if i > 0:
                prev_id = path_nodes[i - 1]
                prev_node = self.cg.nodes[prev_id]
                edge = self.cg.get_edge_between(prev_id, node_id)
                if edge:
                    seg_dist = edge.distance_m
                    seg_time = edge.estimated_time_sec
                    total_dist += seg_dist
                    total_time += seg_time

                    if edge.verification == VerificationStatus.PROVISIONAL:
                        all_verified = False
                        provisional_count += 1
                    elif edge.verification == VerificationStatus.DEMONSTRATION:
                        all_verified = False
                        demonstration_count += 1

                    if edge.floor_transition:
                        floor_transitions += 1

                    if edge.has_stairs:
                        stairs_count += 1
                    if edge.is_elevator:
                        elevators_count += 1
                    if edge.has_ramp:
                        ramps_count += 1

                    if edge.surface.value == "UNKNOWN":
                        unknowns.append(f"Surface unknown between {prev_node.name} and {node.name}")
                    if edge.width_cm is None:
                        unknowns.append(f"Pathway width unmeasured between {prev_node.name} and {node.name}")

                    # Compose instruction
                    if edge.is_elevator:
                        instruction = f"Take Elevator from {prev_node.name} to {node.name} (Floor {node.floor})"
                    elif edge.has_stairs:
                        instruction = f"Climb Stairs to {node.name} (Floor {node.floor})"
                    elif edge.has_ramp:
                        instruction = f"Follow accessible Ramp to {node.name}"
                    elif prev_node.is_indoor() != node.is_indoor():
                        instruction = f"Transition threshold between {prev_node.name} and {node.name}"
                    else:
                        instruction = f"Proceed {seg_dist:.1f}m along corridor/pathway to {node.name}"
            else:
                instruction = f"Depart from starting point: {node.name}"

            steps.append(RouteStep(
                node_id=node.id,
                node_name=node.name,
                floor=node.floor,
                is_indoor=node.is_indoor(),
                transition_instruction=instruction,
                edge_taken=edge,
                distance_segment_m=seg_dist,
                time_segment_sec=seg_time
            ))

        is_step_free = (stairs_count == 0)

        # Check for active obstacles in the database that might affect the vicinity
        active_obs = [
            f"{o.obstacle_type.value}: {o.description}"
            for o in self.cg.obstacle_db.get_active_blocking_obstacles()
        ]

        return RouteResult(
            start_id=path_nodes[0],
            destination_id=path_nodes[-1],
            algorithm=algorithm_name,
            success=True,
            path_nodes=path_nodes,
            steps=steps,
            total_distance_m=round(total_dist, 1),
            estimated_travel_time_sec=round(total_time, 1),
            floors_visited=sorted(list(floors_visited)),
            floor_transitions_count=floor_transitions,
            stairs_count=stairs_count,
            elevators_used_count=elevators_count,
            ramps_used_count=ramps_count,
            step_free_certified=is_step_free,
            all_segments_verified=all_verified,
            provisional_segments_count=provisional_count,
            demonstration_segments_count=demonstration_count,
            active_obstacles_encountered=active_obs,
            unknown_attributes_flagged=list(set(unknowns)),
            route_eligibility="ELIGIBLE"
        )

    def explain_route(self, route: RouteResult, profile: AccessibilityProfile) -> Dict[str, Any]:
        """Provides human-readable justifications and audit breakdown for why this route was recommended."""
        if not route.success:
            return {
                "verdict": "ROUTE INELIGIBLE / UNAVAILABLE",
                "summary": route.failure_reason,
                "rejection_log": route.rejection_explanations[:5]
            }

        reasons = []
        if profile.require_step_free:
            reasons.append("Mandatory step-free constraint satisfied: 0 stairs encountered on path.")
        if not profile.permit_stairs:
            reasons.append("All stairwells strictly bypassed in favor of ground ramps and certified elevators.")
        if route.elevators_used_count > 0:
            reasons.append(f"Elevator utilized ({route.elevators_used_count} floor transfer) to connect multi-level layout.")
        if route.ramps_used_count > 0:
            reasons.append(f"Gentle-slope ramp access ({route.ramps_used_count} segments) chosen over stepped entries.")
        if profile.optimize_for == "distance":
            reasons.append(f"Optimized for minimum physical distance ({route.total_distance_m}m).")
        else:
            reasons.append(f"Optimized for minimum travel time ({int(route.estimated_travel_time_sec // 60)}m {int(route.estimated_travel_time_sec % 60)}s).")

        transparency = []
        if route.demonstration_segments_count > 0:
            transparency.append(
                f"{route.demonstration_segments_count} segments utilize the DEMONSTRATION FET FLOOR PLAN (illustrative layout, not official FET blueprints)."
            )
        if route.provisional_segments_count > 0:
            transparency.append(
                f"{route.provisional_segments_count} segments utilize provisional outdoor walkways (awaiting final on-site surveying)."
            )
        if route.unknown_attributes_flagged:
            transparency.append(
                f"{len(route.unknown_attributes_flagged)} attributes (such as surface friction or precise doorway width) are recorded as UNKNOWN and not assumed."
            )

        return {
            "verdict": "RECOMMENDED ACCESSIBLE ROUTE",
            "algorithm": route.algorithm,
            "accessibility_profile": profile.name,
            "total_distance": f"{route.total_distance_m} meters",
            "estimated_time": f"{int(route.estimated_travel_time_sec // 60)} min {int(route.estimated_travel_time_sec % 60)} sec",
            "floors_visited": [f"Floor {f}" for f in route.floors_visited],
            "justifications": reasons,
            "transparency_notices": transparency,
            "active_obstacle_count": len(route.active_obstacles_encountered)
        }
