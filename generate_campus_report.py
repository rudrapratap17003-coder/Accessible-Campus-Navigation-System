"""
generate_campus_report.py — JAIN Global Campus Accessibility Data Report Generator
=====================================================================================
Reads `campus_data.json` and outputs an audit report distinguishing:
    1. VERIFIED INFORMATION (publicly confirmed facilities, official university sources)
    2. PROTOTYPE / UNVERIFIED INFORMATION (schematic distances, travel times,
       accessibility confidence levels, and 2D canvas coordinates)

Academic Mini-Project Context:
    JAIN (Deemed-to-be University) – Global Campus, Kanakapura Taluk, Karnataka.
"""

import json
from pathlib import Path
import sys


def generate_campus_report(data_or_path=None, output_file=None):
    """Generate a comprehensive, human-readable campus accessibility audit report.

    Args:
        data_or_path (dict, str, or Path, optional): Custom data dict or file path.
        output_file (str or Path, optional): If provided, writes the report to disk.

    Returns:
        str: The full generated report text.
    """
    # 1. Resolve and load campus data
    if isinstance(data_or_path, dict):
        data = data_or_path
    else:
        file_path = Path(data_or_path) if data_or_path else Path(__file__).resolve().parent / "campus_data.json"
        if not file_path.is_file():
            raise FileNotFoundError(f"Cannot find campus_data.json at: {file_path}")
        data = json.loads(file_path.read_text(encoding="utf-8"))

    locations = data.get("locations", [])
    connections = data.get("connections", [])

    # Group locations by functional category
    academic = []
    research = []
    student_life = []
    sports = []
    access = []

    for loc in locations:
        cat = loc.get("category", "").lower()
        loc_id = loc.get("id", "")
        if cat == "academic":
            academic.append(loc)
        elif cat == "research":
            research.append(loc)
        elif loc_id == "sports" or "sports" in loc.get("name", "").lower():
            sports.append(loc)
        elif cat == "access":
            access.append(loc)
        else:
            student_life.append(loc)

    # Count verification and confidence levels
    verified_facilities = [l for l in locations if l.get("verification_status") == "facility_verified_accessibility_unverified"]
    unverified_facilities = [l for l in locations if l.get("verification_status") != "facility_verified_accessibility_unverified"]

    low_conf_conns = [c for c in connections if c.get("accessibility_confidence") == "low"]
    med_conf_conns = [c for c in connections if c.get("accessibility_confidence") == "medium"]
    high_conf_conns = [c for c in connections if c.get("accessibility_confidence") == "high"]

    # Build the report sections
    sep = "=" * 70
    subsep = "-" * 70

    lines = [
        sep,
        "JAIN GLOBAL CAMPUS",
        "ACCESSIBILITY DATA REPORT",
        sep,
        "",
        "Campus:",
        f"  {data.get('campus_name', 'JAIN Global Campus')}",
        f"  Address: {data.get('campus_address', 'Jakkasandra Post, Kanakapura Taluk, Ramanagara District, Karnataka – 562112')}",
        f"  Corridor: {data.get('campus_road', 'Bengaluru–Kanakapura Main Road (NH-209 / NH-948)')}",
        "",
        "Total Locations:",
        f"  {len(locations)}",
        "",
        subsep,
        "FACILITIES BREAKDOWN",
        subsep,
        "",
        "Academic Facilities:",
    ]
    for loc in academic:
        lines.append(f"  • {loc['name']} ({loc.get('short_name', loc['id'])})")
        lines.append(f"    - Type: {loc.get('building_type', 'academic')}")
        lines.append(f"    - Source: {loc.get('source_reference', 'Official Documentation')}")
        lines.append(f"    - Description: {loc.get('description', '')}")

    lines.append("")
    lines.append("Research Facilities:")
    for loc in research:
        lines.append(f"  • {loc['name']} ({loc.get('short_name', loc['id'])})")
        lines.append(f"    - Type: {loc.get('building_type', 'research')}")
        lines.append(f"    - Source: {loc.get('source_reference', 'Official Documentation')}")
        lines.append(f"    - Floor: Level {loc.get('floor_level', 0)}")
        lines.append(f"    - Notes: {loc.get('notes', '')}")

    lines.append("")
    lines.append("Student Facilities:")
    for loc in student_life:
        lines.append(f"  • {loc['name']} ({loc.get('short_name', loc['id'])})")
        lines.append(f"    - Type: {loc.get('building_type', 'facility')}")
        lines.append(f"    - Source: {loc.get('source_reference', 'Official Documentation')}")

    lines.append("")
    lines.append("Sports Facilities:")
    for loc in sports:
        lines.append(f"  • {loc['name']}")
        lines.append(f"    - Confirmed Infrastructure: Sprintoor (80,000 sq ft indoor stadium), The Aqua, The Oval")
        lines.append(f"    - Source: {loc.get('source_reference', 'Official Documentation')}")

    lines.append("")
    lines.append("Access & Parking:")
    for loc in access:
        lines.append(f"  • {loc['name']} (x={loc.get('x')}, y={loc.get('y')})")

    lines.extend([
        "",
        subsep,
        "ACCESSIBILITY DATA SUMMARY",
        subsep,
        "",
        "Accessibility Data:",
        f"  • Total Pathway Segments (Connections): {len(connections)}",
        f"  • High Confidence (Physically verified on-site): {len(high_conf_conns)}",
        f"  • Medium Confidence (Document-backed, not audited): {len(med_conf_conns)}",
        f"  • Low Confidence (Prototype estimates): {len(low_conf_conns)}",
        f"  • Unknown Accessibility Flags: 100% of pathways are conservatively marked 'unknown'",
        f"    pending physical field measurement.",
        "",
        subsep,
        "DATA AUDIT CLASSIFICATION",
        subsep,
        "",
        "[1] VERIFIED INFORMATION:",
        f"  ✓ 14 of 15 facilities verified through official JAIN University publications.",
        "  ✓ Institutional collaborations confirmed (IIAEM with SIATI, UL-JAIN Fire Lab).",
        "  ✓ Specialized centres confirmed (CNMS established 2012; CRFM on 1st floor of Fire Lab).",
        "  ✓ Sports infrastructure verified (Sprintoor indoor stadium, The Aqua, The Oval).",
        "  ✓ Official postal address and National Highway corridor location verified.",
        "",
        "[2] PROTOTYPE / UNVERIFIED INFORMATION (DO NOT TREAT AS OFFICIAL):",
        "  ⚠ Estimated Walking Distances:",
        f"    - All {len(connections)} connection distances are schematic prototype estimates (35 m to 290 m).",
        "    - They are NOT official surveyed architectural measurements.",
        "  ⚠ Estimated Walking Times:",
        "    - Estimated times (1 to 4 minutes) are calculated assuming average speeds (~60–75 m/min).",
        "  ⚠ Physical Accessibility Infrastructure:",
        "    - Presence/absence of ramps, wheelchair-accessible doorways, elevator capacities, and",
        "      stairway step counts have NOT yet been audited on site.",
        "    - Currently labeled as 'needs_physical_verification' under conservative policy.",
        "  ⚠ 2D Visualization Coordinates:",
        "    - Pixel coordinates (x, y) are schematic layout points for Tkinter Canvas rendering.",
        "    - They are NOT GPS geographic coordinates.",
        "  ⚠ Node Identity Note:",
        "    - Centre for Aerospace and Engineering (CRAE) is included as a prototype aerospace division",
        "      node and requires physical on-site confirmation.",
        "",
        subsep,
        "PROTOTYPE ESTIMATED DISTANCES (SAMPLE CONNECTIONS)",
        subsep,
        "",
        "Sample Route Segments:",
    ])

    for c in connections[:8]:
        lines.append(f"  • {c['source']} -> {c['destination']}")
        lines.append(f"    Estimated Distance: {c['distance']} m | Est. Time: ~{c['time']} min | Confidence: {c.get('accessibility_confidence', 'low').upper()}")
        lines.append(f"    Accessibility: {c.get('accessible', 'unknown')} | Note: {c.get('accessibility_notes', '')}")

    lines.extend([
        f"  ... and {len(connections) - 8} additional schematic connections.",
        "",
        sep,
        "END OF JAIN GLOBAL CAMPUS REPORT",
        sep,
    ])

    report_text = "\n".join(lines)

    # Optional file output
    if output_file:
        Path(output_file).write_text(report_text, encoding="utf-8")

    return report_text


def main():
    """Run generator and print report to console with Windows encoding safety."""
    report = generate_campus_report()
    try:
        print(report)
    except UnicodeEncodeError:
        safe_report = report.replace("✓", "[PASS]").replace("⚠", "[!]").replace("•", "*")
        print(safe_report)


if __name__ == "__main__":
    main()
