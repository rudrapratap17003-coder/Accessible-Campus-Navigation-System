"""Graph engine for Accessible Campus Navigator.

Constructs unified NetworkX graph structures combining:
1. Outdoor geographic network
2. Indoor 4-floor architectural network
3. Explicit outdoor-indoor transition connectors
4. Dynamic filtering based on active obstacles and accessibility constraints
"""

import networkx as nx
from typing import Dict, Any, List, Optional, Tuple, Set
from campus_navigator.models.core_models import (
    LocationNode,
    PathwayEdge,
    AccessibilityProfile,
    VerificationStatus,
    ObstacleReport,
)
from campus_navigator.data.loader import DataLoader
from campus_navigator.data.transitions import CAMPUS_TRANSITIONS
from campus_navigator.db.obstacle_db import ObstacleDB


class CampusGraph:
    def __init__(self, data_loader: Optional[DataLoader] = None, obstacle_db: Optional[ObstacleDB] = None):
        self.loader = data_loader or DataLoader()
        self.obstacle_db = obstacle_db or ObstacleDB()
        self.nodes: Dict[str, LocationNode] = {}
        self.edges: Dict[str, PathwayEdge] = {}
        self.graph = nx.Graph()
        self.outdoor_meta: Dict[str, Any] = {}
        self.indoor_meta: Dict[str, Any] = {}
        
        self.build_graph()

    def build_graph(self) -> None:
        """Construct the combined outdoor and indoor graph."""
        self.graph.clear()
        self.nodes.clear()
        self.edges.clear()

        # 1. Load Outdoor Data
        self.outdoor_meta, out_nodes, out_edges = self.loader.load_outdoor_data()
        for node in out_nodes:
            self.nodes[node.id] = node
            self.graph.add_node(
                node.id,
                **node.to_dict()
            )

        for edge in out_edges:
            self.edges[edge.id] = edge
            self._add_bidirectional_edge(edge)

        # 2. Load Indoor Data
        self.indoor_meta, in_nodes, in_edges = self.loader.load_indoor_data()
        for node in in_nodes:
            self.nodes[node.id] = node
            self.graph.add_node(
                node.id,
                **node.to_dict()
            )

        for edge in in_edges:
            self.edges[edge.id] = edge
            self._add_bidirectional_edge(edge)

        # 3. Add Explicit Outdoor <-> Indoor Transitions
        for trans in CAMPUS_TRANSITIONS:
            edge = PathwayEdge(
                id=trans["id"],
                source=trans["outdoor_node_id"],
                target=trans["indoor_node_id"],
                distance_m=trans["distance_m"],
                estimated_time_sec=trans["estimated_time_sec"],
                verification=VerificationStatus.PROVISIONAL,
                is_step_free=trans["is_step_free"],
                has_stairs=trans["has_stairs"],
                has_ramp=trans["has_ramp"],
                is_elevator=False,
                is_indoor=False,
                floor_transition=False,
                notes=trans["notes"]
            )
            self.edges[edge.id] = edge
            self._add_bidirectional_edge(edge)

    def _add_bidirectional_edge(self, edge: PathwayEdge) -> None:
        """Add undirected pathway edge."""
        edge_data = edge.to_dict()
        self.graph.add_edge(
            edge.source,
            edge.target,
            edge_id=edge.id,
            **edge_data
        )

    def get_node(self, node_id: str) -> Optional[LocationNode]:
        return self.nodes.get(node_id)

    def get_edge(self, edge_id: str) -> Optional[PathwayEdge]:
        return self.edges.get(edge_id)

    def get_edge_between(self, u: str, v: str) -> Optional[PathwayEdge]:
        if self.graph.has_edge(u, v):
            data = self.graph.get_edge_data(u, v)
            edge_id = data.get("edge_id")
            if edge_id and edge_id in self.edges:
                return self.edges[edge_id]
        return None

    def get_filtered_subgraph(
        self,
        profile: AccessibilityProfile,
        blocked_ids: Optional[Set[str]] = None
    ) -> Tuple[nx.Graph, List[str]]:
        """
        Creates a subgraph filtered by:
        1. Mandatory mobility constraints (stairs prohibited for wheelchair, elevators forbidden if disallowed)
        2. Active blocking obstacles from the SQLite database
        Returns the filtered graph and a list of rejection reasons.
        """
        if blocked_ids is None:
            blocked_ids = self.obstacle_db.get_blocked_target_ids()

        filtered = self.graph.copy()
        rejections = []

        # 1. Filter blocked nodes
        nodes_to_remove = []
        for n_id, n_data in list(filtered.nodes(data=True)):
            if n_id in blocked_ids:
                nodes_to_remove.append(n_id)
                rejections.append(f"Node '{n_data.get('name', n_id)}' excluded: Active obstacle reported.")
        for n_id in nodes_to_remove:
            filtered.remove_node(n_id)

        # 2. Filter edges by profile constraints and edge obstacles
        edges_to_remove = []
        for u, v, data in list(filtered.edges(data=True)):
            e_id = data.get("edge_id", "")
            edge_name = f"{self.nodes.get(u, u).name} <-> {self.nodes.get(v, v).name}"

            # Check if edge is explicitly blocked
            if e_id in blocked_ids:
                edges_to_remove.append((u, v))
                rejections.append(f"Pathway '{edge_name}' excluded: Active obstacle on pathway.")
                continue

            # Mandatory constraint: Stairs prohibited
            if not profile.permit_stairs and data.get("has_stairs", False):
                edges_to_remove.append((u, v))
                rejections.append(f"Pathway '{edge_name}' excluded: Contains stairs, forbidden for {profile.name}.")
                continue

            # Mandatory constraint: Step-free access required
            if profile.require_step_free and not data.get("is_step_free", True):
                edges_to_remove.append((u, v))
                rejections.append(f"Pathway '{edge_name}' excluded: Not step-free, violates {profile.name} requirement.")
                continue

            # Elevators allowed check
            if not profile.allow_elevators and data.get("is_elevator", False):
                edges_to_remove.append((u, v))
                rejections.append(f"Pathway '{edge_name}' excluded: Elevator transport disabled by user profile.")
                continue

            # Strict mode: exclude unverified or demonstration pathways and unknown accessibility
            if profile.strict_mode:
                verif = data.get("verification", "PROVISIONAL")
                if verif not in ("VERIFIED", VerificationStatus.VERIFIED.value):
                    edges_to_remove.append((u, v))
                    rejections.append(f"Pathway '{edge_name}' excluded by strictness policy: Pathway verification is '{verif}' (not certified on-site).")
                    continue

        for u, v in edges_to_remove:
            filtered.remove_edge(u, v)

        return filtered, rejections
