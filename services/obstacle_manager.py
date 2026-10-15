"""
obstacle_manager.py — Accessibility Obstacle & Disruption Reporter Service
============================================================================
Handles loading, saving, reporting, and resolving temporary accessibility
obstacles (e.g. broken ramps, out-of-service elevators, construction zones).

Uses Python Standard Library:
    - json      (persistence to obstacles.json)
    - pathlib   (file path resolution)
    - datetime  (timestamping reports)

Learning Objectives:
    - Dynamic graph re-weighting / edge exclusion
    - JSON-based transaction logging and state management
    - Defensive file handling and error recovery
"""

import json
from pathlib import Path
from datetime import datetime, timezone


def get_default_obstacles_path():
    """Resolve the default path to obstacles.json relative to the project root."""
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir / "obstacles.json"


class ObstacleManager:
    """Manages active and resolved accessibility obstacles on campus."""

    def __init__(self, file_path=None):
        """Initialize the obstacle manager.

        Args:
            file_path (str or Path, optional): Path to obstacles.json.
        """
        self.file_path = Path(file_path) if file_path else get_default_obstacles_path()
        self._ensure_file_exists()

    def _ensure_file_exists(self):
        """Create an empty obstacles file if it does not already exist."""
        if not self.file_path.is_file():
            initial_data = {"reported_obstacles": []}
            self.file_path.write_text(json.dumps(initial_data, indent=4), encoding="utf-8")

    def load_all_obstacles(self):
        """Read all obstacle records from disk.

        Returns:
            list: List of obstacle dictionaries.
        """
        try:
            content = self.file_path.read_text(encoding="utf-8")
            data = json.loads(content)
            return data.get("reported_obstacles", [])
        except (json.JSONDecodeError, OSError):
            return []

    def get_active_obstacles(self):
        """Retrieve only active (unresolved) accessibility obstacles.

        Returns:
            list: List of active obstacle dictionaries.
        """
        all_obs = self.load_all_obstacles()
        return [obs for obs in all_obs if obs.get("status") == "active"]

    def get_blocked_edges(self):
        """Extract a set of blocked edge tuples {(source, destination), ...} from active obstacles.

        Returns:
            set: Set of (u, v) and (v, u) node pairs that cannot currently be traversed.
        """
        blocked = set()
        for obs in self.get_active_obstacles():
            source = obs.get("source")
            destination = obs.get("destination")
            if source and destination:
                blocked.add((source, destination))
                blocked.add((destination, source))
        return blocked

    def report_obstacle(self, source, destination, obstacle_type, description, reported_by="Campus User"):
        """Add a new accessibility obstacle report.

        Args:
            source (str): Starting location of the obstructed path.
            destination (str): Ending location of the obstructed path.
            obstacle_type (str): Category (e.g. 'ramp_broken', 'elevator_out_of_service', 'construction').
            description (str): Human-readable details.
            reported_by (str, optional): Identity or role of the reporter.

        Returns:
            dict: The newly created obstacle record.
        """
        obstacles = self.load_all_obstacles()

        new_id = f"obs_{len(obstacles) + 1}_{int(datetime.now(timezone.utc).timestamp())}"
        now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        new_record = {
            "id": new_id,
            "source": source,
            "destination": destination,
            "obstacle_type": obstacle_type,
            "description": description,
            "reported_by": reported_by,
            "reported_at": now_iso,
            "status": "active",
        }

        obstacles.append(new_record)
        self._save(obstacles)
        return new_record

    def resolve_obstacle(self, obstacle_id):
        """Mark an existing obstacle as resolved.

        Args:
            obstacle_id (str): The ID of the obstacle to resolve.

        Returns:
            bool: True if obstacle was found and resolved; False otherwise.
        """
        obstacles = self.load_all_obstacles()
        found = False

        for obs in obstacles:
            if obs.get("id") == obstacle_id:
                obs["status"] = "resolved"
                obs["resolved_at"] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
                found = True
                break

        if found:
            self._save(obstacles)

        return found

    def clear_all_obstacles(self):
        """Reset the obstacles file to empty (useful for testing and reset functionality)."""
        self._save([])

    def _save(self, obstacles_list):
        """Write the obstacles array back to disk."""
        payload = {"reported_obstacles": obstacles_list}
        self.file_path.write_text(json.dumps(payload, indent=4, ensure_ascii=False), encoding="utf-8")
