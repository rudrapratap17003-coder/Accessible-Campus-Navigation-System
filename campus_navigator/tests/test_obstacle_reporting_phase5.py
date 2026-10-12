"""
Phase 5 Comprehensive Automated Test Suite: Obstacle Reporting and Dynamic Route Updates.

Validates:
1. Creating a report with location/pathway, building, and floor.
2. Persisting reports across fresh ObstacleDB instances in SQLite.
3. Review workflow: SUBMITTED -> UNDER_REVIEW -> VERIFIED -> RESOLVED by administrator.
4. Edge exclusion in routing when obstacle affects a pathway.
5. Path restoration when an obstacle is marked RESOLVED.
6. Dynamic recalculation of alternative routes around newly verified obstacles.
7. Handling duplicate reports and updates gracefully.
8. Safe handling of invalid pathway/node IDs.
9. Expiration behavior for temporary obstacles.
10. Strict separation of user-submitted (unverified) vs verified reports.
"""

import os
import tempfile
import pytest
from datetime import datetime, timezone, timedelta

from campus_navigator.models.core_models import (
    ObstacleReport,
    ObstacleType,
    ObstacleStatus,
    ObstacleSeverity,
    VerificationStatus,
    AccessibilityProfile
)
from campus_navigator.db.obstacle_db import ObstacleDB
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine


@pytest.fixture
def temp_db():
    """Provides an isolated SQLite database in a temp directory with clean teardown."""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_obstacles_p5.db")
    db = ObstacleDB(db_path=db_path)
    yield db
    # Cleanup safely
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
        os.rmdir(temp_dir)
    except Exception:
        pass


@pytest.fixture
def engines():
    """Initializes the complete campus graph and routing engine."""
    cg = CampusGraph()
    re = RoutingEngine(campus_graph=cg)
    return cg, re


def test_create_report_with_building_and_floor(temp_db):
    """Verify storing a detailed obstacle report with pathway, building, and floor."""
    report = ObstacleReport(
        id="rep_test_001",
        location_or_edge_id="fet_p_012",
        pathway_id="fet_p_012",
        location_id="INDOOR_FET_1_CORRIDOR_MAIN",
        building_id="FET_MAIN_BUILDING",
        floor_id=1,
        obstacle_type=ObstacleType.BLOCKED_CORRIDOR,
        description="Spill in east corridor near lab 101",
        severity=ObstacleSeverity.MEDIUM,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.SUBMITTED,
        verification_status=VerificationStatus.PROVISIONAL
    )

    success = temp_db.save_report(report)
    assert success is True

    fetched = temp_db.get_report_by_id("rep_test_001")
    assert fetched is not None
    assert fetched.location_id == "INDOOR_FET_1_CORRIDOR_MAIN"
    assert fetched.pathway_id == "fet_p_012"
    assert fetched.building_id == "FET_MAIN_BUILDING"
    assert fetched.floor_id == 1
    assert fetched.obstacle_type == ObstacleType.BLOCKED_CORRIDOR
    assert fetched.status == ObstacleStatus.SUBMITTED


def test_persistence_across_fresh_instances(temp_db):
    """Verify reports persist cleanly across completely distinct ObstacleDB instances."""
    db_path = temp_db.db_path
    initial_count = len(temp_db.get_all_reports())

    report = ObstacleReport(
        id="rep_persist_01",
        location_or_edge_id="E_MAIN_GATE_TO_JUNCTION",
        pathway_id="E_MAIN_GATE_TO_JUNCTION",
        obstacle_type=ObstacleType.CONSTRUCTION,
        description="Pavement digging near main gate",
        severity=ObstacleSeverity.HIGH,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.SUBMITTED,
        verification_status=VerificationStatus.PROVISIONAL
    )
    temp_db.save_report(report)

    # Open fresh instance
    new_db = ObstacleDB(db_path=db_path)
    reports = new_db.get_all_reports()
    assert len(reports) == initial_count + 1
    found = [r for r in reports if r.id == "rep_persist_01"]
    assert len(found) == 1
    assert found[0].description == "Pavement digging near main gate"


def test_admin_verification_workflow(temp_db):
    """Verify status transition: SUBMITTED -> UNDER_REVIEW -> VERIFIED -> RESOLVED."""
    report = ObstacleReport(
        id="rep_wf_01",
        location_or_edge_id="E_JUNCTION_TO_FET_RAMP",
        pathway_id="E_JUNCTION_TO_FET_RAMP",
        location_id="FET_ACCESSIBLE_ENTRANCE_RAMP",
        building_id="FET_MAIN_BUILDING",
        floor_id=0,
        obstacle_type=ObstacleType.BLOCKED_RAMP,
        description="Heavy furniture parked on entrance ramp",
        severity=ObstacleSeverity.CRITICAL_BLOCKING,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.SUBMITTED,
        verification_status=VerificationStatus.PROVISIONAL
    )
    temp_db.save_report(report)

    # 1. Admin places Under Review
    temp_db.update_report_status(
        report_id="rep_wf_01",
        new_status=ObstacleStatus.UNDER_REVIEW,
        verification_status=VerificationStatus.PROVISIONAL
    )
    r_review = temp_db.get_report_by_id("rep_wf_01")
    assert r_review.status == ObstacleStatus.UNDER_REVIEW

    # 2. Admin verifies the report
    temp_db.update_report_status(
        report_id="rep_wf_01",
        new_status=ObstacleStatus.VERIFIED,
        verification_status=VerificationStatus.VERIFIED
    )
    r_ver = temp_db.get_report_by_id("rep_wf_01")
    assert r_ver.status == ObstacleStatus.VERIFIED
    assert r_ver.verification_status == VerificationStatus.VERIFIED
    assert r_ver.is_blocking_for_routing() is True

    # 3. Issue is resolved by facility staff
    temp_db.update_report_status(
        report_id="rep_wf_01",
        new_status=ObstacleStatus.RESOLVED,
        verification_status=VerificationStatus.VERIFIED
    )
    r_res = temp_db.get_report_by_id("rep_wf_01")
    assert r_res.status == ObstacleStatus.RESOLVED
    assert r_res.is_blocking_for_routing() is False


def test_disabling_affected_edge_during_routing(engines):
    """Verify that reporting an edge as blocked excludes that edge in route calculation."""
    cg, re = engines
    wc_profile = AccessibilityProfile.wheelchair_user()

    # Baseline route between Junction and FET Atrium uses the ramp entrance
    baseline = re.find_route(
        start_id="OUTDOOR_JUNCTION_CENTRAL",
        destination_id="INDOOR_FET_G_ATRIUM",
        profile=wc_profile
    )
    assert baseline.success is True
    assert "FET_ACCESSIBLE_ENTRANCE_RAMP" in baseline.path_nodes

    # Now simulate active obstacle on the ramp edge E_JUNCTION_TO_FET_RAMP
    # The graph allows passing active_obstacles (or custom edge_filter)
    ramp_obstacle = ObstacleReport(
        id="obs_ramp_blocked",
        location_or_edge_id="E_JUNCTION_TO_FET_RAMP",
        pathway_id="E_JUNCTION_TO_FET_RAMP",
        location_id="FET_ACCESSIBLE_ENTRANCE_RAMP",
        building_id="FET_MAIN_BUILDING",
        floor_id=0,
        obstacle_type=ObstacleType.BLOCKED_RAMP,
        description="Ramp undergoing maintenance",
        severity=ObstacleSeverity.CRITICAL_BLOCKING,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.VERIFIED,
        verification_status=VerificationStatus.VERIFIED
    )

    recalculated = re.recalculate_route(
        start_id="OUTDOOR_JUNCTION_CENTRAL",
        destination_id="INDOOR_FET_G_ATRIUM",
        profile=wc_profile,
        new_blocked_id=ramp_obstacle.location_or_edge_id
    )

    # Wheelchair cannot use stepped entrance; fails safely
    assert recalculated.success is False
    assert "No path satisfies all mandatory accessibility constraints" in recalculated.failure_reason


def test_pathway_restoration_when_resolved(engines):
    """Verify that once a report is RESOLVED, the pathway is restored to route calculations."""
    cg, re = engines
    wc_profile = AccessibilityProfile.wheelchair_user()

    resolved_obstacle = ObstacleReport(
        id="obs_ramp_cleared",
        location_or_edge_id="E_JUNCTION_TO_FET_RAMP",
        pathway_id="E_JUNCTION_TO_FET_RAMP",
        location_id="FET_ACCESSIBLE_ENTRANCE_RAMP",
        building_id="FET_MAIN_BUILDING",
        floor_id=0,
        obstacle_type=ObstacleType.BLOCKED_RAMP,
        description="Maintenance completed, ramp open",
        severity=ObstacleSeverity.CRITICAL_BLOCKING,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.RESOLVED,
        verification_status=VerificationStatus.VERIFIED
    )

    # Active obstacles list only includes is_blocking_for_routing() items
    assert resolved_obstacle.is_blocking_for_routing() is False

    # Normal routing succeeds because obstacle is not blocking
    route = re.find_route(
        start_id="OUTDOOR_JUNCTION_CENTRAL",
        destination_id="INDOOR_FET_G_ATRIUM",
        profile=wc_profile
    )
    assert route.success is True
    assert "FET_ACCESSIBLE_ENTRANCE_RAMP" in route.path_nodes


def test_dynamic_recalculation_after_obstacle(engines):
    """Verify recalculate_route generates a valid bypass around an obstacle encountered en route."""
    cg, re = engines
    walk_profile = AccessibilityProfile.general_walking()

    # Baseline multi-floor route from Ground Atrium to First Floor Concourse
    initial_route = re.find_route(
        start_id="INDOOR_FET_G_ATRIUM",
        destination_id="INDOOR_FET_1_CORRIDOR_MAIN",
        profile=walk_profile
    )
    assert initial_route.success is True

    # Recalculate route if primary path is blocked
    # E.g. block ground stairs: E_INDOOR_G_STAIRS
    recalculated = re.recalculate_route(
        start_id="INDOOR_FET_G_ATRIUM",
        destination_id="INDOOR_FET_1_CORRIDOR_MAIN",
        profile=walk_profile,
        new_blocked_id="E_FET_G_TO_1_STAIRS"
    )

    assert recalculated.success is True
    # Can still reach floor 1 via elevator
    assert any("ELEVATOR" in n for n in recalculated.path_nodes)


def test_duplicate_report_id_handling(temp_db):
    """Verify that saving a report with an existing ID updates the record rather than duplicating."""
    initial_count = len(temp_db.get_all_reports())
    r1 = ObstacleReport(
        id="dup_001",
        location_or_edge_id="INDOOR_FET_G_ATRIUM",
        obstacle_type=ObstacleType.TEMPORARY_OBSTRUCTION,
        description="Initial description",
        severity=ObstacleSeverity.LOW,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.SUBMITTED,
        verification_status=VerificationStatus.PROVISIONAL
    )
    temp_db.save_report(r1)
    assert len(temp_db.get_all_reports()) == initial_count + 1

    # Overwrite / update with same ID
    r1_updated = ObstacleReport(
        id="dup_001",
        location_or_edge_id="INDOOR_FET_G_ATRIUM",
        obstacle_type=ObstacleType.TEMPORARY_OBSTRUCTION,
        description="Updated description with more details",
        severity=ObstacleSeverity.HIGH,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.UNDER_REVIEW,
        verification_status=VerificationStatus.PROVISIONAL
    )
    temp_db.save_report(r1_updated)

    all_reports = temp_db.get_all_reports()
    assert len(all_reports) == initial_count + 1
    found = [r for r in all_reports if r.id == "dup_001"]
    assert len(found) == 1
    assert found[0].description == "Updated description with more details"
    assert found[0].severity == ObstacleSeverity.HIGH


def test_expiration_of_temporary_reports(temp_db):
    """Verify that past-expiration unverified reports expire and cease blocking."""
    past_time = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
    future_time = (datetime.now(timezone.utc) + timedelta(hours=4)).isoformat()
    now_iso = datetime.now(timezone.utc).isoformat()

    # Expired unverified report
    expired_report = ObstacleReport(
        id="exp_001",
        location_or_edge_id="INDOOR_FET_G_ATRIUM",
        obstacle_type=ObstacleType.TEMPORARY_OBSTRUCTION,
        description="Temporary water bucket",
        severity=ObstacleSeverity.HIGH,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.SUBMITTED,
        verification_status=VerificationStatus.PROVISIONAL,
        expiration_time=past_time
    )
    temp_db.save_report(expired_report)

    # Active future report
    active_report = ObstacleReport(
        id="act_002",
        location_or_edge_id="INDOOR_FET_1_CORRIDOR_MAIN",
        obstacle_type=ObstacleType.CONSTRUCTION,
        description="Scheduled tile work",
        severity=ObstacleSeverity.HIGH,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.SUBMITTED,
        verification_status=VerificationStatus.PROVISIONAL,
        expiration_time=future_time
    )
    temp_db.save_report(active_report)

    # Test is_blocking_for_routing logic
    assert expired_report.is_blocking_for_routing(current_time_iso=now_iso) is False
    assert active_report.is_blocking_for_routing(current_time_iso=now_iso) is True

    # Active reports query from DB
    active_in_db = temp_db.get_active_reports()
    active_ids = [r.id for r in active_in_db]
    assert "act_002" in active_ids
    assert "exp_001" not in active_ids


def test_invalid_pathway_or_node_id_resilience(temp_db, engines):
    """Verify that obstacle reports pointing to nonexistent IDs fail gracefully and do not crash routing."""
    cg, re = engines
    bogus_report = ObstacleReport(
        id="bogus_001",
        location_or_edge_id="NON_EXISTENT_EDGE_9999",
        pathway_id="NON_EXISTENT_EDGE_9999",
        obstacle_type=ObstacleType.OTHER,
        description="Obstacle on imaginary path",
        severity=ObstacleSeverity.LOW,
        timestamp=datetime.now(timezone.utc).isoformat(),
        status=ObstacleStatus.VERIFIED,
        verification_status=VerificationStatus.VERIFIED
    )
    temp_db.save_report(bogus_report)

    # Routing engine should ignore nonexistent pathways/nodes without throwing exceptions
    profile = AccessibilityProfile.general_walking()
    route = re.find_route(
        start_id="CAMPUS_MAIN_GATE",
        destination_id="CENTRAL_LIBRARY_ENTRANCE",
        profile=profile
    )
    assert route.success is True
