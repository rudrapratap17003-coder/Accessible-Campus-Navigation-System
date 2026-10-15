"""
Unit tests for Phase 9: Campus Accessibility Analytics Engine.

Tests:
1. Category aggregation with Pandas.
2. Active vs. resolved reports breakdown.
3. Repeated reports ranking and name resolution.
4. Identification of pathways requiring accessibility verification (unknown surfaces, unmeasured widths).
5. Building data completeness percentages and inspection priority ranking.
6. Calculation of mean and median resolution time (when timestamps exist).
7. Historical date timeline aggregation.
8. Scorecard completeness metrics without invented values.
"""

import pytest
import datetime
import pandas as pd
from campus_navigator.models.core_models import (
    LocationNode,
    PathwayEdge,
    ObstacleReport,
    ObstacleType,
    ObstacleSeverity,
    ObstacleStatus,
    VerificationStatus,
    LocationType,
    SurfaceType
)
from campus_navigator.algorithms.analytics import CampusAnalyticsEngine


@pytest.fixture
def mock_analytics_data():
    """Builds controlled nodes, edges, and obstacle reports for analytical verification."""
    nodes = {
        "N1": LocationNode(id="N1", name="Main Gate", node_type=LocationType.OUTDOOR_ENTRANCE, verification=VerificationStatus.VERIFIED, latitude=12.648, longitude=77.441, is_step_free_accessible=True, door_width_cm=300.0, has_tactile_paving=True),
        "N2": LocationNode(id="N2", name="FET Atrium", node_type=LocationType.BUILDING_ENTRANCE, verification=VerificationStatus.DEMONSTRATION, floor=0, building_id="FET_MAIN", is_step_free_accessible=True, door_width_cm=None, has_tactile_paving=False),
        "N3": LocationNode(id="N3", name="Unlocated Lab", node_type=LocationType.LABORATORY, verification=VerificationStatus.PROVISIONAL, latitude=None, longitude=None, is_step_free_accessible=False, door_width_cm=None, has_tactile_paving=None)
    }

    edges = {
        "E1": PathwayEdge(id="E1", source="N1", target="N2", distance_m=100.0, estimated_time_sec=80.0, verification=VerificationStatus.VERIFIED, is_step_free=True, surface=SurfaceType.PAVED_SMOOTH, width_cm=200.0),
        "E2": PathwayEdge(id="E2", source="N2", target="N3", distance_m=50.0, estimated_time_sec=40.0, verification=VerificationStatus.PROVISIONAL, is_step_free=False, has_stairs=True, surface=SurfaceType.UNKNOWN, width_cm=None)
    }

    reports = [
        ObstacleReport(
            id="R1",
            location_or_edge_id="E1",
            obstacle_type=ObstacleType.BLOCKED_RAMP,
            description="Debris on ramp",
            severity=ObstacleSeverity.HIGH,
            timestamp="2026-10-10T08:00:00+00:00",
            status=ObstacleStatus.RESOLVED,
            resolved_at="2026-10-10T14:00:00+00:00"  # 6.0 hours duration
        ),
        ObstacleReport(
            id="R2",
            location_or_edge_id="E1",
            obstacle_type=ObstacleType.CONSTRUCTION,
            description="Routine paving",
            severity=ObstacleSeverity.MEDIUM,
            timestamp="2026-10-11T09:00:00+00:00",
            status=ObstacleStatus.SUBMITTED
        ),
        ObstacleReport(
            id="R3",
            location_or_edge_id="N2",
            obstacle_type=ObstacleType.ELEVATOR_UNAVAILABLE,
            description="Lift service",
            severity=ObstacleSeverity.CRITICAL_BLOCKING,
            timestamp="2026-10-11T10:00:00+00:00",
            status=ObstacleStatus.VERIFIED
        )
    ]

    return nodes, edges, reports


def test_analytics_reports_by_category(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    df_cat = engine.get_reports_by_category()
    assert len(df_cat) == 3
    assert set(df_cat["Category"]) == {"BLOCKED_RAMP", "CONSTRUCTION", "ELEVATOR_UNAVAILABLE"}
    assert df_cat.loc[df_cat["Category"] == "BLOCKED_RAMP", "Count"].values[0] == 1


def test_analytics_active_vs_resolved(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    df_status = engine.get_active_vs_resolved_status()
    assert len(df_status) == 3
    counts = dict(zip(df_status["Status"], df_status["Count"]))
    assert counts.get("RESOLVED") == 1
    assert counts.get("SUBMITTED") == 1
    assert counts.get("VERIFIED") == 1


def test_analytics_repeated_reports_ranking(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    df_repeat = engine.get_locations_with_repeated_reports()
    assert len(df_repeat) == 2
    # E1 has 2 reports, N2 has 1 report
    top_target = df_repeat.iloc[0]
    assert top_target["Target ID"] == "E1"
    assert top_target["Total Reports"] == 2
    assert "Pathway: Main Gate ↔ FET Atrium" in top_target["Name"]


def test_analytics_pathways_requiring_verification(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    df_audit = engine.get_pathways_requiring_verification()
    # E2 has PROVISIONAL verification, unknown surface, and unmeasured width
    assert len(df_audit) == 1
    row = df_audit.iloc[0]
    assert row["Pathway ID"] == "E2"
    assert "Surface material unknown" in row["Audit Reasons"]
    assert "Door/corridor width unmeasured" in row["Audit Reasons"]


def test_analytics_building_data_completeness(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    df_bldg = engine.get_buildings_data_completeness()
    assert len(df_bldg) >= 2
    bldg_names = list(df_bldg["Building / Zone"])
    assert "FET_MAIN" in bldg_names
    fet_row = df_bldg.loc[df_bldg["Building / Zone"] == "FET_MAIN"].iloc[0]
    # FET_MAIN has 1 demo node (0% verified completeness) -> HIGH priority inspection
    assert fet_row["Verification Completeness (%)"] == 0.0
    assert fet_row["Inspection Priority"] == "HIGH"


def test_analytics_resolution_time_metrics(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    res_metrics = engine.get_resolution_time_metrics()
    assert res_metrics["has_data"] is True
    assert res_metrics["resolved_count_with_timestamps"] == 1
    # 08:00 to 14:00 is 6.0 hours
    assert res_metrics["mean_hours"] == 6.0
    assert res_metrics["median_hours"] == 6.0


def test_analytics_historical_trends(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    df_trends = engine.get_historical_trends_by_date()
    assert len(df_trends) == 2
    date_counts = dict(zip(df_trends["Date"], df_trends["Submissions"]))
    assert date_counts.get("2026-10-10") == 1
    assert date_counts.get("2026-10-11") == 2


def test_analytics_completeness_scorecard(mock_analytics_data):
    nodes, edges, reports = mock_analytics_data
    engine = CampusAnalyticsEngine(nodes, edges, reports)

    scorecard = engine.get_data_completeness_scorecard()
    assert scorecard["total_nodes"] == 3
    assert scorecard["node_verification_pct"] == round(1 / 3 * 100, 1)  # N1 is only verified
    assert scorecard["total_pathways"] == 2
    assert scorecard["pathway_verification_pct"] == 50.0  # E1 is only verified
    assert scorecard["corridor_width_measured_pct"] == 50.0
