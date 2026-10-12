"""Test Phase 2 requirements: Geographic Map integration, unlocated destinations, resilient tile failure, and coordinate validation."""

import pytest
import folium
from campus_navigator.models.core_models import (
    AccessibilityProfile,
    VerificationStatus,
    LocationType,
)
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine
from campus_navigator.ui.map_builder import OutdoorMapBuilder
from campus_navigator.data.loader import DataLoader


def test_campus_geographic_coordinates():
    loader = DataLoader()
    meta, nodes, edges = loader.load_outdoor_data()

    # Campus center must be JAIN Global Campus, Jakkasandra
    center = meta["center_coordinates"]
    assert 12.63 <= center["latitude"] <= 12.66
    assert 77.42 <= center["longitude"] <= 77.46

    # Main Gate coordinate test
    gate = next(n for n in nodes if n.id == "CAMPUS_MAIN_GATE")
    assert gate.verification == VerificationStatus.VERIFIED
    assert gate.latitude is not None
    assert gate.longitude is not None
    assert gate.data_source is not None


def test_unlocated_destinations_handling():
    loader = DataLoader()
    meta, nodes, edges = loader.load_outdoor_data()

    # Must contain unlocated destinations rather than fabricating coordinates
    unlocated = [n for n in nodes if not n.is_geolocated()]
    assert len(unlocated) >= 2

    for un in unlocated:
        assert un.latitude is None
        assert un.longitude is None
        assert "Awaiting" in un.data_source or "Unlocated" in un.data_source


def test_map_builder_with_unlocated_and_controls():
    cg = CampusGraph()
    mb = OutdoorMapBuilder()

    # Map builder should ignore unlocated nodes for marker placing without crashing
    campus_map = mb.create_campus_map(
        nodes=cg.nodes,
        edges=cg.edges,
        selected_node_id="UNLOCATED_AEROSPACE_HANGAR"
    )
    assert isinstance(campus_map, folium.Map)
    html = campus_map._repr_html_()
    assert "OpenStreetMap" in html or "leaflet" in html.lower()


def test_map_builder_resilient_fallback():
    mb = OutdoorMapBuilder()
    # Pass invalid/corrupt node dict to verify fallback try/except
    corrupted_nodes = {"BAD_NODE": "not_a_node_object"}
    fallback_map = mb.create_campus_map(
        nodes=corrupted_nodes,
        edges={}
    )
    assert isinstance(fallback_map, folium.Map)
    html = fallback_map._repr_html_()
    assert html is not None


def test_route_calculation_follows_known_pathways():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    # Calculate route from Main Gate to Central Library Entrance
    route = re.find_route("CAMPUS_MAIN_GATE", "CENTRAL_LIBRARY_ENTRANCE", wc)
    assert route.success
    # The route must follow defined outdoor edges
    for i in range(len(route.path_nodes) - 1):
        u = route.path_nodes[i]
        v = route.path_nodes[i + 1]
        edge = cg.get_edge_between(u, v)
        assert edge is not None, f"No pathway edge between {u} and {v}"
        assert edge.is_step_free, f"Pathway between {u} and {v} is not step-free"


def test_unlocated_destination_routing_rejection():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    # Routing to an unlocated destination with no mapped edges should fail cleanly
    route = re.find_route("CAMPUS_MAIN_GATE", "UNLOCATED_AEROSPACE_HANGAR", wc)
    assert not route.success
    assert "No path satisfies all mandatory accessibility constraints" in route.failure_reason
