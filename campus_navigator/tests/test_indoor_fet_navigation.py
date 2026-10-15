"""Test Phase 3: Indoor FET Building Navigation.

Covers:
- Movement between connected rooms on the same floor.
- Movement between floors via elevators and stairwells.
- Rejection of disconnected destinations.
- Strict wheelchair routing without stairs.
- Elevator outage handling (blocking elevator and ensuring wheelchair recalculation fails gracefully with the mandated notice).
- Alternative route calculation inside the building.
- Floor selector and visual geometry data separation.
"""

import pytest
from campus_navigator.models.core_models import AccessibilityProfile
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine
from campus_navigator.data.loader import DataLoader


def test_connected_rooms_same_floor():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    # Route from Ground Floor West Ramp Lobby to Information Desk
    route = re.find_route("INDOOR_FET_G_RAMP_ENTRY", "INDOOR_FET_G_RECEPTION", wc)
    assert route.success
    assert route.stairs_count == 0
    assert route.floor_transitions_count == 0
    assert "INDOOR_FET_G_ATRIUM" in route.path_nodes


def test_multi_floor_movement():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    # Route from Ground Floor Atrium to 2nd Floor Smart Lecture 201
    route = re.find_route("INDOOR_FET_G_ATRIUM", "INDOOR_FET_2_LECTURE_201", wc)
    assert route.success
    assert route.elevators_used_count == 2  # G->1F, 1F->2F
    assert route.stairs_count == 0
    assert route.step_free_certified


def test_wheelchair_strictly_excludes_indoor_stairs():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    route = re.find_route("INDOOR_FET_1_CS_LAB_101", "INDOOR_FET_3_DEANS_SUITE", wc)
    assert route.success
    assert route.stairs_count == 0
    assert "INDOOR_FET_1_STAIRS" not in route.path_nodes
    assert "INDOOR_FET_2_STAIRS" not in route.path_nodes
    assert "INDOOR_FET_3_STAIRS" not in route.path_nodes


def test_elevator_outage_handling():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    # Block Ground to 1st floor elevator
    recalculated = re.recalculate_route(
        start_id="INDOOR_FET_G_ATRIUM",
        destination_id="INDOOR_FET_1_CS_LAB_101",
        profile=wc,
        new_blocked_id="E_FET_ELEV_G_TO_1"
    )

    # Wheelchair cannot climb stairs, so no step-free route exists
    assert not recalculated.success
    assert "No verified step-free route to this floor is available in the current building dataset." in recalculated.failure_reason


def test_walking_user_uses_stairs_during_elevator_outage():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    walk = AccessibilityProfile.general_walking()

    # If elevator is blocked, walking profile should fall back to stairs
    recalculated = re.recalculate_route(
        start_id="INDOOR_FET_G_ATRIUM",
        destination_id="INDOOR_FET_1_CS_LAB_101",
        profile=walk,
        new_blocked_id="E_FET_ELEV_G_TO_1"
    )

    assert recalculated.success
    assert recalculated.stairs_count >= 1
    assert "INDOOR_FET_G_STAIRS" in recalculated.path_nodes


def test_disconnected_destination_rejection():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    # Destination that doesn't exist
    res = re.find_route("INDOOR_FET_G_ATRIUM", "NON_EXISTENT_ROOM_999", wc)
    assert not res.success
    assert "does not exist" in res.failure_reason


def test_indoor_alternative_routes():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    walk = AccessibilityProfile.general_walking()

    # Between Ground Atrium and First Floor Concourse, walking user has 2 valid paths: Elevator vs Stairs
    alts = re.find_alternative_routes("INDOOR_FET_G_ATRIUM", "INDOOR_FET_1_CORRIDOR_MAIN", walk, max_alternatives=2)
    assert len(alts) >= 2
    assert alts[0].success
    assert alts[1].success


def test_floor_plan_data_separation():
    loader = DataLoader()
    bldgs = loader.load_buildings()
    plans = loader.load_floor_plans()
    pathways = loader.load_indoor_pathways()

    assert len(bldgs["buildings"]) >= 1
    assert "FET_MAIN" == bldgs["buildings"][0]["building_id"]
    assert "0" in plans["floors"]
    assert "1" in plans["floors"]
    assert "2" in plans["floors"]
    assert "3" in plans["floors"]
    assert len(pathways) >= 20
