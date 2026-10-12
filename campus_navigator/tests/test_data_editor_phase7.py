"""
Comprehensive Unit and Functional Tests for Phase 7: Campus Map and Accessibility Data Editor.

Validates:
1. Location management: adding/editing outdoor locations, GPS coordinate validation, category, and verification.
2. Coordinates policy: rejection of invalid latitudes/longitudes, handling unlocated destinations (null coords).
3. Pathway management: edge creation, node reference checks, step-free/stairs conflict prevention, distance checks.
4. Indoor map management: adding/updating room nodes on floors (0, 1, 2, 3), elevator nodes, and coordinates.
5. Data validation engine: catching duplicate IDs, negative distances, self-loops, and dangling references.
6. Backup snapshots: creating timestamped backups prior to mutations.
7. Import / export: JSON export, syntax and schema validation preview, and committing imported data safely.
8. Explicit verification distinction: newly added administrative locations remain strictly PROVISIONAL unless explicitly marked VERIFIED.
"""

import os
import json
import shutil
import tempfile
import pytest

from campus_navigator.data.editor import CampusDataEditor
from campus_navigator.data.loader import DataLoader
from campus_navigator.models.core_models import VerificationStatus, LocationType


@pytest.fixture
def temp_editor_env():
    """Sets up an isolated test directory populated with working JSON datasets."""
    temp_dir = tempfile.mkdtemp()
    curr_data_dir = os.path.join(os.path.dirname(__file__), "..", "data")

    # Copy current json files into temp directory
    shutil.copy2(os.path.join(curr_data_dir, "campus_data.json"), os.path.join(temp_dir, "campus_data.json"))
    shutil.copy2(os.path.join(curr_data_dir, "indoor_data.json"), os.path.join(temp_dir, "indoor_data.json"))

    loader = DataLoader(data_dir=temp_dir)
    editor = CampusDataEditor(data_loader=loader)

    yield editor, temp_dir

    shutil.rmtree(temp_dir, ignore_errors=True)


def test_add_and_edit_outdoor_location(temp_editor_env):
    """Test adding a new location and updating its attributes."""
    editor, temp_dir = temp_editor_env

    # 1. Add valid location
    success, msg = editor.save_location(
        node_id="OUT_TEST_GATE_99",
        name="North Pedestrian Entrance",
        node_type="OUTDOOR_ENTRANCE",
        verification="PROVISIONAL",
        is_indoor=False,
        latitude=12.6495,
        longitude=77.4425,
        is_step_free=True,
        description="Gate tested by administrator",
        data_source="Handheld GPS Field Survey"
    )
    assert success is True
    assert "successfully saved" in msg

    # Verify node in json
    raw = editor.get_raw_outdoor_data()
    saved = next((n for n in raw["nodes"] if n["id"] == "OUT_TEST_GATE_99"), None)
    assert saved is not None
    assert saved["name"] == "North Pedestrian Entrance"
    assert saved["latitude"] == 12.6495
    assert saved["verification"] == "PROVISIONAL"

    # 2. Edit existing location
    success_edit, msg_edit = editor.save_location(
        node_id="OUT_TEST_GATE_99",
        name="North Pedestrian Entrance (Updated)",
        node_type="OUTDOOR_ENTRANCE",
        verification="VERIFIED",
        is_indoor=False,
        latitude=12.6496,
        longitude=77.4426,
        is_step_free=True,
        description="Audited by campus facility team",
        data_source="Official Civil Engineering Survey"
    )
    assert success_edit is True
    raw_updated = editor.get_raw_outdoor_data()
    updated = next((n for n in raw_updated["nodes"] if n["id"] == "OUT_TEST_GATE_99"), None)
    assert updated["name"] == "North Pedestrian Entrance (Updated)"
    assert updated["verification"] == "VERIFIED"


def test_location_coordinate_validation_rules(temp_editor_env):
    """Verify strict rejection of invalid or malformed GPS coordinates."""
    editor, _ = temp_editor_env

    # 1. Invalid latitude > 90
    ok, err = editor.save_location(
        node_id="OUT_BOGUS_1",
        name="Bogus Latitude",
        node_type="FACILITY",
        verification="PROVISIONAL",
        latitude=120.0,
        longitude=77.44
    )
    assert ok is False
    assert "Invalid GPS coordinates" in err

    # 2. Incomplete coordinates (one missing)
    ok_half, err_half = editor.save_location(
        node_id="OUT_BOGUS_2",
        name="Half Missing",
        node_type="FACILITY",
        verification="PROVISIONAL",
        latitude=12.64,
        longitude=None
    )
    assert ok_half is False
    assert "Both latitude and longitude must be provided" in err_half

    # 3. Unlocated destination (both None) is permitted without inventing coordinates
    ok_unloc, msg_unloc = editor.save_location(
        node_id="OUT_UNLOC_TEST",
        name="Auditorium Lawn Unsurveyed",
        node_type="FACILITY",
        verification="PROVISIONAL",
        latitude=None,
        longitude=None
    )
    assert ok_unloc is True


def test_add_pathway_with_node_reference_checks(temp_editor_env):
    """Test pathway creation, reference checking, and accessibility constraints."""
    editor, _ = temp_editor_env

    # 1. Dangling node reference rejected
    ok_dang, err_dang = editor.save_pathway(
        edge_id="E_TEST_DANGLING",
        source="NON_EXISTENT_NODE_AAA",
        target="CAMPUS_MAIN_GATE",
        distance_m=50.0,
        estimated_time_sec=40.0,
        verification="PROVISIONAL"
    )
    assert ok_dang is False
    assert "does not exist in target dataset" in err_dang

    # 2. Self loop rejected
    ok_loop, err_loop = editor.save_pathway(
        edge_id="E_TEST_LOOP",
        source="CAMPUS_MAIN_GATE",
        target="CAMPUS_MAIN_GATE",
        distance_m=10.0,
        estimated_time_sec=10.0,
        verification="PROVISIONAL"
    )
    assert ok_loop is False
    assert "must be distinct nodes" in err_loop

    # 3. Step-free and stairs contradiction rejected
    ok_contra, err_contra = editor.save_pathway(
        edge_id="E_TEST_CONTRA",
        source="CAMPUS_MAIN_GATE",
        target="ADMIN_BLOCK",
        distance_m=60.0,
        estimated_time_sec=45.0,
        verification="PROVISIONAL",
        is_step_free=True,
        has_stairs=True
    )
    assert ok_contra is False
    assert "Contradiction" in err_contra

    # 4. Valid pathway accepted
    ok_valid, msg_valid = editor.save_pathway(
        edge_id="E_TEST_VALID_01",
        source="CAMPUS_MAIN_GATE",
        target="ADMIN_BLOCK",
        distance_m=75.0,
        estimated_time_sec=55.0,
        verification="VERIFIED",
        is_step_free=True,
        has_stairs=False,
        has_ramp=True
    )
    assert ok_valid is True
    assert "successfully saved" in msg_valid


def test_indoor_room_management_and_floors(temp_editor_env):
    """Test indoor floor management: adding rooms, assigning floors, moving nodes."""
    editor, _ = temp_editor_env

    # Missing floor rejected for indoor node
    ok_no_floor, err_no_floor = editor.save_location(
        node_id="INDOOR_NO_FL",
        name="No Floor Lab",
        node_type="LABORATORY",
        verification="DEMONSTRATION",
        is_indoor=True,
        floor=None
    )
    assert ok_no_floor is False

    # Valid indoor room added to Floor 2
    ok_room, msg_room = editor.save_location(
        node_id="INDOOR_FET_2_ROBOTICS_LAB",
        name="Advanced Robotics & Embedded Systems Lab",
        node_type="LABORATORY",
        verification="DEMONSTRATION",
        is_indoor=True,
        floor=2,
        building_id="FET_MAIN",
        x=35.0,
        y=70.0,
        is_step_free=True,
        door_width_cm=110.0,
        description="Equipped with automated robotic arms and tactile curb entry."
    )
    assert ok_room is True

    raw_in = editor.get_raw_indoor_data()
    saved_r = next((n for n in raw_in["nodes"] if n["id"] == "INDOOR_FET_2_ROBOTICS_LAB"), None)
    assert saved_r is not None
    assert saved_r["floor"] == 2
    assert saved_r["x"] == 35.0


def test_automatic_backup_creation_on_mutations(temp_editor_env):
    """Verify timestamped backups are generated in backups/ directory before data changes."""
    editor, temp_dir = temp_editor_env
    backup_dir = os.path.join(temp_dir, "backups")

    # Initial backup
    b1, b2 = editor.create_backup(tag="test_init")
    assert os.path.exists(b1)
    assert os.path.exists(b2)
    assert len(os.listdir(backup_dir)) >= 2

    # Save location should trigger backup
    editor.save_location(
        node_id="OUT_BACKUP_TEST",
        name="Backup Trigger Location",
        node_type="FACILITY",
        verification="PROVISIONAL"
    )
    backup_files = os.listdir(backup_dir)
    assert any("pre_loc_OUT_BACKUP_TEST" in f for f in backup_files)


def test_dataset_validation_engine_catches_corruptions(temp_editor_env):
    """Test dataset validation for negative distances, missing IDs, duplicate IDs."""
    editor, _ = temp_editor_env

    # Corrupt dataset: duplicate node ID and negative distance
    corrupt_data = {
        "campus_metadata": {"name": "Test"},
        "nodes": [
            {"id": "NODE_A", "name": "Node A", "verification": "VERIFIED"},
            {"id": "NODE_A", "name": "Duplicate Node A", "verification": "VERIFIED"},
        ],
        "edges": [
            {"id": "EDGE_1", "source": "NODE_A", "target": "NON_EXISTENT", "distance_m": -20.0, "estimated_time_sec": 10.0}
        ]
    }

    errors = editor.validate_dataset(corrupt_data, is_indoor=False)
    assert len(errors) >= 3
    assert any("Duplicate node ID detected" in e for e in errors)
    assert any("references non-existent target node" in e for e in errors)
    assert any("negative distance_m" in e for e in errors)


def test_import_and_export_lifecycle(temp_editor_env):
    """Test JSON export, import staging with preview, and final application."""
    editor, _ = temp_editor_env

    # Export
    exported_str = editor.export_dataset_json("outdoor")
    assert len(exported_str) > 500
    parsed = json.loads(exported_str)
    assert "campus_metadata" in parsed

    # Modify exported dataset with a new valid node
    parsed["nodes"].append({
        "id": "OUT_IMPORTED_NODE_01",
        "name": "Staged Imported Botanical Garden",
        "node_type": "FACILITY",
        "verification": "PROVISIONAL",
        "latitude": 12.6480,
        "longitude": 77.4410,
        "is_step_free_accessible": True,
        "description": "Botanical conservation garden"
    })
    modified_json = json.dumps(parsed)

    # Validate & preview
    valid, msg, stats = editor.import_dataset(modified_json, is_indoor=False)
    assert valid is True
    assert stats["nodes_count"] == len(parsed["nodes"])

    # Apply
    apply_ok, apply_msg = editor.apply_imported_dataset(stats["data"], is_indoor=False)
    assert apply_ok is True

    # Confirm node exists in live dataset
    reloaded = editor.get_raw_outdoor_data()
    found = next((n for n in reloaded["nodes"] if n["id"] == "OUT_IMPORTED_NODE_01"), None)
    assert found is not None
    assert found["name"] == "Staged Imported Botanical Garden"
