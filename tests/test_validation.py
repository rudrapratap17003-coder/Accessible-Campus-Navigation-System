"""
test_validation.py — Unit Tests for Campus Data Validation Rules
==================================================================
Tests the 12 validation constraints implemented in validate_campus_data():
    1. Unique node IDs
    2. Node names
    3. Edge references existing nodes
    4. Positive distances
    5. Positive times
    6. Existing numeric coordinates
    7. Valid accessibility values (true, false, unknown)
    8. verification_status present
    9. data_source present
    10. No duplicate edges
    11. No self-loops
    12. All required campus locations present
"""

import copy
import unittest

from services.data_manager import (
    load_campus_data,
    validate_campus_data,
    REQUIRED_CAMPUS_LOCATIONS,
)


class TestCampusDataValidation(unittest.TestCase):
    """Test suite verifying all 12 validation constraints."""

    @classmethod
    def setUpClass(cls):
        """Load baseline valid campus data for mutation testing."""
        cls.valid_data = load_campus_data()

    def test_baseline_campus_data_is_valid(self):
        """The production campus_data.json must pass all validation rules."""
        result = validate_campus_data(self.valid_data, verbose=False)
        self.assertTrue(result["is_valid"], f"Validation failed: {result['errors']}")
        self.assertEqual(result["location_count"], 15)
        self.assertEqual(result["connection_count"], 25)
        self.assertIn("STATUS:\nVALID", result["report"])

    def test_duplicate_node_id_fails(self):
        """Rule 1: Duplicate location IDs must be caught."""
        bad_data = copy.deepcopy(self.valid_data)
        bad_data["locations"][1]["id"] = bad_data["locations"][0]["id"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Duplicate location id" in e for e in result["errors"]))

    def test_missing_node_name_fails(self):
        """Rule 2: Location missing a name must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        del bad_data["locations"][0]["name"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("missing a 'name'" in e for e in result["errors"]))

    def test_invalid_edge_endpoint_fails(self):
        """Rule 3: Connection referencing a non-existent node must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        bad_data["connections"][0]["destination"] = "Non Existent Building"
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("references non-existent destination" in e for e in result["errors"]))

    def test_non_positive_distance_fails(self):
        """Rule 4: Zero or negative distances must be flagged."""
        bad_data = copy.deepcopy(self.valid_data)
        bad_data["connections"][0]["distance"] = 0
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("non-positive distance" in e for e in result["errors"]))

    def test_non_positive_time_fails(self):
        """Rule 5: Zero or negative travel times must be flagged."""
        bad_data = copy.deepcopy(self.valid_data)
        bad_data["connections"][0]["time"] = -2
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("non-positive time" in e for e in result["errors"]))

    def test_missing_coordinates_fails(self):
        """Rule 6: Locations missing coordinates must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        del bad_data["locations"][0]["x"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("missing 'x' or 'y'" in e for e in result["errors"]))

    def test_invalid_accessibility_value_fails(self):
        """Rule 7: Accessibility values other than true/false/unknown must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        bad_data["connections"][0]["accessible"] = "maybe"
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("invalid 'accessible'" in e for e in result["errors"]))

    def test_missing_verification_status_fails(self):
        """Rule 8: Missing verification_status must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        del bad_data["connections"][0]["verification_status"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("missing 'verification_status'" in e for e in result["errors"]))

    def test_missing_data_source_fails(self):
        """Rule 9: Missing data_source must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        del bad_data["locations"][0]["data_source"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("missing 'data_source'" in e for e in result["errors"]))

    def test_duplicate_connection_fails(self):
        """Rule 10: Duplicate connections (even reversed) must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        # Duplicate the first connection
        dup = copy.deepcopy(bad_data["connections"][0])
        dup["source"], dup["destination"] = dup["destination"], dup["source"]
        bad_data["connections"].append(dup)
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Duplicate connection detected" in e for e in result["errors"]))

    def test_self_loop_connection_fails(self):
        """Rule 11: A self-loop connection must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        bad_data["connections"][0]["destination"] = bad_data["connections"][0]["source"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("has a self-loop" in e for e in result["errors"]))

    def test_missing_required_location_fails(self):
        """Rule 12: Missing any of the 15 required locations must fail."""
        bad_data = copy.deepcopy(self.valid_data)
        # Remove Auditorium
        bad_data["locations"] = [l for l in bad_data["locations"] if l["name"] != "Auditorium"]
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("Missing required campus location" in e for e in result["errors"]))


if __name__ == "__main__":
    unittest.main()
