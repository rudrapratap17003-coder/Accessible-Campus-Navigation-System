"""
test_report.py — Unit Tests for Campus Data Report Generator
=============================================================
Verifies that generate_campus_report() produces all required audit sections
and correctly separates verified from prototype information.
"""

import unittest
from generate_campus_report import generate_campus_report


class TestCampusReport(unittest.TestCase):
    """Test suite for campus data report generation."""

    def test_report_contains_required_sections(self):
        """The generated report must contain all mandatory headings and disclosures."""
        report = generate_campus_report()

        # Check main header
        self.assertIn("JAIN GLOBAL CAMPUS", report)
        self.assertIn("ACCESSIBILITY DATA REPORT", report)
        self.assertIn("Total Locations:\n  15", report)

        # Check facility categories
        self.assertIn("Academic Facilities:", report)
        self.assertIn("Research Facilities:", report)
        self.assertIn("Student Facilities:", report)
        self.assertIn("Sports Facilities:", report)

        # Check audit classification sections
        self.assertIn("VERIFIED INFORMATION:", report)
        self.assertIn("PROTOTYPE / UNVERIFIED INFORMATION", report)
        self.assertIn("NOT official surveyed architectural measurements", report)
        self.assertIn("NOT GPS geographic coordinates", report)

        # Check specific verified facilities are named
        self.assertIn("Faculty of Engineering & Technology", report)
        self.assertIn("Campus Library", report)
        self.assertIn("International Institute for Aerospace Engineering and Management", report)
        self.assertIn("Sprintoor", report)


if __name__ == "__main__":
    unittest.main()
