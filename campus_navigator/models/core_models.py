"""Data models for Accessible Campus Navigator.

Encapsulates:
- VerificationStatus: distinctions between Verified, Provisional/Sample, and Unknown.
- AccessibilityProfile: constraints and preferences for wheelchairs, limited mobility, stair avoidance, general walking.
- LocationNode: outdoor and indoor points with accessibility metadata.
- PathwayEdge: edges connecting locations with step-free, ramp, stair, elevator flags.
- ObstacleReport: persistent lifecycle reports for accessibility barriers.
"""

import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PROVISIONAL = "PROVISIONAL"
    DEMONSTRATION = "DEMONSTRATION"
    UNKNOWN = "UNKNOWN"


class LocationType(str, Enum):
    OUTDOOR_ENTRANCE = "OUTDOOR_ENTRANCE"
    BUILDING_ENTRANCE = "BUILDING_ENTRANCE"
    BUILDING = "BUILDING"
    PARKING = "PARKING"
    FACILITY = "FACILITY"
    CORRIDOR = "CORRIDOR"
    CLASSROOM = "CLASSROOM"
    LABORATORY = "LABORATORY"
    OFFICE = "OFFICE"
    RESTROOM = "RESTROOM"
    ELEVATOR = "ELEVATOR"
    STAIRCASE = "STAIRCASE"
    RAMP = "RAMP"
    EMERGENCY_EXIT = "EMERGENCY_EXIT"
    FLOOR_JUNCTION = "FLOOR_JUNCTION"


class SurfaceType(str, Enum):
    PAVED_SMOOTH = "PAVED_SMOOTH"
    PAVED_TACTILE = "PAVED_TACTILE"
    COBBLESTONE = "COBBLESTONE"
    GRAVEL = "GRAVEL"
    INDOOR_TILE = "INDOOR_TILE"
    INDOOR_CARPET = "INDOOR_CARPET"
    UNKNOWN = "UNKNOWN"


class ObstacleType(str, Enum):
    BLOCKED_RAMP = "BLOCKED_RAMP"
    CONSTRUCTION = "CONSTRUCTION"
    ELEVATOR_UNAVAILABLE = "ELEVATOR_UNAVAILABLE"
    DAMAGED_PATHWAY = "DAMAGED_PATHWAY"
    BLOCKED_CORRIDOR = "BLOCKED_CORRIDOR"
    INACCESSIBLE_ENTRANCE = "INACCESSIBLE_ENTRANCE"
    TEMPORARY_OBSTRUCTION = "TEMPORARY_OBSTRUCTION"
    STAIR_BLOCKED = "STAIR_BLOCKED"
    DOOR_NARROW = "DOOR_NARROW"
    OTHER = "OTHER"


class ObstacleSeverity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL_BLOCKING = "CRITICAL_BLOCKING"


class ObstacleStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    UNDER_REVIEW = "UNDER_REVIEW"
    VERIFIED = "VERIFIED"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


@dataclass
class AccessibilityProfile:
    """User mobility profile configuration."""
    name: str = "Wheelchair User"
    permit_stairs: bool = False
    require_step_free: bool = True
    prefer_ramps: bool = True
    allow_elevators: bool = True
    max_walking_distance_m: Optional[float] = None
    optimize_for: str = "distance"  # "distance" or "time"
    strict_mode: bool = False  # If True, excludes edges with UNKNOWN accessibility or unverified status

    @classmethod
    def wheelchair_user(cls, strict_mode: bool = False) -> "AccessibilityProfile":
        return cls(
            name="Wheelchair User",
            permit_stairs=False,
            require_step_free=True,
            prefer_ramps=True,
            allow_elevators=True,
            max_walking_distance_m=None,
            optimize_for="distance",
            strict_mode=strict_mode
        )

    @classmethod
    def limited_mobility(cls) -> "AccessibilityProfile":
        return cls(
            name="Limited Mobility",
            permit_stairs=False,
            require_step_free=True,
            prefer_ramps=True,
            allow_elevators=True,
            max_walking_distance_m=800.0,
            optimize_for="distance"
        )

    @classmethod
    def avoid_stairs(cls) -> "AccessibilityProfile":
        return cls(
            name="Avoid Stairs",
            permit_stairs=False,
            require_step_free=False,
            prefer_ramps=True,
            allow_elevators=True,
            max_walking_distance_m=None,
            optimize_for="time"
        )

    @classmethod
    def general_walking(cls) -> "AccessibilityProfile":
        return cls(
            name="General Walking",
            permit_stairs=True,
            require_step_free=False,
            prefer_ramps=False,
            allow_elevators=True,
            max_walking_distance_m=None,
            optimize_for="time"
        )


@dataclass
class LocationNode:
    """Node representing a point on outdoor campus or indoor floor plan."""
    id: str
    name: str
    node_type: LocationType
    verification: VerificationStatus
    # Geographic coordinates (for outdoor nodes)
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    # Indoor coordinates (for demonstration floor plans)
    floor: Optional[int] = None  # 0 = Ground, 1 = 1st, 2 = 2nd, 3 = 3rd
    building_id: Optional[str] = None
    x: Optional[float] = None  # 2D schematic x
    y: Optional[float] = None  # 2D schematic y
    # Accessibility metadata
    is_step_free_accessible: bool = True
    has_tactile_paving: Optional[bool] = None
    door_width_cm: Optional[float] = None
    is_emergency_exit: bool = False
    description: str = ""
    notes: str = ""
    data_source: str = "Verified Geographic / OpenStreetMap"
    indoor_building_id: Optional[str] = None

    def is_indoor(self) -> bool:
        return self.floor is not None and self.building_id is not None

    def is_geolocated(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type.value if isinstance(self.node_type, LocationType) else self.node_type,
            "verification": self.verification.value if isinstance(self.verification, VerificationStatus) else self.verification,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "floor": self.floor,
            "building_id": self.building_id,
            "x": self.x,
            "y": self.y,
            "is_step_free_accessible": self.is_step_free_accessible,
            "has_tactile_paving": self.has_tactile_paving,
            "door_width_cm": self.door_width_cm,
            "is_emergency_exit": self.is_emergency_exit,
            "description": self.description,
            "notes": self.notes,
            "data_source": self.data_source,
            "indoor_building_id": self.indoor_building_id
        }


@dataclass
class PathwayEdge:
    """Edge representing a navigable pathway between two locations."""
    id: str
    source: str
    target: str
    distance_m: float
    estimated_time_sec: float
    verification: VerificationStatus
    # Accessibility features
    is_step_free: bool = True
    has_stairs: bool = False
    has_ramp: bool = False
    is_elevator: bool = False
    surface: SurfaceType = SurfaceType.UNKNOWN
    width_cm: Optional[float] = None
    slope_percent: Optional[float] = None
    is_indoor: bool = False
    floor_transition: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "target": self.target,
            "distance_m": self.distance_m,
            "estimated_time_sec": self.estimated_time_sec,
            "verification": self.verification.value if isinstance(self.verification, VerificationStatus) else self.verification,
            "is_step_free": self.is_step_free,
            "has_stairs": self.has_stairs,
            "has_ramp": self.has_ramp,
            "is_elevator": self.is_elevator,
            "surface": self.surface.value if isinstance(self.surface, SurfaceType) else self.surface,
            "width_cm": self.width_cm,
            "slope_percent": self.slope_percent,
            "is_indoor": self.is_indoor,
            "floor_transition": self.floor_transition,
            "notes": self.notes
        }


@dataclass
class ObstacleReport:
    """Report of a physical or operational barrier affecting accessibility."""
    id: str
    location_or_edge_id: str
    obstacle_type: ObstacleType
    description: str
    severity: ObstacleSeverity
    timestamp: str
    status: ObstacleStatus
    reported_by_role: str = "Student / Visitor"
    verification_notes: str = ""
    expiration_time: Optional[str] = None
    location_id: Optional[str] = None
    pathway_id: Optional[str] = None
    building_id: Optional[str] = None
    floor_id: Optional[int] = None
    verification_status: VerificationStatus = VerificationStatus.PROVISIONAL
    resolved_at: Optional[str] = None

    def is_blocking_for_routing(self, current_time_iso: Optional[str] = None) -> bool:
        """Determines if the obstacle actively impairs or blocks navigation.
        Policy:
        1. RESOLVED or REJECTED obstacles never block.
        2. VERIFIED obstacles block when severity is HIGH or CRITICAL_BLOCKING.
        3. SUBMITTED or UNDER_REVIEW severe obstacles block cautiously for safety.
        4. If expiration_time is reached on an unverified report, it is considered expired (non-blocking).
        """
        if self.status in (ObstacleStatus.RESOLVED, ObstacleStatus.REJECTED):
            return False

        # Expiration check
        if self.expiration_time:
            now_iso = current_time_iso or datetime.datetime.now(datetime.timezone.utc).isoformat()
            try:
                # Replace 'Z' if present, parse ISO or standard format
                t_exp = datetime.datetime.fromisoformat(self.expiration_time.replace("Z", "+00:00"))
                t_now = datetime.datetime.fromisoformat(now_iso.replace("Z", "+00:00"))
                # Normalize timezones if one is naive and one is aware
                if t_exp.tzinfo is None and t_now.tzinfo is not None:
                    t_exp = t_exp.replace(tzinfo=t_now.tzinfo)
                elif t_exp.tzinfo is not None and t_now.tzinfo is None:
                    t_now = t_now.replace(tzinfo=t_exp.tzinfo)

                if t_now > t_exp and self.status != ObstacleStatus.VERIFIED:
                    return False
            except Exception:
                # Fallback to string comparison if parsing fails
                if now_iso > self.expiration_time and self.status != ObstacleStatus.VERIFIED:
                    return False

        # Critical or High severity blocks routing even under review for wheelchair safety
        if self.status in (ObstacleStatus.VERIFIED, ObstacleStatus.UNDER_REVIEW, ObstacleStatus.SUBMITTED):
            return self.severity in (ObstacleSeverity.CRITICAL_BLOCKING, ObstacleSeverity.HIGH)
        return False
