"""Interactive Floor Navigator using Plotly.

Renders clear 2D schematic layouts of the 4 demonstration floors:
- Ground Floor (Atrium, Reception, Accessible Restroom, Seminar Hall, Ramp entry)
- First Floor (CS & AI Lab 101, Data Lab 102, Faculty Cabins, Elevators)
- Second Floor (Smart Lecture 201, IoT Lab, Accessible Restroom)
- Third Floor (Dean's Suite, Capstone Projects Studio, Restroom)

Features:
- Visual geometry separated from graph topology.
- Support for background architectural image / raster overlay (preserving aspect ratio).
- Clickable nodes, zoom, pan, floor selection.
- Clear route highlighting & accessible pathway color coding (Step-free green, ramp blue, stairs dashed red).
- Obstacle markers directly overlaid on indoor floors.
- Prominent "DEMONSTRATION FLOOR PLAN — NOT AN OFFICIAL FET FLOOR PLAN" notice.
"""

import plotly.graph_objects as go
from typing import Dict, Any, List, Optional
from campus_navigator.models.core_models import (
    LocationNode,
    PathwayEdge,
    LocationType,
    ObstacleReport,
)
from campus_navigator.algorithms.routing_engine import RouteResult


class FloorPlanVisualizer:
    def __init__(self):
        # Accessible high-contrast color palette for floor elements
        self.node_colors = {
            LocationType.BUILDING_ENTRANCE: "#10B981",  # Emerald
            LocationType.CORRIDOR: "#64748B",           # Slate
            LocationType.CLASSROOM: "#3B82F6",          # Blue
            LocationType.LABORATORY: "#8B5CF6",         # Purple
            LocationType.OFFICE: "#EC4899",             # Pink
            LocationType.RESTROOM: "#06B6D4",           # Cyan
            LocationType.ELEVATOR: "#F59E0B",           # Amber (Elevators)
            LocationType.STAIRCASE: "#EF4444",          # Red (Stairs)
            LocationType.EMERGENCY_EXIT: "#DC2626",     # Crimson
            LocationType.RAMP: "#10B981",               # Emerald
        }

    def render_floor(
        self,
        floor_level: int,
        nodes: Dict[str, LocationNode],
        edges: Dict[str, PathwayEdge],
        active_route: Optional[RouteResult] = None,
        obstacles: Optional[List[ObstacleReport]] = None,
        highlight_node_id: Optional[str] = None,
        background_image_url: Optional[str] = None
    ) -> go.Figure:
        """Create a Plotly figure rendering a specific floor plan."""
        fig = go.Figure()

        # Filter nodes and edges on this specific floor
        floor_nodes = {k: v for k, v in nodes.items() if v.floor == floor_level}
        floor_node_ids = set(floor_nodes.keys())

        # 0. Optional architectural background image (preserving aspect ratio)
        if background_image_url:
            fig.add_layout_image(
                dict(
                    source=background_image_url,
                    xref="x",
                    yref="y",
                    x=0,
                    y=100,
                    sizex=100,
                    sizey=100,
                    sizing="contain",
                    opacity=0.3,
                    layer="below"
                )
            )

        # 1. Draw base corridors/pathways on this floor
        for edge_id, edge in edges.items():
            if edge.source in floor_node_ids and edge.target in floor_node_ids:
                u = floor_nodes[edge.source]
                v = floor_nodes[edge.target]
                if u.x is not None and v.x is not None:
                    # Corridor casing boundary
                    fig.add_trace(go.Scatter(
                        x=[u.x, v.x],
                        y=[u.y, v.y],
                        mode="lines",
                        line=dict(color="#CBD5E1", width=14),
                        hoverinfo="none",
                        showlegend=False
                    ))

                    # Center line color-coded by accessibility feature
                    if edge.has_stairs:
                        path_color = "#EF4444"
                        dash_style = "dot"
                        acc_label = "Stepped Corridor (Stairs)"
                    elif edge.has_ramp:
                        path_color = "#2563EB"
                        dash_style = "solid"
                        acc_label = "Accessible Ramp Corridor"
                    else:
                        path_color = "#10B981"
                        dash_style = "solid"
                        acc_label = "Step-Free Level Corridor"

                    fig.add_trace(go.Scatter(
                        x=[u.x, v.x],
                        y=[u.y, v.y],
                        mode="lines",
                        line=dict(color=path_color, width=3, dash=dash_style),
                        hovertext=f"{u.name} ↔ {v.name}<br>{edge.distance_m}m | {acc_label}",
                        hoverinfo="text",
                        showlegend=False
                    ))

        # 2. Highlight route segments on this floor
        if active_route and active_route.success and len(active_route.path_nodes) > 1:
            for i in range(len(active_route.path_nodes) - 1):
                u_id = active_route.path_nodes[i]
                v_id = active_route.path_nodes[i + 1]

                # Check if both nodes are on this floor
                if u_id in floor_node_ids and v_id in floor_node_ids:
                    u = floor_nodes[u_id]
                    v = floor_nodes[v_id]
                    fig.add_trace(go.Scatter(
                        x=[u.x, v.x],
                        y=[u.y, v.y],
                        mode="lines+markers",
                        line=dict(color="#1D4ED8", width=7),
                        marker=dict(size=11, color="#1E40AF"),
                        hoverinfo="text",
                        hovertext=f"Active Step: {u.name} → {v.name}",
                        showlegend=False
                    ))
                # Check for elevator / stair transitions departing or arriving on this floor
                elif u_id in floor_node_ids or v_id in floor_node_ids:
                    node_here = floor_nodes.get(u_id) or floor_nodes.get(v_id)
                    trans_label = "Take Elevator (Vertical Transfer)" if "ELEV" in f"{u_id}_{v_id}" else "Use Stairs (Floor Transfer)"
                    fig.add_trace(go.Scatter(
                        x=[node_here.x],
                        y=[node_here.y],
                        mode="markers+text",
                        marker=dict(size=24, color="#F59E0B", symbol="hexagon"),
                        text=[f"🛗 {trans_label}" if "ELEV" in f"{u_id}_{v_id}" else f"🪜 {trans_label}"],
                        textposition="top center",
                        textfont=dict(size=12, color="#92400E", family="Arial Black"),
                        hoverinfo="text",
                        hovertext=f"Floor Transfer: {trans_label}",
                        showlegend=False
                    ))

        # 3. Plot Floor Nodes
        for n_type in LocationType:
            typed_nodes = [n for n in floor_nodes.values() if n.node_type == n_type]
            if not typed_nodes:
                continue

            x_vals = [n.x for n in typed_nodes]
            y_vals = [n.y for n in typed_nodes]
            texts = [n.name.split(" - ")[-1] if " - " in n.name else n.name for n in typed_nodes]
            ids = [n.id for n in typed_nodes]

            hover_descs = [
                f"<b>{n.name}</b><br>ID: <code>{n.id}</code><br>Category: {n.node_type.value}<br>Step-Free: {'Yes' if n.is_step_free_accessible else 'No'}<br>{n.description}"
                for n in typed_nodes
            ]

            fig.add_trace(go.Scatter(
                x=x_vals,
                y=y_vals,
                mode="markers+text",
                marker=dict(
                    size=18,
                    color=self.node_colors.get(n_type, "#64748B"),
                    line=dict(width=2, color="#FFFFFF")
                ),
                text=texts,
                textposition="bottom center",
                textfont=dict(size=11, color="#1E293B"),
                hovertext=hover_descs,
                hoverinfo="text",
                customdata=ids,
                name=n_type.value.replace("_", " ").title()
            ))

        # 4. Highlight obstacles located on this floor
        if obstacles:
            for obs in obstacles:
                obs_node = floor_nodes.get(obs.location_or_edge_id)
                obs_loc = None
                if obs_node and obs_node.x is not None and obs_node.y is not None:
                    obs_loc = (obs_node.x, obs_node.y)
                elif obs.location_or_edge_id in edges:
                    e = edges[obs.location_or_edge_id]
                    if e.source in floor_nodes and e.target in floor_nodes:
                        u = floor_nodes[e.source]
                        v = floor_nodes[e.target]
                        if u.x is not None and v.x is not None:
                            obs_loc = ((u.x + v.x) / 2.0, (u.y + v.y) / 2.0)

                if obs_loc:
                    fig.add_trace(go.Scatter(
                        x=[obs_loc[0]],
                        y=[obs_loc[1]],
                        mode="markers+text",
                        marker=dict(size=22, color="#DC2626", symbol="x"),
                        text=[f"⚠️ {obs.obstacle_type.value}"],
                        textposition="top center",
                        textfont=dict(size=10, color="#991B1B"),
                        hoverinfo="text",
                        hovertext=f"<b>Obstacle: {obs.obstacle_type.value}</b><br>Severity: {obs.severity.value}<br>{obs.description}",
                        showlegend=False
                    ))

        # 5. Highlight currently selected focus node
        if highlight_node_id and highlight_node_id in floor_nodes:
            hn = floor_nodes[highlight_node_id]
            fig.add_trace(go.Scatter(
                x=[hn.x],
                y=[hn.y],
                mode="markers",
                marker=dict(size=30, color="rgba(239, 68, 68, 0.35)", line=dict(color="#EF4444", width=3)),
                hoverinfo="none",
                showlegend=False
            ))

        # 6. Prominent Demonstration notice
        fig.add_annotation(
            text="DEMONSTRATION FLOOR PLAN — NOT AN OFFICIAL FET FLOOR PLAN",
            xref="paper", yref="paper",
            x=0.5, y=1.05,
            showarrow=False,
            font=dict(size=12, color="#991B1B", family="Arial Black"),
            bgcolor="#FEE2E2",
            bordercolor="#F87171",
            borderwidth=1,
            borderpad=4
        )

        floor_names = {0: "Ground Floor (G)", 1: "First Floor (1F)", 2: "Second Floor (2F)", 3: "Third Floor (3F)"}
        current_floor_name = floor_names.get(floor_level, f"Floor {floor_level}")

        fig.update_layout(
            title=f"Faculty of Engineering & Technology — {current_floor_name}",
            xaxis=dict(showgrid=True, zeroline=False, showticklabels=False, range=[0, 100]),
            yaxis=dict(showgrid=True, zeroline=False, showticklabels=False, range=[0, 100], scaleanchor="x", scaleratio=1),
            plot_bgcolor="#F8FAFC",
            paper_bgcolor="#FFFFFF",
            margin=dict(l=20, r=20, t=55, b=25),
            legend=dict(orientation="h", yanchor="bottom", y=-0.22, xanchor="center", x=0.5),
            height=620
        )

        return fig
