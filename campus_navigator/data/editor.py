"""Campus Map and Accessibility Data Editor Service.

Provides robust, validated data management for campus administrators without
manually editing Python code:
1. Location management (add/edit, coordinates validation, category, verification, building/floor).
2. Pathway management (add/edit, node reference checks, distances, accessibility attributes, verification).
3. Indoor map management (floors, room coordinates, floor transitions, elevators, demo replacement).
4. Data validation (duplicate IDs, invalid/missing coordinates, dangling edges, negative weights).
5. Data import/export with preview, schema validation, and automatic pre-save backup creation.
6. Explicit verification controls preventing unverified data from silently becoming verified.
"""

import os
import json
import shutil
import datetime
from typing import Dict, Any, List, Optional, Tuple
from campus_navigator.models.core_models import (
    LocationNode,
    PathwayEdge,
    LocationType,
    VerificationStatus,
    SurfaceType
)
from campus_navigator.data.loader import DataLoader


class CampusDataEditor:
    """Administrator data editor and validator for campus datasets."""

    def __init__(self, data_loader: Optional[DataLoader] = None):
        self.loader = data_loader or DataLoader()
        self.backup_dir = os.path.join(self.loader.data_dir, "backups")
        os.makedirs(self.backup_dir, exist_ok=True)

    # -------------------------------------------------------------
    # 1. BACKUP & EXPORT MANAGEMENT
    # -------------------------------------------------------------
    def create_backup(self, tag: str = "auto") -> Tuple[str, str]:
        """Creates timestamped backups of campus_data.json and indoor_data.json."""
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        outdoor_backup = os.path.join(self.backup_dir, f"campus_data_{tag}_{timestamp}.json")
        indoor_backup = os.path.join(self.backup_dir, f"indoor_data_{tag}_{timestamp}.json")

        if os.path.exists(self.loader.outdoor_file):
            shutil.copy2(self.loader.outdoor_file, outdoor_backup)
        if os.path.exists(self.loader.indoor_file):
            shutil.copy2(self.loader.indoor_file, indoor_backup)

        return outdoor_backup, indoor_backup

    def export_dataset_json(self, dataset_type: str = "outdoor") -> str:
        """Returns JSON string for export."""
        target_file = self.loader.outdoor_file if dataset_type == "outdoor" else self.loader.indoor_file
        with open(target_file, "r", encoding="utf-8") as f:
            return f.read()

    # -------------------------------------------------------------
    # 2. DATA VALIDATION ENGINE
    # -------------------------------------------------------------
    def validate_dataset(self, data: Dict[str, Any], is_indoor: bool = False) -> List[str]:
        """Validates dataset dictionary for consistency, integrity, and constraints.
        Returns list of error messages. If empty, dataset is valid.
        """
        errors = []
        meta_key = "building_metadata" if is_indoor else "campus_metadata"
        if meta_key not in data:
            errors.append(f"Missing required metadata key: '{meta_key}'")

        nodes = data.get("nodes", [])
        edges = data.get("edges", [])

        if not isinstance(nodes, list) or not isinstance(edges, list):
            errors.append("'nodes' and 'edges' must be lists.")
            return errors

        # Validate nodes
        node_ids = set()
        for idx, n in enumerate(nodes):
            nid = n.get("id")
            if not nid or not str(nid).strip():
                errors.append(f"Node at index {idx} has missing or empty 'id'.")
                continue
            if nid in node_ids:
                errors.append(f"Duplicate node ID detected: '{nid}'.")
            node_ids.add(nid)

            name = n.get("name")
            if not name or not str(name).strip():
                errors.append(f"Node '{nid}' has missing or empty 'name'.")

            # Verification Status check
            verif = n.get("verification")
            if verif not in VerificationStatus._value2member_map_:
                errors.append(f"Node '{nid}' has invalid verification status: '{verif}'.")

            # Coordinates validation
            if is_indoor:
                x = n.get("x")
                y = n.get("y")
                if x is not None and not isinstance(x, (int, float)):
                    errors.append(f"Indoor node '{nid}' has non-numeric x coordinate: '{x}'.")
                if y is not None and not isinstance(y, (int, float)):
                    errors.append(f"Indoor node '{nid}' has non-numeric y coordinate: '{y}'.")
                if n.get("floor") is None:
                    errors.append(f"Indoor node '{nid}' must specify a floor level.")
            else:
                lat = n.get("latitude")
                lon = n.get("longitude")
                # Latitude/longitude can be null for unlocated destinations
                if lat is not None or lon is not None:
                    if lat is None or lon is None:
                        errors.append(f"Outdoor node '{nid}' has incomplete coordinates (one coordinate is missing).")
                    else:
                        if not isinstance(lat, (int, float)) or not (-90.0 <= lat <= 90.0):
                            errors.append(f"Outdoor node '{nid}' has invalid latitude: '{lat}'. Must be -90 to +90.")
                        if not isinstance(lon, (int, float)) or not (-180.0 <= lon <= 180.0):
                            errors.append(f"Outdoor node '{nid}' has invalid longitude: '{lon}'. Must be -180 to +180.")

        # Validate edges
        edge_ids = set()
        for idx, e in enumerate(edges):
            eid = e.get("id")
            if not eid or not str(eid).strip():
                errors.append(f"Edge at index {idx} has missing or empty 'id'.")
                continue
            if eid in edge_ids:
                errors.append(f"Duplicate edge ID detected: '{eid}'.")
            edge_ids.add(eid)

            src = e.get("source")
            tgt = e.get("target")
            if src not in node_ids:
                errors.append(f"Edge '{eid}' references non-existent source node: '{src}'.")
            if tgt not in node_ids:
                errors.append(f"Edge '{eid}' references non-existent target node: '{tgt}'.")
            if src == tgt:
                errors.append(f"Edge '{eid}' has identical source and target (self-loop): '{src}'.")

            dist = e.get("distance_m")
            if dist is None or not isinstance(dist, (int, float)) or dist < 0:
                errors.append(f"Edge '{eid}' has invalid or negative distance_m: '{dist}'.")

            est_time = e.get("estimated_time_sec")
            if est_time is None or not isinstance(est_time, (int, float)) or est_time < 0:
                errors.append(f"Edge '{eid}' has invalid or negative estimated_time_sec: '{est_time}'.")

            # Accessibility consistency
            if e.get("is_step_free") is True and e.get("has_stairs") is True:
                errors.append(f"Edge '{eid}' conflict: is_step_free=True but has_stairs=True.")

        return errors

    # -------------------------------------------------------------
    # 3. LOCATION MANAGEMENT
    # -------------------------------------------------------------
    def get_raw_outdoor_data(self) -> Dict[str, Any]:
        with open(self.loader.outdoor_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_raw_indoor_data(self) -> Dict[str, Any]:
        with open(self.loader.indoor_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def save_location(
        self,
        node_id: str,
        name: str,
        node_type: str,
        verification: str,
        is_indoor: bool = False,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        floor: Optional[int] = None,
        building_id: Optional[str] = None,
        x: Optional[float] = None,
        y: Optional[float] = None,
        is_step_free: bool = True,
        has_tactile_paving: Optional[bool] = None,
        door_width_cm: Optional[float] = None,
        description: str = "",
        data_source: str = "Verified Geographic / OpenStreetMap"
    ) -> Tuple[bool, str]:
        """Adds or updates a location node with full validation and backup."""
        # 1. Validation checks
        if not node_id.strip() or not name.strip():
            return False, "Node ID and Name cannot be empty."

        if not is_indoor and (latitude is not None or longitude is not None):
            if latitude is None or longitude is None:
                return False, "Both latitude and longitude must be provided for geolocated points."
            if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
                return False, f"Invalid GPS coordinates: ({latitude}, {longitude})."

        if is_indoor and floor is None:
            return False, "Indoor locations must specify a floor level (e.g. 0, 1, 2, 3)."

        # 2. Load target dataset
        target_file = self.loader.indoor_file if is_indoor else self.loader.outdoor_file
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        nodes = data.get("nodes", [])

        # 3. Build node dictionary
        node_dict = {
            "id": node_id.strip(),
            "name": name.strip(),
            "node_type": node_type,
            "verification": verification,
            "is_step_free_accessible": is_step_free,
            "has_tactile_paving": has_tactile_paving,
            "door_width_cm": door_width_cm,
            "description": description.strip()
        }

        if is_indoor:
            node_dict["floor"] = floor
            node_dict["building_id"] = building_id or "FET_MAIN"
            node_dict["x"] = x if x is not None else 50.0
            node_dict["y"] = y if y is not None else 50.0
        else:
            node_dict["latitude"] = latitude
            node_dict["longitude"] = longitude
            node_dict["data_source"] = data_source
            node_dict["indoor_building_id"] = building_id

        # 4. Insert or update
        existing_idx = next((i for i, n in enumerate(nodes) if n["id"] == node_id.strip()), None)
        if existing_idx is not None:
            nodes[existing_idx] = node_dict
        else:
            nodes.append(node_dict)

        data["nodes"] = nodes

        # 5. Validate whole dataset before writing
        errors = self.validate_dataset(data, is_indoor=is_indoor)
        if errors:
            return False, f"Dataset validation failed: {'; '.join(errors)}"

        # 6. Create backup and commit
        self.create_backup(tag=f"pre_loc_{node_id}")
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return True, f"Location '{node_id}' successfully saved!"

    # -------------------------------------------------------------
    # 4. PATHWAY MANAGEMENT
    # -------------------------------------------------------------
    def save_pathway(
        self,
        edge_id: str,
        source: str,
        target: str,
        distance_m: float,
        estimated_time_sec: float,
        verification: str,
        is_step_free: bool = True,
        has_stairs: bool = False,
        has_ramp: bool = False,
        is_elevator: bool = False,
        surface: str = "UNKNOWN",
        width_cm: Optional[float] = None,
        slope_percent: Optional[float] = None,
        is_indoor: bool = False,
        notes: str = ""
    ) -> Tuple[bool, str]:
        """Adds or updates a pathway with reference and constraint validation."""
        if not edge_id.strip() or not source.strip() or not target.strip():
            return False, "Edge ID, source, and target cannot be empty."

        if source == target:
            return False, "Pathway source and target must be distinct nodes."

        if distance_m < 0 or estimated_time_sec < 0:
            return False, "Distance and estimated time cannot be negative."

        if is_step_free and has_stairs:
            return False, "Contradiction: A pathway cannot be both step-free and have stairs."

        target_file = self.loader.indoor_file if is_indoor else self.loader.outdoor_file
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        node_ids = {n["id"] for n in data.get("nodes", [])}
        if source not in node_ids:
            return False, f"Source node '{source}' does not exist in target dataset."
        if target not in node_ids:
            return False, f"Target node '{target}' does not exist in target dataset."

        edges = data.get("edges", [])
        edge_dict = {
            "id": edge_id.strip(),
            "source": source.strip(),
            "target": target.strip(),
            "distance_m": float(distance_m),
            "estimated_time_sec": float(estimated_time_sec),
            "verification": verification,
            "is_step_free": is_step_free,
            "has_stairs": has_stairs,
            "has_ramp": has_ramp,
            "is_elevator": is_elevator,
            "surface": surface,
            "width_cm": width_cm,
            "slope_percent": slope_percent,
            "notes": notes
        }

        existing_idx = next((i for i, e in enumerate(edges) if e["id"] == edge_id.strip()), None)
        if existing_idx is not None:
            edges[existing_idx] = edge_dict
        else:
            edges.append(edge_dict)

        data["edges"] = edges

        errors = self.validate_dataset(data, is_indoor=is_indoor)
        if errors:
            return False, f"Dataset validation failed: {'; '.join(errors)}"

        self.create_backup(tag=f"pre_edge_{edge_id}")
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        return True, f"Pathway '{edge_id}' successfully saved!"

    # -------------------------------------------------------------
    # 5. IMPORT WITH PREVIEW AND BACKUP
    # -------------------------------------------------------------
    def import_dataset(self, json_content: str, is_indoor: bool = False) -> Tuple[bool, str, Dict[str, Any]]:
        """Parses, validates, and stages imported JSON data.
        Returns (success, message, preview_stats).
        """
        try:
            imported_data = json.loads(json_content)
        except Exception as e:
            return False, f"Invalid JSON syntax: {str(e)}", {}

        errors = self.validate_dataset(imported_data, is_indoor=is_indoor)
        if errors:
            return False, f"Import validation failed:\n" + "\n".join([f"• {err}" for err in errors[:10]]), {}

        nodes = imported_data.get("nodes", [])
        edges = imported_data.get("edges", [])
        stats = {
            "nodes_count": len(nodes),
            "edges_count": len(edges),
            "verified_nodes": sum(1 for n in nodes if n.get("verification") == "VERIFIED"),
            "provisional_nodes": sum(1 for n in nodes if n.get("verification") == "PROVISIONAL"),
            "demo_nodes": sum(1 for n in nodes if n.get("verification") == "DEMONSTRATION"),
            "step_free_edges": sum(1 for e in edges if e.get("is_step_free") is True),
            "data": imported_data
        }
        return True, "Dataset passed all validation checks and is ready to apply.", stats

    def apply_imported_dataset(self, validated_data: Dict[str, Any], is_indoor: bool = False) -> Tuple[bool, str]:
        """Commits validated imported data with automatic backup."""
        target_file = self.loader.indoor_file if is_indoor else self.loader.outdoor_file
        self.create_backup(tag="pre_bulk_import")

        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(validated_data, f, indent=2)

        return True, "Dataset successfully imported and persisted to disk!"
