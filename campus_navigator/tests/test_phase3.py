"""Test Phase 3: Visual map rendering and floor plan generation."""

import pytest
from campus_navigator.models.core_models import AccessibilityProfile
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine
from campus_navigator.ui.map_builder import OutdoorMapBuilder
from campus_navigator.ui.floor_visualizer import FloorPlanVisualizer


def test_outdoor_map_generation():
    cg = CampusGraph()
    builder = OutdoorMapBuilder()
    campus_map = builder.create_campus_map(
        nodes=cg.nodes,
        edges=cg.edges,
        obstacles=cg.obstacle_db.get_all_reports()
    )
    # Folium map should produce valid html representation
    html = campus_map._repr_html_()
    assert "leaflet" in html.lower()
    assert len(html) > 500


def test_outdoor_map_with_route():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()
    route = re.find_route("CAMPUS_MAIN_GATE", "CENTRAL_LIBRARY_ENTRANCE", wc)

    builder = OutdoorMapBuilder()
    campus_map = builder.create_campus_map(
        nodes=cg.nodes,
        edges=cg.edges,
        active_route=route
    )
    html = campus_map._repr_html_()
    assert html is not None


def test_indoor_floor_visualizer():
    cg = CampusGraph()
    viz = FloorPlanVisualizer()

    # Test all 4 floors render successfully
    for floor_idx in [0, 1, 2, 3]:
        fig = viz.render_floor(
            floor_level=floor_idx,
            nodes=cg.nodes,
            edges=cg.edges
        )
        assert fig is not None
        assert "DEMONSTRATION FLOOR PLAN" in fig.layout.annotations[0].text
