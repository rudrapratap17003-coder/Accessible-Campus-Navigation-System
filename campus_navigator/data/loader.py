"""Data loader and validator for campus datasets."""

import json
import os
from typing import Dict, Any, List, Tuple
from campus_navigator.models.core_models import (
    LocationNode,
    PathwayEdge,
    LocationType,
    VerificationStatus,
    SurfaceType,
)
from campus_navigator.data.transitions import CAMPUS_TRANSITIONS


class DataLoader:
    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = os.path.dirname(os.path.abspath(__file__))
        else:
            self.data_dir = data_dir

        self.outdoor_file = os.path.join(self.data_dir, "campus_data.json")
        self.indoor_file = os.path.join(self.data_dir, "indoor_data.json")

    def load_outdoor_data(self) -> Tuple[Dict[str, Any], List[LocationNode], List[PathwayEdge]]:
        with open(self.outdoor_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("campus_metadata", {})
        nodes = []
        for n in data.get("nodes", []):
            nodes.append(LocationNode(
                id=n["id"],
                name=n["name"],
                node_type=LocationType(n["node_type"]) if n["node_type"] in LocationType._value2member_map_ else LocationType.FACILITY,
                verification=VerificationStatus(n["verification"]),
                latitude=n.get("latitude"),
                longitude=n.get("longitude"),
                is_step_free_accessible=n.get("is_step_free_accessible", True),
                has_tactile_paving=n.get("has_tactile_paving"),
                door_width_cm=n.get("door_width_cm"),
                description=n.get("description", ""),
                notes=n.get("notes", ""),
                data_source=n.get("data_source", "Verified Geographic / OpenStreetMap"),
                indoor_building_id=n.get("indoor_building_id")
            ))

        edges = []
        for e in data.get("edges", []):
            edges.append(PathwayEdge(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                distance_m=float(e["distance_m"]),
                estimated_time_sec=float(e["estimated_time_sec"]),
                verification=VerificationStatus(e["verification"]),
                is_step_free=e.get("is_step_free", True),
                has_stairs=e.get("has_stairs", False),
                has_ramp=e.get("has_ramp", False),
                is_elevator=e.get("is_elevator", False),
                surface=SurfaceType(e["surface"]) if e.get("surface") in SurfaceType._value2member_map_ else SurfaceType.UNKNOWN,
                width_cm=e.get("width_cm"),
                slope_percent=e.get("slope_percent"),
                is_indoor=False,
                floor_transition=False,
                notes=e.get("notes", "")
            ))

        return meta, nodes, edges

    def load_indoor_data(self) -> Tuple[Dict[str, Any], List[LocationNode], List[PathwayEdge]]:
        with open(self.indoor_file, "r", encoding="utf-8") as f:
            data = json.load(f)

        meta = data.get("building_metadata", {})
        nodes = []
        for n in data.get("nodes", []):
            nodes.append(LocationNode(
                id=n["id"],
                name=n["name"],
                node_type=LocationType(n["node_type"]) if n["node_type"] in LocationType._value2member_map_ else LocationType.FACILITY,
                verification=VerificationStatus(n["verification"]),
                floor=n.get("floor"),
                building_id=n.get("building_id"),
                x=n.get("x"),
                y=n.get("y"),
                is_step_free_accessible=n.get("is_step_free_accessible", True),
                has_tactile_paving=n.get("has_tactile_paving"),
                door_width_cm=n.get("door_width_cm"),
                is_emergency_exit=n.get("is_emergency_exit", False),
                description=n.get("description", "")
            ))

        edges = []
        for e in data.get("edges", []):
            edges.append(PathwayEdge(
                id=e["id"],
                source=e["source"],
                target=e["target"],
                distance_m=float(e["distance_m"]),
                estimated_time_sec=float(e["estimated_time_sec"]),
                verification=VerificationStatus(e["verification"]),
                is_step_free=e.get("is_step_free", True),
                has_stairs=e.get("has_stairs", False),
                has_ramp=e.get("has_ramp", False),
                is_elevator=e.get("is_elevator", False),
                surface=SurfaceType(e["surface"]) if e.get("surface") in SurfaceType._value2member_map_ else SurfaceType.UNKNOWN,
                width_cm=e.get("width_cm"),
                slope_percent=e.get("slope_percent"),
                is_indoor=True,
                floor_transition=e.get("floor_transition", False),
                notes=e.get("notes", "")
            ))

        return meta, nodes, edges

    def save_outdoor_data(self, meta: Dict[str, Any], nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
        data = {
            "campus_metadata": meta,
            "nodes": nodes,
            "edges": edges
        }
        with open(self.outdoor_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load_buildings(self) -> Dict[str, Any]:
        buildings_file = os.path.join(self.data_dir, "buildings.json")
        if os.path.exists(buildings_file):
            with open(buildings_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"buildings": []}

    def load_floor_plans(self) -> Dict[str, Any]:
        floor_plans_file = os.path.join(self.data_dir, "floor_plans.json")
        if os.path.exists(floor_plans_file):
            with open(floor_plans_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {"floors": {}}

    def load_indoor_pathways(self) -> List[Dict[str, Any]]:
        pathways_file = os.path.join(self.data_dir, "indoor_pathways.json")
        if os.path.exists(pathways_file):
            with open(pathways_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("pathways", [])
        return []

    def save_indoor_data(self, meta: Dict[str, Any], nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> None:
        data = {
            "building_metadata": meta,
            "nodes": nodes,
            "edges": edges
        }
        with open(self.indoor_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
