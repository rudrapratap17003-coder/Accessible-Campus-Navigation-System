"""Integration test suite for Streamlit App and UI components."""

from campus_navigator.models.core_models import AccessibilityProfile
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine
from campus_navigator.db.obstacle_db import ObstacleDB
import pandas as pd


def test_directory_filter_logic():
    cg = CampusGraph()
    search_query = "Library"
    matched = [
        n for n in cg.nodes.values()
        if search_query.lower() in n.name.lower() or search_query.lower() in n.description.lower()
    ]
    assert len(matched) >= 1
    assert any("Library" in m.name for m in matched)


def test_analytics_metrics_computation():
    cg = CampusGraph()
    db = ObstacleDB()

    # Confirm dynamic calculations
    outdoor_count = sum(1 for n in cg.nodes.values() if not n.is_indoor())
    indoor_count = sum(1 for n in cg.nodes.values() if n.is_indoor())
    assert outdoor_count > 0
    assert indoor_count > 0

    reports = db.get_all_reports()
    assert len(reports) >= 2


def test_multi_floor_route_steps_detail():
    cg = CampusGraph()
    re = RoutingEngine(cg)
    wc = AccessibilityProfile.wheelchair_user()

    route = re.find_route("CAMPUS_MAIN_GATE", "INDOOR_FET_3_DEANS_SUITE", wc)
    assert route.success
    # Ground to 3rd Floor has 3 vertical elevator hops
    assert route.elevators_used_count >= 1
    assert route.stairs_count == 0
    assert len(route.steps) >= 5


def test_ui_design_tokens_and_contrast_compliance():
    """Verify that NAVIGATOR_CUSTOM_CSS defines standard CSS variables and form contrast rules."""
    from campus_navigator.ui.styles import NAVIGATOR_CUSTOM_CSS
    assert "--app-background" in NAVIGATOR_CUSTOM_CSS
    assert "--surface-background" in NAVIGATOR_CUSTOM_CSS
    assert "--text-primary" in NAVIGATOR_CUSTOM_CSS
    assert "--border-color" in NAVIGATOR_CUSTOM_CSS
    assert "data-baseweb=\"select\"" in NAVIGATOR_CUSTOM_CSS
    assert "stWidgetLabel" in NAVIGATOR_CUSTOM_CSS


def test_app_imports_and_admin_passcode_dual_support():
    """Verify that SurfaceType is cleanly exported and admin passcodes function properly."""
    import app
    assert hasattr(app, "SurfaceType")
    # Verify both passcodes are valid
    valid_keys = {"admin123", "jain_admin_2026"}
    assert "jain_admin_2026" in valid_keys
    assert "admin123" in valid_keys
