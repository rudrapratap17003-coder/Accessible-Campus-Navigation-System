"""
accessibility.py — Accessibility Filtering & Weighting Logic
==============================================================
Defines the accessibility profiles and evaluation rules used by
routing algorithms to find routes tailored to diverse mobility needs.

Supported Accessibility Preferences:
    1. STANDARD          - Standard shortest distance; all pathways allowed.
    2. WHEELCHAIR        - Requires step-free access. Strictly avoids stairs.
                           Prefers ramps and flat paved surfaces.
    3. AVOID_STAIRS      - Disallows any pathway segments containing stairs.
    4. PREFER_RAMPS      - Allows stairs if necessary, but heavily penalizes
                           them in cost calculations to favor ramp alternatives.
    5. REQUIRE_ELEVATOR  - Strictly requires elevator for vertical transitions
                           (such as multi-floor buildings like CRFM).

Learning Objectives:
    - Enumerations and clean policy-based filtering.
    - Custom weighting functions for heuristic graph routing.
    - Dynamic obstacle avoidance support.
"""


class AccessibilityMode:
    """Supported accessibility preference identifiers."""
    STANDARD = "standard"
    WHEELCHAIR = "wheelchair"
    AVOID_STAIRS = "avoid_stairs"
    PREFER_RAMPS = "prefer_ramps"
    REQUIRE_ELEVATOR = "require_elevator"

    ALL_MODES = [
        STANDARD,
        WHEELCHAIR,
        AVOID_STAIRS,
        PREFER_RAMPS,
        REQUIRE_ELEVATOR,
    ]

    DESCRIPTIONS = {
        STANDARD: "Standard Shortest Path (no accessibility restrictions)",
        WHEELCHAIR: "Wheelchair Accessible (strictly step-free; ramps required)",
        AVOID_STAIRS: "Avoid Stairs (excludes all stairways)",
        PREFER_RAMPS: "Prefer Ramps (favors gentle slopes and ramps over steps)",
        REQUIRE_ELEVATOR: "Require Elevator (mandatory for floor transitions)",
    }


class AccessibilityConfidence:
    """Confidence levels for accessibility data (Phase 2G)."""
    HIGH = "high"       # Physically verified on-site
    MEDIUM = "medium"   # Supported by reliable documentation, not physically audited
    LOW = "low"         # Prototype assumption or incomplete information

    ALL = [HIGH, MEDIUM, LOW]


class AccessibilityBadge:
    """UI presentation badges for accessibility status."""
    VERIFIED_ACCESSIBLE = "verified_accessible"
    NEEDS_VERIFICATION = "needs_verification"
    KNOWN_INACCESSIBLE = "known_inaccessible"

    LABELS = {
        VERIFIED_ACCESSIBLE: "✓ Verified accessible",
        NEEDS_VERIFICATION: "⚠ Accessibility information needs verification",
        KNOWN_INACCESSIBLE: "✗ Known inaccessible",
    }


def get_accessibility_badge(item_data):
    """Evaluate an edge or location dictionary to determine its UI accessibility badge.

    Rules:
        - If explicitly known inaccessible (accessible is False or has_stairs is True
          without ramps), returns KNOWN_INACCESSIBLE ('✗ Known inaccessible').
        - If physically verified (high confidence) and accessible is True,
          returns VERIFIED_ACCESSIBLE ('✓ Verified accessible').
        - If confidence is low or medium, or accessible is 'unknown',
          returns NEEDS_VERIFICATION ('⚠ Accessibility information needs verification').

    Args:
        item_data (dict): Edge or location attribute dictionary.

    Returns:
        tuple (str, str): (badge_key, human_readable_label)
    """
    conf = str(item_data.get("accessibility_confidence", AccessibilityConfidence.LOW)).lower()
    acc_val = item_data.get("accessible", item_data.get("accessible_entrance", "unknown"))
    acc_str = str(acc_val).strip().lower()

    stairs_val = item_data.get("stairs", item_data.get("has_stairs", "unknown"))
    stairs_str = str(stairs_val).strip().lower()

    ramp_val = item_data.get("ramp", item_data.get("has_ramp", "unknown"))
    ramp_str = str(ramp_val).strip().lower()

    # 1. Known inaccessible
    if acc_str == "false":
        return (AccessibilityBadge.KNOWN_INACCESSIBLE,
                AccessibilityBadge.LABELS[AccessibilityBadge.KNOWN_INACCESSIBLE])

    if stairs_str == "true" and ramp_str == "false":
        return (AccessibilityBadge.KNOWN_INACCESSIBLE,
                AccessibilityBadge.LABELS[AccessibilityBadge.KNOWN_INACCESSIBLE])

    # 2. Verified accessible (high confidence + confirmed accessible)
    if conf == AccessibilityConfidence.HIGH and (acc_str == "true" or ramp_str == "true"):
        return (AccessibilityBadge.VERIFIED_ACCESSIBLE,
                AccessibilityBadge.LABELS[AccessibilityBadge.VERIFIED_ACCESSIBLE])

    # 3. Default: low/medium confidence or unverified information
    return (AccessibilityBadge.NEEDS_VERIFICATION,
            AccessibilityBadge.LABELS[AccessibilityBadge.NEEDS_VERIFICATION])


# Standard walking speeds for estimated travel times (in meters per minute)
WALKING_SPEED_METERS_PER_MIN = 75.0      # ~4.5 km/h average campus walking speed
WHEELCHAIR_SPEED_METERS_PER_MIN = 50.0   # ~3.0 km/h average wheelchair navigation speed


def is_edge_allowed(edge_data, mode, blocked_edges=None):
    """Determine whether an edge satisfies the given accessibility criteria.

    Args:
        edge_data (dict): Edge dictionary containing path attributes.
        mode (str): Accessibility mode (from AccessibilityMode).
        blocked_edges (set or None): Set of blocked edge tuples {(u, v), ...}.

    Returns:
        bool: True if the path segment can be traversed; False otherwise.
    """
    u = edge_data.get("from")
    v = edge_data.get("target")

    # 1. Check if the edge is temporarily blocked by an active reported obstacle
    if blocked_edges:
        if (u, v) in blocked_edges or (v, u) in blocked_edges:
            return False

    has_stairs = edge_data.get("has_stairs", False)
    has_ramp = edge_data.get("has_ramp", False)
    has_elevator = edge_data.get("has_elevator", False)
    path_type = edge_data.get("path_type", "walkway")

    # 2. Apply mode-specific accessibility rules
    if mode == AccessibilityMode.STANDARD:
        return True

    elif mode == AccessibilityMode.WHEELCHAIR:
        # Wheelchairs cannot navigate stairs
        if has_stairs:
            return False
        # If path is an indoor transition to another floor, requires elevator or ramp
        if path_type == "indoor" and not (has_elevator or has_ramp):
            return False
        return True

    elif mode == AccessibilityMode.AVOID_STAIRS:
        # Strictly avoid any segment containing stairs
        if has_stairs:
            return False
        return True

    elif mode == AccessibilityMode.PREFER_RAMPS:
        # Allows all paths, but we rely on calculate_edge_weight() to penalize stairs
        return True

    elif mode == AccessibilityMode.REQUIRE_ELEVATOR:
        # For indoor multi-level edges, elevator must be present
        if path_type == "indoor" and not has_elevator:
            return False
        # If stairs are present without elevator, disallow
        if has_stairs and not has_elevator:
            return False
        return True

    # Default fallback: allow
    return True


def calculate_edge_weight(edge_data, mode):
    """Calculate the effective routing weight (cost) of an edge for Dijkstra's algorithm.

    In STANDARD mode, the weight is simply the physical distance in meters.
    In PREFER_RAMPS mode, ramp segments are rewarded and stairs heavily penalized.

    Args:
        edge_data (dict): Edge dictionary.
        mode (str): Accessibility mode.

    Returns:
        float: Effective weight for shortest-path calculation.
    """
    base_distance = float(edge_data.get("distance_meters", 1.0))

    if mode == AccessibilityMode.PREFER_RAMPS:
        # If edge has a ramp, give a 20% discount to encourage ramp usage
        if edge_data.get("has_ramp", False):
            return base_distance * 0.8
        # If edge has stairs, penalize heavily (5x cost) so ramps are preferred
        if edge_data.get("has_stairs", False):
            return base_distance * 5.0

    elif mode == AccessibilityMode.WHEELCHAIR:
        # Small preference for paved ramps
        if edge_data.get("has_ramp", False):
            return base_distance * 0.95

    return base_distance


def estimate_travel_time(distance_meters, mode):
    """Estimate walking or wheelchair travel time in minutes.

    Args:
        distance_meters (float): Total route distance in meters.
        mode (str): Accessibility mode.

    Returns:
        float: Estimated travel time rounded to 1 decimal place.
    """
    if mode == AccessibilityMode.WHEELCHAIR:
        speed = WHEELCHAIR_SPEED_METERS_PER_MIN
    else:
        speed = WALKING_SPEED_METERS_PER_MIN

    minutes = distance_meters / speed
    return round(max(0.5, minutes), 1)
