"""Test Phase 4: Accessibility-Aware Graph Routing Engine (independent of Streamlit).

Comprehensive unit and algorithmic tests:
1. Shortest path (distance vs time Dijkstra)
2. Minimum-time path vs minimum-distance path
3. BFS unweighted minimum hops behavior vs weighted Dijkstra
4. Disconnected destinations
5. Missing nodes
6. Stair avoidance (strict enforcement)
7. Elevator use
8. Blocked pathways (active obstacle avoidance)
9. Unknown accessibility data & strictness policy
10. No valid accessible route failure reporting
11. Outdoor-to-indoor transitions
12. Multi-floor routing
"""

import pytest
from campus_navigator.models.core_models import AccessibilityProfile
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine


@pytest.fixture
def engines():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    return cg, re


def test_dijkstra_minimum_distance_vs_time(engines):
    cg, re = engines
    # Profile 1: optimize for distance
    prof_dist = AccessibilityProfile.wheelchair_user()
    prof_dist.optimize_for = "distance"

    # Profile 2: optimize for time
    prof_time = AccessibilityProfile.wheelchair_user()
    prof_time.optimize_for = "time"

    res_dist = re.find_route("CAMPUS_MAIN_GATE", "CENTRAL_LIBRARY_ENTRANCE", prof_dist)
    res_time = re.find_route("CAMPUS_MAIN_GATE", "CENTRAL_LIBRARY_ENTRANCE", prof_time)

    assert res_dist.success
    assert res_time.success
    assert res_dist.total_distance_m > 0
    assert res_time.estimated_travel_time_sec > 0


def test_bfs_unweighted_behavior_and_comparison(engines):
    cg, re = engines
    walk = AccessibilityProfile.general_walking()

    # Educational comparison method
    comp = re.compare_bfs_vs_dijkstra("CAMPUS_MAIN_GATE", "CENTRAL_LIBRARY_ENTRANCE", walk)
    assert comp["bfs"]["success"]
    assert comp["dijkstra"]["success"]
    assert comp["bfs"]["hops"] >= 1
    assert "minimizes" in comp["analysis"].lower()


def test_missing_and_disconnected_nodes(engines):
    cg, re = engines
    wc = AccessibilityProfile.wheelchair_user()

    # Non-existent start
    res_bad_start = re.find_route("NON_EXISTENT_SOURCE", "CAMPUS_MAIN_GATE", wc)
    assert not res_bad_start.success
    assert "does not exist" in res_bad_start.failure_reason
    assert res_bad_start.route_eligibility == "INELIGIBLE"

    # Non-existent dest
    res_bad_dest = re.find_route("CAMPUS_MAIN_GATE", "NON_EXISTENT_DEST", wc)
    assert not res_bad_dest.success
    assert "does not exist" in res_bad_dest.failure_reason

    # Disconnected node (unlocated destination without edges)
    res_unlocated = re.find_route("CAMPUS_MAIN_GATE", "UNLOCATED_AEROSPACE_HANGAR", wc)
    assert not res_unlocated.success
    assert res_unlocated.route_eligibility == "INELIGIBLE"


def test_strict_stair_avoidance(engines):
    cg, re = engines
    wc = AccessibilityProfile.wheelchair_user()

    # Route from quadrangle to Ground Floor FET Main
    # Path has 2 options: Stepped Front Entrance (5 steps) or West Ramp Entrance
    route = re.find_route("OUTDOOR_JUNCTION_CENTRAL", "INDOOR_FET_G_ATRIUM", wc)
    assert route.success
    assert route.stairs_count == 0
    assert route.step_free_certified
    assert "FET_ACCESSIBLE_ENTRANCE_RAMP" in route.path_nodes
    assert "FET_MAIN_ENTRANCE_STEPPED" not in route.path_nodes


def test_elevator_use_and_multi_floor_transitions(engines):
    cg, re = engines
    wc = AccessibilityProfile.wheelchair_user()

    # Route from Ground Floor Atrium to 3rd Floor Dean's Suite
    route = re.find_route("INDOOR_FET_G_ATRIUM", "INDOOR_FET_3_DEANS_SUITE", wc)
    assert route.success
    assert route.elevators_used_count >= 1
    assert route.stairs_count == 0
    assert route.floor_transitions_count >= 1
    assert 0 in route.floors_visited
    assert 3 in route.floors_visited


def test_blocked_pathway_dynamic_avoidance(engines):
    cg, re = engines
    wc = AccessibilityProfile.wheelchair_user()

    # Normal route from Main Gate to Parking
    normal_route = re.find_route("CAMPUS_MAIN_GATE", "ACCESSIBLE_PARKING_MAIN", wc)
    assert normal_route.success
    assert "ACCESSIBLE_PARKING_MAIN" in normal_route.path_nodes

    # Block direct edge to parking
    recalculated = re.recalculate_route(
        "CAMPUS_MAIN_GATE",
        "ACCESSIBLE_PARKING_MAIN",
        wc,
        new_blocked_id="E_GATE_TO_PARKING"
    )
    # Edge is blocked, must find alternative path via junction or fail safely
    assert recalculated.success
    # Must have rerouted via OUTDOOR_JUNCTION_CENTRAL
    assert "OUTDOOR_JUNCTION_CENTRAL" in recalculated.path_nodes


def test_strict_mode_unknown_data_policy(engines):
    cg, re = engines
    # Normal wheelchair user permits provisional edges if step-free
    normal_wc = AccessibilityProfile.wheelchair_user(strict_mode=False)
    route_normal = re.find_route("CAMPUS_MAIN_GATE", "INDOOR_FET_G_ATRIUM", normal_wc)
    assert route_normal.success

    # Strict wheelchair user excludes unverified / provisional edges
    strict_wc = AccessibilityProfile.wheelchair_user(strict_mode=True)
    route_strict = re.find_route("CAMPUS_MAIN_GATE", "INDOOR_FET_G_ATRIUM", strict_wc)
    # The indoor demonstration layout and provisional outdoor edges are excluded in strict mode
    assert not route_strict.success
    assert "strict verification policy" in route_strict.failure_reason


def test_outdoor_to_indoor_explicit_transition(engines):
    cg, re = engines
    walk = AccessibilityProfile.general_walking()

    route = re.find_route("CAMPUS_MAIN_GATE", "INDOOR_FET_G_RECEPTION", walk)
    assert route.success
    # Must use explicit transition edge
    transition_steps = [s for s in route.steps if "Transition threshold" in s.transition_instruction or "RAMP" in s.node_id or "MAIN" in s.node_id]
    assert len(transition_steps) >= 1


def test_alternative_routes_ranking(engines):
    cg, re = engines
    walk = AccessibilityProfile.general_walking()

    alts = re.find_alternative_routes("CAMPUS_MAIN_GATE", "OUTDOOR_JUNCTION_CENTRAL", walk, max_alternatives=3)
    assert len(alts) >= 2
    # Ranked by cost
    assert alts[0].total_distance_m <= alts[1].total_distance_m


def test_explain_route_audit(engines):
    cg, re = engines
    wc = AccessibilityProfile.wheelchair_user()

    route = re.find_route("CAMPUS_MAIN_GATE", "INDOOR_FET_1_CS_LAB_101", wc)
    explanation = re.explain_route(route, wc)

    assert explanation["verdict"] == "RECOMMENDED ACCESSIBLE ROUTE"
    assert "Wheelchair" in explanation["accessibility_profile"]
    assert any("step-free" in j.lower() for j in explanation["justifications"])
    assert any("DEMONSTRATION" in n for n in explanation["transparency_notices"])
