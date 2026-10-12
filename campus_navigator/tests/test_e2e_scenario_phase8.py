"""
Repeatable End-to-End Wheelchair Demonstration Test Scenario.

Scenario Flow (Explicitly labeled sample/demonstration data):
1. Origin: 'CAMPUS_MAIN_GATE' (Main Campus Entrance)
2. Destination: 'INDOOR_FET_1_CS_LAB_101' (1st Floor Computer Science Lab 101)
3. Profile: Wheelchair User (Permit stairs = False, Step-free mandatory, Elevators allowed).
4. Step 1: Calculate initial route -> Succeeds with step-free certified ramp entrance and passenger elevator.
5. Step 2: Traverse outdoor to indoor, transitioning from Ground Floor to 1st Floor via elevator.
6. Step 3: Simulate an active Elevator Outage report affecting 'FET_ELEVATOR' / 'E_INDOOR_G_ELEVATOR'.
7. Step 4: Dynamically recalculate route for wheelchair user.
8. Step 5: Since the building demonstration model only has stairs as an alternate vertical link between floors,
   the wheelchair routing engine strictly refuses to route via stairs and safely reports no eligible accessible route
   with transparent rejection audit reasons.
9. Step 6: Verify a General Walking profile CAN use the stairs alternative during the elevator outage.
"""

import pytest
import os
import tempfile
from datetime import datetime, timezone

from campus_navigator.models.core_models import (
    AccessibilityProfile,
    ObstacleReport,
    ObstacleType,
    ObstacleSeverity,
    ObstacleStatus,
    VerificationStatus
)
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine
from campus_navigator.db.obstacle_db import ObstacleDB


@pytest.fixture
def scenario_env():
    """Sets up an isolated database and routing engine for the E2E scenario."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "scenario_demo.db")
    db = ObstacleDB(db_path=db_path)
    cg = CampusGraph(obstacle_db=db)
    re = RoutingEngine(campus_graph=cg)
    yield db, cg, re
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


def test_repeatable_wheelchair_e2e_scenario(scenario_env):
    """Executes the complete end-to-end scenario lifecycle."""
    db, cg, re = scenario_env
    wc_profile = AccessibilityProfile.wheelchair_user()

    # ---------------------------------------------------------
    # STAGE 1: Calculate initial eligible step-free route
    # ---------------------------------------------------------
    start_node = "CAMPUS_MAIN_GATE"
    dest_node = "INDOOR_FET_1_CS_LAB_101"

    initial_route = re.find_route(
        start_id=start_node,
        destination_id=dest_node,
        profile=wc_profile
    )

    # Assert initial route validity
    assert initial_route.success is True, "Initial route should succeed under normal conditions"
    assert initial_route.step_free_certified is True, "Wheelchair route must be step-free certified"
    assert initial_route.stairs_count == 0, "Wheelchair route must have exactly 0 stairs"
    assert initial_route.elevators_used_count >= 1, "Must use elevator to reach Floor 1"
    assert initial_route.total_distance_m > 0, "Distance must be positive"
    assert initial_route.estimated_travel_time_sec > 0, "Estimated time must be positive"

    # Verify outdoor-to-indoor transition: uses ramp entrance, strictly avoids stepped entrance
    assert "FET_ACCESSIBLE_ENTRANCE_RAMP" in initial_route.path_nodes
    assert "FET_MAIN_ENTRANCE_STEPPED" not in initial_route.path_nodes

    # ---------------------------------------------------------
    # STAGE 2: Inspect Step-by-Step Directions
    # ---------------------------------------------------------
    assert len(initial_route.steps) >= 5
    instructions = [s.transition_instruction for s in initial_route.steps]
    assert any("elevator" in inst.lower() for inst in instructions)

    # ---------------------------------------------------------
    # STAGE 3: Elevator Outage Obstacle Report
    # ---------------------------------------------------------
    # Elevator link between Ground and Floor 1: E_FET_ELEV_G_TO_1
    outage_report = ObstacleReport(
        id="OBS-DEMO-ELEV-OUTAGE",
        location_or_edge_id="E_FET_ELEV_G_TO_1",
        pathway_id="E_FET_ELEV_G_TO_1",
        building_id="FET_MAIN",
        floor_id=0,
        obstacle_type=ObstacleType.ELEVATOR_UNAVAILABLE,
        description="Demonstration: FET Passenger Elevator offline for motor overhaul",
        severity=ObstacleSeverity.CRITICAL_BLOCKING,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.VERIFIED,
        verification_status=VerificationStatus.VERIFIED
    )
    db.save_report(outage_report)

    # Verify report is saved and blocking
    saved_rep = db.get_report("OBS-DEMO-ELEV-OUTAGE")
    assert saved_rep is not None
    assert saved_rep.is_blocking_for_routing() is True

    # ---------------------------------------------------------
    # STAGE 4: Dynamic Recalculation for Wheelchair User
    # ---------------------------------------------------------
    recalc_wc = re.recalculate_route(
        start_id=start_node,
        destination_id=dest_node,
        profile=wc_profile,
        new_blocked_id="E_FET_ELEV_G_TO_1"
    )

    # Because no other step-free vertical link exists, wheelchair route must safely fail
    assert recalc_wc.success is False, "Wheelchair route must fail safely when the sole elevator is out of service"
    assert "No path satisfies all mandatory accessibility constraints" in recalc_wc.failure_reason

    # Audit transparency verification
    explanation = re.explain_route(recalc_wc, wc_profile)
    assert "INELIGIBLE" in explanation["verdict"] or "UNAVAILABLE" in explanation["verdict"]
    assert len(recalc_wc.rejection_explanations) > 0

    # ---------------------------------------------------------
    # STAGE 5: Contrast with Walking User (Can Use Stairs Alternative)
    # ---------------------------------------------------------
    walking_profile = AccessibilityProfile.general_walking()
    recalc_walk = re.recalculate_route(
        start_id=start_node,
        destination_id=dest_node,
        profile=walking_profile,
        new_blocked_id="E_FET_ELEV_G_TO_1"
    )

    # Walking user CAN reach CS Lab 101 by taking the stairs
    assert recalc_walk.success is True, "General walking user should succeed by taking stairs"
    assert recalc_walk.stairs_count > 0, "Walking user route should contain stairs"
    assert "E_FET_ELEV_G_TO_1" not in [s.edge_taken.id for s in recalc_walk.steps if s.edge_taken]
    assert any("STAIR" in n for n in recalc_walk.path_nodes)
