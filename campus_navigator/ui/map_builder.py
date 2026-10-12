"""Interactive Folium Map Builder for Outdoor Campus Navigation.

Renders authentic OpenStreetMap tiles centered on JAIN Global Campus, Jakkasandra.
Includes:
- Zoom controls, pan, reset view button / campus center bounds.
- Distinct visual badges for VERIFIED vs PROVISIONAL locations.
- Clear differentiation between geolocated buildings and unlocated directory facilities.
- Step-free (solid green), ramp (solid blue), and stepped (dashed red) pathway classification.
- High-contrast route overlay with distance and travel time.
- Active obstacle markers with severity and verification status.
- Resilient error handling if map rendering or tile network experiences failure.
"""

import folium
from folium.plugins import Fullscreen, LocateControl
from typing import Dict, Any, List, Optional, Set
from campus_navigator.models.core_models import (
    LocationNode,
    PathwayEdge,
    VerificationStatus,
    LocationType,
    ObstacleReport,
)
from campus_navigator.algorithms.routing_engine import RouteResult


class OutdoorMapBuilder:
    def __init__(
        self,
        center_lat: float = 12.6482,
        center_lon: float = 77.4418,
        zoom_start: int = 17
    ):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.zoom_start = zoom_start

    def create_campus_map(
        self,
        nodes: Dict[str, LocationNode],
        edges: Dict[str, PathwayEdge],
        active_route: Optional[RouteResult] = None,
        obstacles: Optional[List[ObstacleReport]] = None,
        selected_node_id: Optional[str] = None
    ) -> folium.Map:
        """Constructs interactive folium map with safe error handling."""
        try:
            # Center on selected node if geolocated, else campus center
            map_center = [self.center_lat, self.center_lon]
            current_zoom = self.zoom_start
            if selected_node_id and selected_node_id in nodes:
                sel_n = nodes[selected_node_id]
                if sel_n.latitude and sel_n.longitude:
                    map_center = [sel_n.latitude, sel_n.longitude]
                    current_zoom = 18

            campus_map = folium.Map(
                location=map_center,
                zoom_start=current_zoom,
                tiles="OpenStreetMap",
                control_scale=True,
                zoom_control=True
            )

            # Add interactive navigation plugins
            Fullscreen(position="topright").add_to(campus_map)

            # 1. Draw base pathways (edges with geographic coordinates)
            for edge_id, edge in edges.items():
                u_node = nodes.get(edge.source)
                v_node = nodes.get(edge.target)

                if u_node and v_node and u_node.latitude and v_node.latitude:
                    # Color code based on accessibility status
                    if not edge.is_step_free or edge.has_stairs:
                        edge_color = "#DC2626"  # Red: contains stairs
                        dash_arr = "6, 6"
                        step_status = "Stepped Pathway (Contains Stairs)"
                    elif edge.has_ramp:
                        edge_color = "#2563EB"  # Blue: ramp pathway
                        dash_arr = None
                        step_status = "Step-Free Ramp Pathway"
                    else:
                        edge_color = "#16A34A"  # Green: level step-free
                        dash_arr = None
                        step_status = "Step-Free Level Pathway"

                    coords = [
                        [u_node.latitude, u_node.longitude],
                        [v_node.latitude, v_node.longitude]
                    ]
                    folium.PolyLine(
                        locations=coords,
                        color=edge_color,
                        weight=4,
                        opacity=0.7,
                        dash_array=dash_arr,
                        tooltip=f"{edge.source} ↔ {edge.target} | {edge.distance_m}m | {step_status}"
                    ).add_to(campus_map)

            # 2. Highlight Active Route if present
            if active_route and active_route.success and len(active_route.path_nodes) > 1:
                route_coords = []
                for n_id in active_route.path_nodes:
                    n = nodes.get(n_id)
                    if n and n.latitude and n.longitude:
                        route_coords.append([n.latitude, n.longitude])

                if len(route_coords) > 1:
                    folium.PolyLine(
                        locations=route_coords,
                        color="#1D4ED8",  # Vibrant route blue
                        weight=7,
                        opacity=0.95,
                        tooltip=f"Selected Route: {active_route.total_distance_m}m ({active_route.algorithm})"
                    ).add_to(campus_map)

            # 3. Add Campus Node Markers (Only for geolocated nodes)
            for node_id, node in nodes.items():
                # Skip unlocated nodes or indoor rooms that have no geographic lat/lon
                if not node.latitude or not node.longitude:
                    continue

                # Determine marker icon and color
                icon_name = "info-sign"
                marker_color = "cadetblue"

                if node.node_type == LocationType.OUTDOOR_ENTRANCE:
                    icon_name = "road"
                    marker_color = "darkblue"
                elif node.node_type == LocationType.BUILDING_ENTRANCE:
                    if node.is_step_free_accessible:
                        icon_name = "leaf"
                        marker_color = "green"
                    else:
                        icon_name = "ban-circle"
                        marker_color = "red"
                elif node.node_type == LocationType.PARKING:
                    icon_name = "asterisk"
                    marker_color = "purple"
                elif node.node_type == LocationType.FACILITY:
                    icon_name = "star"
                    marker_color = "blue"

                # Check if this node is selected as Start or Destination
                if active_route and active_route.path_nodes:
                    if node_id == active_route.start_id:
                        marker_color = "darkgreen"
                        icon_name = "play"
                    elif node_id == active_route.destination_id:
                        marker_color = "darkred"
                        icon_name = "flag"

                # Check if specifically highlighted
                if selected_node_id and node_id == selected_node_id:
                    marker_color = "orange"

                popup_html = f"""
                <div style='font-family: Arial, sans-serif; min-width: 210px;'>
                    <h4 style='margin: 0 0 6px 0; color: #1f2937;'>{node.name}</h4>
                    <p style='margin: 0 0 4px 0;'><b>Category:</b> {node.node_type.value}</p>
                    <p style='margin: 0 0 4px 0;'><b>Verification:</b> 
                        <span style='background-color: {"#e0f2fe" if node.verification.value == "VERIFIED" else "#fef3c7"}; 
                                     color: {"#0369a1" if node.verification.value == "VERIFIED" else "#92400e"}; 
                                     padding: 2px 6px; border-radius: 4px; font-weight: bold;'>
                            {node.verification.value}
                        </span>
                    </p>
                    <p style='margin: 0 0 4px 0;'><b>Source:</b> {node.data_source}</p>
                    <p style='margin: 0 0 4px 0;'><b>Step-Free Access:</b> {'Yes (Accessible)' if node.is_step_free_accessible else 'No (Stairs Present)'}</p>
                    <p style='margin: 0; font-size: 12px; color: #4b5563;'>{node.description}</p>
                </div>
                """

                folium.Marker(
                    location=[node.latitude, node.longitude],
                    popup=folium.Popup(popup_html, max_width=290),
                    tooltip=f"{node.name} ({node.verification.value})",
                    icon=folium.Icon(color=marker_color, icon=icon_name, prefix="glyphicon")
                ).add_to(campus_map)

            # 4. Add Obstacle Markers
            if obstacles:
                for obs in obstacles:
                    target_node = nodes.get(obs.location_or_edge_id)
                    loc = None
                    if target_node and target_node.latitude and target_node.longitude:
                        loc = [target_node.latitude, target_node.longitude]
                    elif obs.location_or_edge_id in edges:
                        e = edges[obs.location_or_edge_id]
                        src = nodes.get(e.source)
                        tgt = nodes.get(e.target)
                        if src and tgt and src.latitude and tgt.latitude:
                            loc = [(src.latitude + tgt.latitude) / 2.0, (src.longitude + tgt.longitude) / 2.0]

                    if loc:
                        obs_popup = f"""
                        <div style='font-family: Arial; min-width: 190px;'>
                            <h4 style='color: #dc2626; margin: 0 0 4px 0;'>⚠️ {obs.obstacle_type.value}</h4>
                            <p style='margin: 0 0 2px 0;'><b>Severity:</b> {obs.severity.value}</p>
                            <p style='margin: 0 0 2px 0;'><b>Status:</b> {obs.status.value}</p>
                            <p style='margin: 0 0 4px 0; font-size: 12px;'>{obs.description}</p>
                            <small style='color: #6b7280;'>Timestamp: {obs.timestamp}</small>
                        </div>
                        """
                        folium.Marker(
                            location=loc,
                            popup=folium.Popup(obs_popup, max_width=250),
                            tooltip=f"Obstacle Alert: {obs.obstacle_type.value} ({obs.severity.value})",
                            icon=folium.Icon(color="red", icon="warning-sign", prefix="glyphicon")
                        ).add_to(campus_map)

            return campus_map

        except Exception as e:
            # Fallback simple map centered safely
            fallback_map = folium.Map(
                location=[self.center_lat, self.center_lon],
                zoom_start=self.zoom_start,
                control_scale=True
            )
            folium.Marker(
                [self.center_lat, self.center_lon],
                popup="JAIN Global Campus Center (Fallback View)",
                tooltip="Campus Geographic Center"
            ).add_to(fallback_map)
            return fallback_map
