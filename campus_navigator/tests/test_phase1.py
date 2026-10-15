"""Test Phase 1: Data models, JSON loader, and SQLite obstacle storage."""

import pytest
import tempfile
import os
from campus_navigator.models.core_models import (
    AccessibilityProfile,
    LocationNode,
    PathwayEdge,
    ObstacleReport,
    ObstacleStatus,
    ObstacleSeverity,
    ObstacleType,
    VerificationStatus,
    LocationType,
)
from campus_navigator.db.obstacle_db import ObstacleDB
from campus_navigator.data.loader import DataLoader


def test_accessibility_profiles():
    wc = AccessibilityProfile.wheelchair_user()
    assert not wc.permit_stairs
    assert wc.require_step_free
    assert wc.prefer_ramps
    assert wc.allow_elevators

    walk = AccessibilityProfile.general_walking()
    assert walk.permit_stairs
    assert not walk.require_step_free


def test_data_loader_outdoor():
    loader = DataLoader()
    meta, nodes, edges = loader.load_outdoor_data()

    assert "JAIN" in meta["name"]
    assert len(nodes) >= 10
    assert len(edges) >= 10

    # Ensure geolocated nodes have valid coordinates and unlocated nodes have None
    geolocated = [n for n in nodes if n.is_geolocated()]
    unlocated = [n for n in nodes if not n.is_geolocated()]
    assert len(geolocated) >= 10
    assert len(unlocated) >= 2

    for node in geolocated:
        assert node.latitude is not None
        assert node.longitude is not None
        assert node.verification in (VerificationStatus.VERIFIED, VerificationStatus.PROVISIONAL)


def test_data_loader_indoor():
    loader = DataLoader()
    meta, nodes, edges = loader.load_indoor_data()

    assert meta["floors_count"] == 4
    assert len(nodes) >= 20
    assert len(edges) >= 20

    # Check that each floor 0, 1, 2, 3 has nodes
    floors = {n.floor for n in nodes}
    assert {0, 1, 2, 3}.issubset(floors)

    # Check that vertical connections exist
    elev_edges = [e for e in edges if e.is_elevator and e.floor_transition]
    stair_edges = [e for e in edges if e.has_stairs and e.floor_transition]
    assert len(elev_edges) >= 3  # G->1, 1->2, 2->3
    assert len(stair_edges) >= 3


def test_obstacle_db_persistence():
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = os.path.join(tmpdir, "test_obstacles.db")
        db = ObstacleDB(db_path=test_db_path)

        # Initial seed check
        initial_reports = db.get_all_reports()
        assert len(initial_reports) >= 2

        # Add new report
        new_obs = ObstacleReport(
            id="TEST-001",
            location_or_edge_id="E_JUNCTION_TO_FET_RAMP",
            obstacle_type=ObstacleType.BLOCKED_RAMP,
            description="Temporary delivery truck blocking ramp access",
            severity=ObstacleSeverity.CRITICAL_BLOCKING,
            timestamp="2026-10-12 12:00:00",
            status=ObstacleStatus.SUBMITTED,
            reported_by_role="Student"
        )
        assert db.add_report(new_obs)

        # Retrieve and verify
        retrieved = db.get_report("TEST-001")
        assert retrieved is not None
        assert retrieved.obstacle_type == ObstacleType.BLOCKED_RAMP
        assert retrieved.is_blocking_for_routing()

        # Update status
        db.update_report_status("TEST-001", ObstacleStatus.VERIFIED, "Confirmed by security")
        verified_obs = db.get_report("TEST-001")
        assert verified_obs.status == ObstacleStatus.VERIFIED
        assert verified_obs.verification_notes == "Confirmed by security"

        # Check blocked target IDs
        blocked_ids = db.get_blocked_target_ids()
        assert "E_JUNCTION_TO_FET_RAMP" in blocked_ids

        # Reopen connection with new instance to verify disk persistence
        db2 = ObstacleDB(db_path=test_db_path)
        persisted_report = db2.get_report("TEST-001")
        assert persisted_report is not None
        assert persisted_report.status == ObstacleStatus.VERIFIED
