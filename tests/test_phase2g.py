"""
test_phase2g.py — Unit Tests for Accessibility-Aware Representation & Confidence Rules
========================================================================================
Verifies:
    1. Every connection contains accessible, stairs, ramp, elevator, accessibility_confidence, and accessibility_notes.
    2. accessibility_confidence adheres to the taxonomy: high, medium, low.
    3. UI badge helper get_accessibility_badge() correctly maps to:
       - ✓ Verified accessible
       - ⚠ Accessibility information needs verification
       - ✗ Known inaccessible
    4. Crucial rule: Low-confidence data is NEVER classified as verified accessible.
"""

import copy
import unittest

from services.data_manager import load_campus_data, validate_campus_data
from core.accessibility import (
    AccessibilityConfidence,
    AccessibilityBadge,
    get_accessibility_badge,
)


class TestAccessibilityAwareModel(unittest.TestCase):
    """Test suite for Phase 2G accessibility fields, confidence rules, and UI badges."""

    @classmethod
    def setUpClass(cls):
        """Load campus data."""
        cls.campus_data = load_campus_data()

    def test_production_connections_have_phase2g_fields(self):
        """All 25 connections must have the full Phase 2G accessibility fields."""
        required_flags = ["accessible", "stairs", "ramp", "elevator", "accessibility_confidence", "accessibility_notes"]
        for idx, conn in enumerate(self.campus_data["connections"], 1):
            for field in required_flags:
                self.assertIn(
                    field, conn,
                    f"Connection #{idx} ({conn.get('source')} -> {conn.get('destination')}) missing {field}"
                )
                self.assertTrue(
                    conn[field] is not None and str(conn[field]).strip() != "",
                    f"Connection #{idx} has empty field: {field}"
                )

    def test_confidence_values_are_valid(self):
        """All connection confidence levels must be 'high', 'medium', or 'low'."""
        for conn in self.campus_data["connections"]:
            conf = conn["accessibility_confidence"]
            self.assertIn(conf, AccessibilityConfidence.ALL)

    def test_invalid_confidence_fails_validation(self):
        """validate_campus_data must reject invalid confidence values."""
        bad_data = copy.deepcopy(self.campus_data)
        bad_data["connections"][0]["accessibility_confidence"] = "very_high"
        result = validate_campus_data(bad_data, verbose=False)
        self.assertFalse(result["is_valid"])
        self.assertTrue(any("invalid accessibility_confidence" in e for e in result["errors"]))

    def test_ui_badge_verified_accessible(self):
        """High confidence + accessible==True produces '✓ Verified accessible'."""
        edge = {
            "accessible": True,
            "accessibility_confidence": AccessibilityConfidence.HIGH,
            "stairs": False,
            "ramp": True,
        }
        badge, label = get_accessibility_badge(edge)
        self.assertEqual(badge, AccessibilityBadge.VERIFIED_ACCESSIBLE)
        self.assertIn("Verified accessible", label)

    def test_ui_badge_needs_verification_on_low_confidence(self):
        """Low confidence MUST NEVER be presented as verified, even if marked accessible."""
        edge = {
            "accessible": True,
            "accessibility_confidence": AccessibilityConfidence.LOW,
            "stairs": False,
            "ramp": True,
        }
        badge, label = get_accessibility_badge(edge)
        # MUST NOT be VERIFIED_ACCESSIBLE because confidence is LOW
        self.assertEqual(badge, AccessibilityBadge.NEEDS_VERIFICATION)
        self.assertIn("needs verification", label)

    def test_ui_badge_needs_verification_on_unknown(self):
        """Unknown accessibility produces '⚠ Accessibility information needs verification'."""
        edge = {
            "accessible": "unknown",
            "accessibility_confidence": AccessibilityConfidence.LOW,
            "stairs": "unknown",
            "ramp": "unknown",
        }
        badge, label = get_accessibility_badge(edge)
        self.assertEqual(badge, AccessibilityBadge.NEEDS_VERIFICATION)
        self.assertIn("needs verification", label)

    def test_ui_badge_known_inaccessible(self):
        """Explicitly false accessibility produces '✗ Known inaccessible'."""
        edge_blocked = {
            "accessible": False,
            "accessibility_confidence": AccessibilityConfidence.HIGH,
        }
        badge, label = get_accessibility_badge(edge_blocked)
        self.assertEqual(badge, AccessibilityBadge.KNOWN_INACCESSIBLE)
        self.assertIn("inaccessible", label)

        edge_stairs_only = {
            "accessible": "unknown",
            "stairs": True,
            "ramp": False,
            "accessibility_confidence": AccessibilityConfidence.HIGH,
        }
        badge2, label2 = get_accessibility_badge(edge_stairs_only)
        self.assertEqual(badge2, AccessibilityBadge.KNOWN_INACCESSIBLE)
        self.assertIn("inaccessible", label2)


if __name__ == "__main__":
    unittest.main()
