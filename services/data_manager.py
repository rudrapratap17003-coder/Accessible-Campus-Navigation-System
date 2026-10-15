"""
data_manager.py — Campus Data Loader, Validation & Graph Builder Service
==========================================================================
Handles:
    - Reading and parsing `campus_data.json`
    - Validating schema constraints, accessibility metadata, and graph integrity
    - Constructing the `CampusGraph` data structure for navigation algorithms

Learning Objectives:
    - File I/O using pathlib.Path and json serialization
    - Rigorous data validation and diagnostic reporting
    - Defensive programming and cross-platform terminal compatibility
"""

import json
from pathlib import Path
import sys

from core.graph import CampusGraph


# 15 Publicly Verified Facilities at JAIN Global Campus (Phase 2A / 2C Specification)
REQUIRED_CAMPUS_LOCATIONS = [
    "Main Campus Entrance",
    "Faculty of Engineering & Technology",
    "Campus Library",
    "International Institute for Aerospace Engineering and Management (IIAEM)",
    "Centre for Nano and Material Sciences (CNMS)",
    "Centre for Aerospace and Engineering (CRAE)",
    "Fire and Combustion Research Center / Fire Lab",
    "Centre for Research in Functional Materials (CRFM)",
    "Centre for Disaster Mitigation",
    "Auditorium",
    "Multi-Cuisine Cafeteria",
    "Hostel / Residential Area",
    "Medical Center",
    "Sports Facilities",
    "Parking / Visitor Area",
]

# Valid accessibility states permitted in the prototype data model
ALLOWED_ACCESSIBILITY_VALUES = {True, False, "true", "false", "unknown"}

# Phase 2F Source and Verification Taxonomy
ALLOWED_DATA_SOURCES = {
    "official_jain_website",
    "public_reference",
    "prototype_estimate",
}

ALLOWED_VERIFICATION_STATUSES = {
    "facility_verified_accessibility_unverified",
    "needs_physical_verification",
    "physically_verified",
    "prototype_estimate",
}

# Phase 2G Accessibility Confidence Levels
ALLOWED_CONFIDENCE_LEVELS = {
    "high",
    "medium",
    "low",
}


class DataManagerError(Exception):
    """Custom exception raised when campus data cannot be loaded, parsed, or validated."""
    pass


def get_default_data_path():
    """Resolve the default path to campus_data.json relative to the project root."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "campus_data.json"


def load_campus_data(file_path=None):
    """Read campus JSON file from disk and return the raw dictionary.

    Args:
        file_path (str or Path, optional): Custom file path to load from.

    Returns:
        dict: Parsed campus JSON data.

    Raises:
        DataManagerError: If file not found or contains invalid JSON.
    """
    path = Path(file_path) if file_path else get_default_data_path()

    if not path.is_file():
        raise DataManagerError(f"Campus data file not found at: {path}")

    try:
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        return data
    except json.JSONDecodeError as err:
        raise DataManagerError(f"Malformed JSON syntax in campus data: {err}")
    except OSError as err:
        raise DataManagerError(f"Error accessing campus data file: {err}")


def _normalize_accessibility_val(val):
    """Check if an accessibility value is one of: True, False, or 'unknown'."""
    if isinstance(val, bool):
        return True
    if isinstance(val, str) and val.strip().lower() in ("true", "false", "unknown"):
        return True
    return False


def _get_symbol(unicode_sym, ascii_fallback):
    """Return a unicode symbol if supported by stdout, else an ASCII fallback."""
    enc = getattr(sys.stdout, "encoding", "utf-8") or "utf-8"
    try:
        unicode_sym.encode(enc)
        return unicode_sym
    except Exception:
        return ascii_fallback


def validate_campus_data(data_or_path=None, verbose=True):
    """Validate the campus data model against all 12 architectural constraints.

    Verification Rules:
        1. Every node has a unique ID.
        2. Every node has a name.
        3. Every edge references an existing node.
        4. Distances are positive (> 0).
        5. Times are positive (> 0).
        6. Coordinates exist (x and y numeric).
        7. Accessibility values are one of: true, false, unknown.
        8. verification_status exists on all nodes and edges.
        9. data_source exists on all nodes and edges.
        10. No duplicate edges exist (undirected pair).
        11. No self-loops exist (source != destination).
        12. All required campus locations exist.

    Args:
        data_or_path (dict, str, or Path, optional): Parsed data or path to JSON file.
        verbose (bool): If True, prints a formatted validation report to stdout.

    Returns:
        dict: Validation results with keys:
            - is_valid (bool)
            - errors (list of str)
            - warnings (list of str)
            - report (str)
            - location_count (int)
            - connection_count (int)
    """
    # 1. Load data if needed
    if isinstance(data_or_path, dict):
        data = data_or_path
    else:
        try:
            data = load_campus_data(data_or_path)
        except DataManagerError as err:
            report = f"JAIN GLOBAL CAMPUS DATA VALIDATION\n----------------------------------\n\nERROR:\n{err}\n\nSTATUS:\nINVALID"
            if verbose:
                print(report)
            return {
                "is_valid": False,
                "errors": [str(err)],
                "warnings": [],
                "report": report,
                "location_count": 0,
                "connection_count": 0,
            }

    errors = []
    warnings = []

    locations = data.get("locations", [])
    # Support both "connections" (Phase 2C standard) and legacy "edges"
    connections = data.get("connections", data.get("edges", []))

    # --- Rule 1 & 2: Node IDs and Names ---
    node_ids = set()
    node_names = set()
    node_lookup = {}  # maps both id and name -> location dict

    for idx, loc in enumerate(locations, 1):
        loc_id = loc.get("id")
        loc_name = loc.get("name")

        # Rule 1: Every node has a unique ID
        if not loc_id:
            errors.append(f"Location #{idx} is missing an 'id'.")
        elif loc_id in node_ids:
            errors.append(f"Duplicate location id found: '{loc_id}'.")
        else:
            node_ids.add(loc_id)

        # Rule 2: Every node has a name
        if not loc_name:
            errors.append(f"Location #{idx} (id='{loc_id}') is missing a 'name'.")
        elif loc_name in node_names:
            errors.append(f"Duplicate location name found: '{loc_name}'.")
        else:
            node_names.add(loc_name)

        if loc_id and loc_name:
            node_lookup[loc_id] = loc
            node_lookup[loc_name] = loc

        # Rule 6: Coordinates exist (x and y)
        x = loc.get("x", loc.get("map_x"))
        y = loc.get("y", loc.get("map_y"))
        if x is None or y is None:
            errors.append(f"Location '{loc_name or loc_id}' is missing 'x' or 'y' coordinates.")
        elif not isinstance(x, (int, float)) or not isinstance(y, (int, float)):
            errors.append(f"Location '{loc_name or loc_id}' coordinates must be numeric (got x={x}, y={y}).")

        # Rule 7: Accessibility values on node (true, false, unknown)
        for attr in ("accessible_entrance", "has_ramp", "has_elevator", "has_stairs"):
            val = loc.get(attr)
            if val is not None and not _normalize_accessibility_val(val):
                errors.append(f"Location '{loc_name or loc_id}' has invalid '{attr}': {val}. Expected true, false, or unknown.")

        # Rule 8: verification_status exists on node and is valid
        v_status = loc.get("verification_status")
        if not v_status:
            errors.append(f"Location '{loc_name or loc_id}' is missing 'verification_status'.")
        elif v_status not in ALLOWED_VERIFICATION_STATUSES:
            errors.append(f"Location '{loc_name or loc_id}' has unrecognized verification_status: '{v_status}'.")

        # Rule 9: data_source and source_reference exist on node and are valid
        d_source = loc.get("data_source")
        if not d_source:
            errors.append(f"Location '{loc_name or loc_id}' is missing 'data_source'.")
        elif d_source not in ALLOWED_DATA_SOURCES:
            errors.append(f"Location '{loc_name or loc_id}' has unrecognized data_source: '{d_source}'.")

        s_ref = loc.get("source_reference")
        if not s_ref:
            errors.append(f"Location '{loc_name or loc_id}' is missing 'source_reference'.")

    # --- Rule 12: All required campus locations exist ---
    missing_required = [req for req in REQUIRED_CAMPUS_LOCATIONS if req not in node_names]
    if missing_required:
        errors.append(f"Missing required campus location(s): {', '.join(missing_required)}")

    # --- Connections / Edges Verification ---
    seen_edges = set()
    connected_nodes = set()
    unverified_connections = 0

    for idx, conn in enumerate(connections, 1):
        u = conn.get("source", conn.get("from"))
        v = conn.get("destination", conn.get("to"))
        dist = conn.get("distance", conn.get("distance_meters"))
        travel_time = conn.get("time")

        # Rule 3: Every edge references an existing node
        if not u or u not in node_lookup:
            errors.append(f"Connection #{idx} references non-existent source: '{u}'.")
        else:
            connected_nodes.add(node_lookup[u]["name"])

        if not v or v not in node_lookup:
            errors.append(f"Connection #{idx} references non-existent destination: '{v}'.")
        else:
            connected_nodes.add(node_lookup[v]["name"])

        # Rule 11: No self-loop
        if u and v and (u == v or (u in node_lookup and v in node_lookup and node_lookup[u]["name"] == node_lookup[v]["name"])):
            errors.append(f"Connection #{idx} has a self-loop: '{u}' -> '{v}'.")

        # Rule 10: No duplicate edges (undirected check)
        if u in node_lookup and v in node_lookup:
            u_canon = node_lookup[u]["name"]
            v_canon = node_lookup[v]["name"]
            edge_pair = tuple(sorted([u_canon, v_canon]))
            if edge_pair in seen_edges:
                errors.append(f"Duplicate connection detected between '{u_canon}' and '{v_canon}'.")
            seen_edges.add(edge_pair)

        # Rule 4: Distances are positive
        if dist is None:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') is missing distance.")
        elif not isinstance(dist, (int, float)) or dist <= 0:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') has non-positive distance: {dist}.")

        # Rule 5: Times are positive
        if travel_time is not None:
            if not isinstance(travel_time, (int, float)) or travel_time <= 0:
                errors.append(f"Connection #{idx} ('{u}' -> '{v}') has non-positive time: {travel_time}.")

        # Rule 7: Accessibility values on edge (true, false, unknown)
        for attr in ("accessible", "stairs", "ramp", "elevator", "has_stairs", "has_ramp", "has_elevator"):
            if attr in conn:
                val = conn[attr]
                if not _normalize_accessibility_val(val):
                    errors.append(f"Connection #{idx} has invalid '{attr}': {val}. Expected true, false, or unknown.")

        # Rule 8: verification_status exists on connection and is valid
        v_status = conn.get("verification_status")
        if not v_status:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') is missing 'verification_status'.")
        elif v_status not in ALLOWED_VERIFICATION_STATUSES:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') has unrecognized verification_status: '{v_status}'.")
        elif v_status != "physically_verified":
            unverified_connections += 1

        # Rule 9: data_source exists on connection and is valid
        d_source = conn.get("data_source")
        if not d_source:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') is missing 'data_source'.")
        elif d_source not in ALLOWED_DATA_SOURCES:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') has unrecognized data_source: '{d_source}'.")

        # Phase 2G: accessibility_confidence must be high, medium, or low
        conf = conn.get("accessibility_confidence")
        if not conf:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') is missing 'accessibility_confidence'.")
        elif str(conf).lower() not in ALLOWED_CONFIDENCE_LEVELS:
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') has invalid accessibility_confidence: '{conf}'. Expected high, medium, or low.")

        # Phase 2G: accessibility_notes must exist
        if not conn.get("accessibility_notes"):
            errors.append(f"Connection #{idx} ('{u}' -> '{v}') is missing 'accessibility_notes'.")

    # Check for orphan locations (locations with zero connections)
    orphan_locations = [name for name in node_names if name not in connected_nodes]
    if orphan_locations:
        errors.append(f"Orphan location(s) with no connections: {', '.join(orphan_locations)}")

    # Track warnings
    if unverified_connections > 0:
        warnings.append(f"{unverified_connections} accessibility connections require physical verification.")

    is_valid = len(errors) == 0

    # Build formatted report
    check_sym = _get_symbol("✓", "[OK]")
    err_sym = _get_symbol("✗", "[X]")

    lines = [
        "JAIN GLOBAL CAMPUS DATA VALIDATION",
        "----------------------------------",
        "",
        f"Locations: {len(locations)}",
        f"Connections: {len(connections)}",
        "",
    ]

    if is_valid:
        lines.extend([
            f"{check_sym} All locations valid",
            f"{check_sym} All connections valid",
            f"{check_sym} No orphan locations",
            f"{check_sym} Distances valid",
            f"{check_sym} Coordinates valid",
            f"{check_sym} Accessibility metadata valid",
        ])
    else:
        lines.append("ERRORS FOUND:")
        for err in errors:
            lines.append(f"  {err_sym} {err}")

    if warnings:
        lines.append("")
        lines.append("WARNING:")
        for w in warnings:
            lines.append(f"  {w}")

    lines.append("")
    lines.append("STATUS:")
    lines.append("VALID" if is_valid else "INVALID")

    report_str = "\n".join(lines)

    if verbose:
        try:
            print(report_str)
        except UnicodeEncodeError:
            # Fallback for strict encodings
            ascii_report = report_str.replace("✓", "[OK]").replace("✗", "[X]")
            print(ascii_report)

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "report": report_str,
        "location_count": len(locations),
        "connection_count": len(connections),
    }


def build_campus_graph(data_or_path=None):
    """Construct and populate a CampusGraph instance from data dict or file path.

    Supports both Phase 2C 'connections' schema and legacy 'edges' schema.

    Args:
        data_or_path (dict, str, or Path, optional): Either parsed JSON dict
                                                    or path to JSON file.

    Returns:
        tuple (CampusGraph, dict): The built graph and the raw metadata dictionary.

    Raises:
        DataManagerError: If data validation fails or structure is malformed.
    """
    if isinstance(data_or_path, dict):
        data = data_or_path
    else:
        data = load_campus_data(data_or_path)

    if "locations" not in data:
        raise DataManagerError("Invalid campus data: 'locations' array required.")

    graph = CampusGraph()
    name_to_id = {}

    # 1. Add all locations
    for loc in data["locations"]:
        try:
            graph.add_location(loc)
            name_to_id[loc["name"]] = loc["id"]
            name_to_id[loc["id"]] = loc["id"]
        except Exception as err:
            raise DataManagerError(f"Failed to add location '{loc.get('id')}': {err}")

    # 2. Add all connections / edges
    connections = data.get("connections", data.get("edges", []))
    for conn in connections:
        u_raw = conn.get("source", conn.get("from"))
        v_raw = conn.get("destination", conn.get("to"))
        dist = conn.get("distance", conn.get("distance_meters"))

        if not u_raw or not v_raw or dist is None:
            raise DataManagerError(f"Connection missing required endpoints/distance: {conn}")

        u_id = name_to_id.get(u_raw, u_raw)
        v_id = name_to_id.get(v_raw, v_raw)

        # Extract extra attributes
        extra_attrs = {
            k: v for k, v in conn.items()
            if k not in ("source", "destination", "from", "to", "distance", "distance_meters")
        }

        try:
            graph.add_edge(u_id, v_id, dist, bidirectional=True, **extra_attrs)
        except Exception as err:
            raise DataManagerError(f"Failed to add edge between '{u_id}' and '{v_id}': {err}")

    metadata = {
        "campus_name": data.get("campus_name", "Unknown Campus"),
        "campus_address": data.get("campus_address", ""),
        "description": data.get("description", ""),
        "data_disclaimer": data.get("data_disclaimer", ""),
        "metadata": data.get("metadata", {}),
    }

    return graph, metadata


if __name__ == "__main__":
    validate_campus_data()
