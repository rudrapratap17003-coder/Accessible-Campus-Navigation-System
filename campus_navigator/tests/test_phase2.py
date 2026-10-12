"""Test Phase 2: Graph construction, Dijkstra, BFS, stairs exclusions, obstacles, and multi-floor transitions."""

import pytest
from campus_navigator.models.core_models import AccessibilityProfile
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine


@pytest.fixture
def engines():
    cg = CampusGraph()
    re = RoutingEngine(campus_graph=cg)
    return cg, re


def test_outdoor_to_indoor_wheelchair_route(engines):
    cg, re = engines
    wc_profile = AccessibilityProfile.wheelchair_user()

    # Route from Campus Entrance to 1st Floor CS Lab 101
    route = re.find_route(
        start_id="CAMPUS_MAIN_GATE",
        destination_id="INDOOR_FET_1_CS_LAB_101",
        profile=wc_profile
    )

    assert route.success
    assert route.stairs_count == 0
    assert route.step_free_certified
    assert route.elevators_used_count >= 1
    # Must use ramp entrance, NOT stepped entrance
    assert "FET_ACCESSIBLE_ENTRANCE_RAMP" in route.path_nodes
    assert "FET_MAIN_ENTRANCE_STEPPED" not in route.path_nodes


def test_walking_user_can_use_stairs(engines):
    cg, re = engines
    walk_profile = AccessibilityProfile.general_walking()

    # Route from Ground Atrium to First Floor Concourse
    route = re.find_route(
        start_id="INDOOR_FET_G_ATRIUM",
        destination_id="INDOOR_FET_1_CORRIDOR_MAIN",
        profile=walk_profile
    )

    assert route.success
    # General walking profile can use stairs or elevator depending on time/distance
    assert len(route.path_nodes) > 0


def test_wheelchair_strictly_excludes_stairs(engines):
    cg, re = engines
    wc_profile = AccessibilityProfile.wheelchair_user()

    # Route directly inside between Ground and 2nd Floor
    route = re.find_route(
        start_id="INDOOR_FET_G_ATRIUM",
        destination_id="INDOOR_FET_2_LECTURE_201",
        profile=wc_profile
    )

    assert route.success
    assert route.stairs_count == 0
    assert route.elevators_used_count >= 1
    # Check that stairwell nodes are never touched
    assert "INDOOR_FET_G_STAIRS" not in route.path_nodes
    assert "INDOOR_FET_1_STAIRS" not in route.path_nodes
    assert "INDOOR_FET_2_STAIRS" not in route.path_nodes


def test_bfs_unweighted_route(engines):
    cg, re = engines
    walk_profile = AccessibilityProfile.general_walking()

    bfs_route = re.find_bfs_route(
        start_id="CAMPUS_MAIN_GATE",
        destination_id="CENTRAL_LIBRARY_ENTRANCE",
        profile=walk_profile
    )
    assert bfs_route.success
    assert bfs_route.algorithm == "BFS (Minimum Hops)"


def test_obstacle_recalculation(engines):
    cg, re = engines
    wc_profile = AccessibilityProfile.wheelchair_user()

    # Initially path through ramp is clear
    initial_route = re.find_route(
        start_id="OUTDOOR_JUNCTION_CENTRAL",
        destination_id="INDOOR_FET_G_ATRIUM",
        profile=wc_profile
    )
    assert initial_route.success

    # If the ramp edge is blocked, recalculating route for wheelchair should fail or find alternative
    # In our graph, the only other entrance is stepped (5 steps), so wheelchair should fail gracefully with clear explanation
    recalculated = re.recalculate_route(
        start_id="OUTDOOR_JUNCTION_CENTRAL",
        destination_id="INDOOR_FET_G_ATRIUM",
        profile=wc_profile,
        new_blocked_id="E_JUNCTION_TO_FET_RAMP"
    )

    assert not recalculated.success
    assert "No path satisfies all mandatory accessibility constraints" in recalculated.failure_reason


def test_alternative_routes(engines):
    cg, re = engines
    walk_profile = AccessibilityProfile.general_walking()

    alts = re.find_alternative_routes(
        start_id="CAMPUS_MAIN_GATE",
        destination_id="OUTDOOR_JUNCTION_CENTRAL",
        profile=walk_profile,
        max_alternatives=2
    )

    # There are two paths: direct vs via Parking
    assert len(alts) >= 1
    assert alts[0].success


def test_explain_route(engines):
    cg, re = engines
    wc = AccessibilityProfile.wheelchair_user()
    route = re.find_route(
        start_id="CAMPUS_MAIN_GATE",
        destination_id="INDOOR_FET_G_AUDITORIUM_HALL",
        profile=wc
    )
    explanation = re.explain_route(route, wc)
    assert explanation["verdict"] == "RECOMMENDED ACCESSIBLE ROUTE"
    assert len(explanation["justifications"]) > 0
    assert len(explanation["transparency_notices"]) > 0
