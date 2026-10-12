"""
Campus Accessibility Analytics Engine.

Provides deep, data-driven analytical metrics using Pandas and Plotly:
1. Obstacle reports by category.
2. Active versus resolved reports.
3. Locations with repeated reports.
4. Pathways requiring accessibility verification.
5. Buildings with incomplete accessibility information.
6. Average time between reporting and resolution (when timestamps exist).
7. Historical report trends (by date).
8. Data completeness indicators (% of pathways with verified surface, measured width, and step-free status).

Ethical and Scientific Distinctions:
- Clearly distinguishes a high volume of reports from a verified accessibility defect.
- A location with zero reports is NEVER automatically considered accessible (it may simply be uninspected).
- Never invents historical statistics or simulated records.
- Flags unverified/provisional segments that require campus inspection.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import datetime
from typing import Dict, Any, List, Optional
from campus_navigator.models.core_models import (
    ObstacleReport,
    ObstacleStatus,
    VerificationStatus,
    LocationNode,
    PathwayEdge,
    SurfaceType
)


class CampusAnalyticsEngine:
    """Processes graph and obstacle data into auditable analytics metrics and visualizations."""

    def __init__(self, nodes: Dict[str, LocationNode], edges: Dict[str, PathwayEdge], reports: List[ObstacleReport]):
        self.nodes = nodes
        self.edges = edges
        self.reports = reports

    # ---------------------------------------------------------
    # 1. OBSTACLES BY CATEGORY
    # ---------------------------------------------------------
    def get_reports_by_category(self) -> pd.DataFrame:
        if not self.reports:
            return pd.DataFrame(columns=["Category", "Count"])
        data = [r.obstacle_type.value for r in self.reports]
        df = pd.Series(data).value_counts().reset_index()
        df.columns = ["Category", "Count"]
        return df

    def plot_reports_by_category(self) -> go.Figure:
        df = self.get_reports_by_category()
        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="No obstacle reports recorded")
            return fig
        fig = px.bar(
            df,
            x="Category",
            y="Count",
            color="Count",
            color_continuous_scale="Reds",
            title="Obstacle Reports by Category",
            labels={"Count": "Report Count", "Category": "Obstacle Type"}
        )
        fig.update_layout(showlegend=False, margin=dict(t=40, b=30, l=40, r=20))
        return fig

    # ---------------------------------------------------------
    # 2. ACTIVE VS RESOLVED STATUS
    # ---------------------------------------------------------
    def get_active_vs_resolved_status(self) -> pd.DataFrame:
        if not self.reports:
            return pd.DataFrame(columns=["Status", "Count"])
        data = [r.status.value for r in self.reports]
        df = pd.Series(data).value_counts().reset_index()
        df.columns = ["Status", "Count"]
        return df

    def plot_active_vs_resolved(self) -> go.Figure:
        df = self.get_active_vs_resolved_status()
        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="No obstacle reports recorded")
            return fig
        color_map = {
            "SUBMITTED": "#f59e0b",
            "UNDER_REVIEW": "#3b82f6",
            "VERIFIED": "#ef4444",
            "RESOLVED": "#10b981",
            "REJECTED": "#94a3b8"
        }
        fig = px.pie(
            df,
            names="Status",
            values="Count",
            title="Report Lifecycle Distribution (Active vs. Resolved)",
            color="Status",
            color_discrete_map=color_map,
            hole=0.4
        )
        fig.update_layout(margin=dict(t=40, b=30, l=30, r=30))
        return fig

    # ---------------------------------------------------------
    # 3. REPEATED REPORT LOCATIONS
    # ---------------------------------------------------------
    def get_locations_with_repeated_reports(self) -> pd.DataFrame:
        """Identifies physical locations or pathways that have accumulated multiple reports."""
        if not self.reports:
            return pd.DataFrame(columns=["Target ID", "Name", "Total Reports", "Verified Reports", "Pending Reports"])

        target_records = []
        for r in self.reports:
            target_records.append({
                "target_id": r.location_or_edge_id,
                "is_verified": r.status == ObstacleStatus.VERIFIED or r.verification_status == VerificationStatus.VERIFIED,
                "is_pending": r.status in (ObstacleStatus.SUBMITTED, ObstacleStatus.UNDER_REVIEW)
            })
        df_raw = pd.DataFrame(target_records)
        grouped = df_raw.groupby("target_id").agg(
            total_reports=("target_id", "count"),
            verified_reports=("is_verified", "sum"),
            pending_reports=("is_pending", "sum")
        ).reset_index()

        # Add readable name if it exists in nodes
        def get_readable_name(tid):
            if tid in self.nodes:
                return self.nodes[tid].name
            elif tid in self.edges:
                e = self.edges[tid]
                src_n = self.nodes.get(e.source, e.source).name if e.source in self.nodes else e.source
                tgt_n = self.nodes.get(e.target, e.target).name if e.target in self.nodes else e.target
                return f"Pathway: {src_n} ↔ {tgt_n}"
            return tid

        grouped["Name"] = grouped["target_id"].apply(get_readable_name)
        grouped = grouped.rename(columns={
            "target_id": "Target ID",
            "total_reports": "Total Reports",
            "verified_reports": "Verified Reports",
            "pending_reports": "Pending Reports"
        }).sort_values(by="Total Reports", ascending=False)
        return grouped

    # ---------------------------------------------------------
    # 4. PATHWAYS REQUIRING VERIFICATION
    # ---------------------------------------------------------
    def get_pathways_requiring_verification(self) -> pd.DataFrame:
        """Finds pathways with PROVISIONAL or DEMONSTRATION status or missing audit metrics."""
        rows = []
        for e in self.edges.values():
            needs_audit = False
            reasons = []

            if e.verification in (VerificationStatus.PROVISIONAL, VerificationStatus.DEMONSTRATION):
                needs_audit = True
                reasons.append(f"Status is {e.verification.value}")

            if e.surface == SurfaceType.UNKNOWN:
                needs_audit = True
                reasons.append("Surface material unknown")

            if e.width_cm is None:
                needs_audit = True
                reasons.append("Door/corridor width unmeasured")

            if needs_audit:
                src_name = self.nodes[e.source].name if e.source in self.nodes else e.source
                tgt_name = self.nodes[e.target].name if e.target in self.nodes else e.target
                rows.append({
                    "Pathway ID": e.id,
                    "From Location": src_name,
                    "To Location": tgt_name,
                    "Distance (m)": e.distance_m,
                    "Status": e.verification.value,
                    "Step-Free": "Yes" if e.is_step_free else "No (Stairs)",
                    "Audit Reasons": ", ".join(reasons)
                })
        return pd.DataFrame(rows)

    # ---------------------------------------------------------
    # 5. BUILDINGS WITH INCOMPLETE ACCESSIBILITY DATA
    # ---------------------------------------------------------
    def get_buildings_data_completeness(self) -> pd.DataFrame:
        """Analyzes indoor building clusters for missing widths, tactile tags, or demo layouts."""
        bldg_stats: Dict[str, Dict[str, Any]] = {}

        for n in self.nodes.values():
            b_id = n.building_id or n.indoor_building_id or ("Outdoor Campus" if not n.is_indoor() else "Unknown Building")
            if b_id not in bldg_stats:
                bldg_stats[b_id] = {
                    "total_nodes": 0,
                    "verified_nodes": 0,
                    "demo_or_prov_nodes": 0,
                    "measured_widths": 0,
                    "tactile_surveyed": 0,
                }
            bldg_stats[b_id]["total_nodes"] += 1
            if n.verification == VerificationStatus.VERIFIED:
                bldg_stats[b_id]["verified_nodes"] += 1
            else:
                bldg_stats[b_id]["demo_or_prov_nodes"] += 1

            if n.door_width_cm is not None:
                bldg_stats[b_id]["measured_widths"] += 1
            if n.has_tactile_paving is not None:
                bldg_stats[b_id]["tactile_surveyed"] += 1

        rows = []
        for b_id, st in bldg_stats.items():
            tot = st["total_nodes"]
            verif_pct = (st["verified_nodes"] / tot * 100) if tot else 0.0
            width_pct = (st["measured_widths"] / tot * 100) if tot else 0.0
            tact_pct = (st["tactile_surveyed"] / tot * 100) if tot else 0.0
            rows.append({
                "Building / Zone": b_id,
                "Total Nodes": tot,
                "Verified Nodes": st["verified_nodes"],
                "Verification Completeness (%)": round(verif_pct, 1),
                "Width Measurement (%)": round(width_pct, 1),
                "Tactile Surveyed (%)": round(tact_pct, 1),
                "Inspection Priority": "HIGH" if verif_pct < 50.0 else ("MEDIUM" if width_pct < 80.0 else "LOW")
            })
        return pd.DataFrame(rows).sort_values(by="Verification Completeness (%)")

    # ---------------------------------------------------------
    # 6. AVERAGE TIME BETWEEN REPORTING AND RESOLUTION
    # ---------------------------------------------------------
    def get_resolution_time_metrics(self) -> Dict[str, Any]:
        """Calculates actual elapsed time between reporting and resolution for resolved records."""
        resolved_durations_hours = []

        for r in self.reports:
            if r.status == ObstacleStatus.RESOLVED and r.resolved_at and r.timestamp:
                try:
                    # Parse ISO timestamps
                    t_start = datetime.datetime.fromisoformat(r.timestamp.replace("Z", "+00:00"))
                    t_end = datetime.datetime.fromisoformat(r.resolved_at.replace("Z", "+00:00"))
                    diff_sec = (t_end - t_start).total_seconds()
                    if diff_sec >= 0:
                        resolved_durations_hours.append(diff_sec / 3600.0)
                except Exception:
                    pass

        if not resolved_durations_hours:
            return {
                "has_data": False,
                "resolved_count_with_timestamps": 0,
                "mean_hours": None,
                "median_hours": None,
                "min_hours": None,
                "max_hours": None
            }

        s = pd.Series(resolved_durations_hours)
        return {
            "has_data": True,
            "resolved_count_with_timestamps": len(resolved_durations_hours),
            "mean_hours": round(s.mean(), 2),
            "median_hours": round(s.median(), 2),
            "min_hours": round(s.min(), 2),
            "max_hours": round(s.max(), 2)
        }

    # ---------------------------------------------------------
    # 7. HISTORICAL REPORT TRENDS
    # ---------------------------------------------------------
    def get_historical_trends_by_date(self) -> pd.DataFrame:
        """Aggregates reports by calendar date based on actual stored timestamps."""
        if not self.reports:
            return pd.DataFrame(columns=["Date", "Submissions"])

        dates = []
        for r in self.reports:
            try:
                d_str = r.timestamp[:10]  # YYYY-MM-DD
                dates.append(d_str)
            except Exception:
                pass

        if not dates:
            return pd.DataFrame(columns=["Date", "Submissions"])

        s = pd.Series(dates).value_counts().sort_index().reset_index()
        s.columns = ["Date", "Submissions"]
        return s

    def plot_historical_trends(self) -> go.Figure:
        df = self.get_historical_trends_by_date()
        if df.empty:
            fig = go.Figure()
            fig.update_layout(title="No chronological report data available")
            return fig

        fig = px.line(
            df,
            x="Date",
            y="Submissions",
            markers=True,
            title="Obstacle Reports Ingestion Timeline",
            labels={"Submissions": "Daily Submissions", "Date": "Date Recorded"}
        )
        fig.update_layout(margin=dict(t=40, b=30, l=40, r=20))
        return fig

    # ---------------------------------------------------------
    # 8. DATA COMPLETENESS & TRANSPARENCY SCORECARD
    # ---------------------------------------------------------
    def get_data_completeness_scorecard(self) -> Dict[str, Any]:
        """Calculates global dataset completeness metrics."""
        total_nodes = len(self.nodes)
        total_edges = len(self.edges)

        verified_nodes = sum(1 for n in self.nodes.values() if n.verification == VerificationStatus.VERIFIED)
        geolocated_outdoor = sum(1 for n in self.nodes.values() if not n.is_indoor() and n.is_geolocated())
        total_outdoor = sum(1 for n in self.nodes.values() if not n.is_indoor())

        verified_edges = sum(1 for e in self.edges.values() if e.verification == VerificationStatus.VERIFIED)
        known_surfaces = sum(1 for e in self.edges.values() if e.surface != SurfaceType.UNKNOWN)
        measured_widths = sum(1 for e in self.edges.values() if e.width_cm is not None)

        return {
            "total_nodes": total_nodes,
            "node_verification_pct": round((verified_nodes / total_nodes * 100), 1) if total_nodes else 0.0,
            "outdoor_gps_coverage_pct": round((geolocated_outdoor / total_outdoor * 100), 1) if total_outdoor else 0.0,
            "total_pathways": total_edges,
            "pathway_verification_pct": round((verified_edges / total_edges * 100), 1) if total_edges else 0.0,
            "surface_material_known_pct": round((known_surfaces / total_edges * 100), 1) if total_edges else 0.0,
            "corridor_width_measured_pct": round((measured_widths / total_edges * 100), 1) if total_edges else 0.0
        }
