"""Accessible Campus Navigator - Streamlit Application.

Smart Indoor & Outdoor Accessibility Navigation System
JAIN (Deemed-to-be University)
Faculty of Engineering and Technology (FET)
JAIN Global Campus, Jakkasandra Post, Kanakapura Road, Ramanagara District, Karnataka, India.

TAGLINE: "Every Destination Accessible. Every Student Included."
"""

import os
import streamlit as st
import pandas as pd
import datetime
from campus_navigator.models.core_models import (
    AccessibilityProfile,
    VerificationStatus,
    LocationType,
    SurfaceType,
    ObstacleReport,
    ObstacleType,
    ObstacleSeverity,
    ObstacleStatus,
)
from campus_navigator.algorithms.graph_builder import CampusGraph
from campus_navigator.algorithms.routing_engine import RoutingEngine, RouteResult
from campus_navigator.algorithms.analytics import CampusAnalyticsEngine
from campus_navigator.db.obstacle_db import ObstacleDB
from campus_navigator.data.editor import CampusDataEditor
from campus_navigator.ui.map_builder import OutdoorMapBuilder
from campus_navigator.ui.floor_visualizer import FloorPlanVisualizer
from campus_navigator.ui.styles import NAVIGATOR_CUSTOM_CSS
from streamlit_folium import st_folium

# -------------------------------------------------------------
# PAGE CONFIGURATION & DESIGN SYSTEM
# -------------------------------------------------------------
st.set_page_config(
    page_title="Accessible Campus Navigator | JAIN Global Campus (FET)",
    page_icon="♿",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(NAVIGATOR_CUSTOM_CSS, unsafe_allow_html=True)

# -------------------------------------------------------------
# STATE INITIALIZATION
# -------------------------------------------------------------
if "obstacle_db" not in st.session_state:
    st.session_state.obstacle_db = ObstacleDB()

if "graph" not in st.session_state:
    st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
    st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)

if "editor" not in st.session_state:
    st.session_state.editor = CampusDataEditor()

cg: CampusGraph = st.session_state.graph
re: RoutingEngine = st.session_state.routing
db: ObstacleDB = st.session_state.obstacle_db
editor: CampusDataEditor = st.session_state.editor

# Page navigation state for seamless cross-page redirects
if "nav_page" not in st.session_state:
    st.session_state.nav_page = "🏠 Home Dashboard"

# -------------------------------------------------------------
# SIDEBAR: ACCESSIBLE NAVIGATION & MOBILITY PROFILE
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("## ♿ Campus Navigator")
    st.markdown(
        "**JAIN (Deemed-to-be University)**<br>"
        "<span style='color: #94a3b8; font-size: 13px;'>Faculty of Engineering & Technology (FET)<br>"
        "JAIN Global Campus, Jakkasandra, Karnataka</span>",
        unsafe_allow_html=True
    )
    st.markdown("---")

    menu_options = [
        "🏠 Home Dashboard",
        "🗺️ Outdoor Campus Map",
        "🏢 Indoor Floor Navigator",
        "🧭 Find Accessible Route",
        "⚠️ Report an Obstacle",
        "📖 Campus Directory",
        "📊 Accessibility Analytics",
        "⚙️ Administration"
    ]

    # Synchronize radio with session state navigation
    current_index = menu_options.index(st.session_state.nav_page) if st.session_state.nav_page in menu_options else 0
    selected_page = st.radio(
        "Navigation Menu",
        menu_options,
        index=current_index,
        key="sidebar_navigation_radio"
    )
    st.session_state.nav_page = selected_page

    st.markdown("---")
    st.markdown("### 🦽 Mobility Profile")
    profile_type = st.selectbox(
        "Select User Profile",
        ["Wheelchair User", "Limited Mobility", "Avoid Stairs", "General Walking", "Custom Configuration"],
        key="sidebar_profile_selector"
    )

    if profile_type == "Wheelchair User":
        active_profile = AccessibilityProfile.wheelchair_user()
    elif profile_type == "Limited Mobility":
        active_profile = AccessibilityProfile.limited_mobility()
    elif profile_type == "Avoid Stairs":
        active_profile = AccessibilityProfile.avoid_stairs()
    elif profile_type == "General Walking":
        active_profile = AccessibilityProfile.general_walking()
    else:
        st.caption("Customize constraints:")
        permit_stairs = st.checkbox("Permit Stairs", value=False)
        step_free = st.checkbox("Require Step-Free Access", value=True)
        prefer_ramps = st.checkbox("Prefer Ramps", value=True)
        allow_elev = st.checkbox("Allow Elevators", value=True)
        opt_for = st.radio("Optimize For", ["distance", "time"], horizontal=True)
        active_profile = AccessibilityProfile(
            name="Custom Profile",
            permit_stairs=permit_stairs,
            require_step_free=step_free,
            prefer_ramps=prefer_ramps,
            allow_elevators=allow_elev,
            optimize_for=opt_for
        )

    st.session_state.active_profile = active_profile

    st.markdown(
        f"<div style='background: #111e3b; padding: 10px 12px; border-radius: 8px; font-size: 12px; margin-top: 8px; border: 1px solid #1e293b;'>"
        f"<b style='color: #60a5fa;'>Active Constraints:</b><br>"
        f"• <b>Stairs:</b> {'Allowed' if active_profile.permit_stairs else '<span style=\"color:#f87171;\">Prohibited</span>'}<br>"
        f"• <b>Step-Free:</b> {'<span style=\"color:#4ade80;\">Mandatory</span>' if active_profile.require_step_free else 'Optional'}<br>"
        f"• <b>Elevators:</b> {'Enabled' if active_profile.allow_elevators else 'Disabled'}<br>"
        f"• <b>Objective:</b> Minimum {active_profile.optimize_for}"
        f"</div>",
        unsafe_allow_html=True
    )

    st.markdown("---")
    st.markdown(
        "<div style='font-size: 11px; color: #94a3b8; line-height: 1.5;'>"
        "<b>Official Institutional References:</b><br>"
        "• <a href='https://set.jainuniversity.ac.in/contacts' target='_blank' style='color: #38bdf8;'>FET Campus Contacts</a><br>"
        "• <a href='https://www.jainuniversity.ac.in/contact/top-indian-university-with-best-colleges-with-location-maps' target='_blank' style='color: #38bdf8;'>JAIN Location Maps</a><br>"
        "• <a href='https://cet.jainuniversity.ac.in/Location-Map.htm' target='_blank' style='color: #38bdf8;'>CET Campus Directions</a>"
        "</div>",
        unsafe_allow_html=True
    )


# =============================================================
# PAGE 1: HOME DASHBOARD
# =============================================================
if selected_page == "🏠 Home Dashboard":
    st.markdown("""
    <div class="campus-hero-banner">
        <div class="campus-hero-title">ACCESSIBLE CAMPUS NAVIGATOR</div>
        <div class="campus-hero-subtitle">Smart Indoor & Outdoor Accessibility Navigation System — JAIN Global Campus (FET)</div>
        <div class="campus-hero-tagline">"Every Destination Accessible. Every Student Included."</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="integrity-notice">
        <b>GEOGRAPHIC INTEGRITY & DEMONSTRATION NOTICE:</b><br>
        • <b>Real Geographic Campus Data:</b> Arterial roads, perimeter gates, and GPS coordinates are referenced from official JAIN University publications and verified OpenStreetMap data for Jakkasandra, Kanakapura Road (<code>12.6482° N, 77.4418° E</code>).<br>
        • <b>Demonstration Floor Plan:</b> Indoor layouts for the Faculty of Engineering and Technology (FET) use an illustrative four-floor architectural demonstration model (<b>NOT an official FET building blueprint</b>) designed to be seamlessly replaced with verified blueprints when authorized.<br>
        • <b>Verification Standards:</b> Unverified pathways remain explicitly marked as <span class="badge-provisional">PROVISIONAL</span>.
    </div>
    """, unsafe_allow_html=True)

    # Campus Selector
    c_col1, c_col2 = st.columns([2, 1])
    with c_col1:
        st.selectbox(
            "Campus Selection",
            ["JAIN Global Campus — Faculty of Engineering & Technology (FET), Kanakapura Rd, Karnataka (Active)"]
        )
    with c_col2:
        st.write("")
        st.markdown(
            "<div style='padding-top: 8px;'><span class='badge-verified'>VERIFIED REAL CAMPUS BOUNDARY</span></div>",
            unsafe_allow_html=True
        )

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("Total Campus Nodes", len(cg.nodes), help="Total outdoor facilities, gates, and indoor demonstration rooms")
    with m2:
        st.metric("Navigable Pathways", len(cg.edges), help="Step-free walkways, ramps, corridors, and stairs in the active graph")
    with m3:
        active_blocking = len(db.get_active_blocking_obstacles())
        st.metric("Active Obstacle Alerts", active_blocking, delta=f"{active_blocking} actively blocking" if active_blocking else "All paths clear", delta_color="inverse" if active_blocking else "normal")
    with m4:
        st.metric("Demonstration Floors", 4, help="Ground, 1st, 2nd, and 3rd floors of the FET Complex demonstration layout")

    st.markdown("---")

    # Quick Route & Search Destination
    q_left, q_right = st.columns([1, 1])

    with q_left:
        st.markdown("### ⚡ Quick Route Finder")
        with st.form("home_quick_route_form"):
            all_sorted_nodes = sorted(cg.nodes.values(), key=lambda n: n.name)
            node_map = {f"{n.name} ({'Floor ' + str(n.floor) if n.is_indoor() else 'Outdoor'})": n.id for n in all_sorted_nodes}

            quick_start = st.selectbox("Starting Location", list(node_map.keys()), index=0)
            quick_dest = st.selectbox("Destination", list(node_map.keys()), index=min(len(node_map)-1, 10))

            quick_calc = st.form_submit_button("🚀 Find Route Now", type="primary", use_container_width=True)
            if quick_calc:
                st.session_state.pending_start_id = node_map[quick_start]
                st.session_state.pending_dest_id = node_map[quick_dest]
                st.session_state.nav_page = "🧭 Find Accessible Route"
                st.rerun()

    with q_right:
        st.markdown("### 🔍 Search Destination & Facilities")
        home_search = st.text_input("Search classrooms, labs, parking, or entrances", placeholder="E.g., CS Lab, Library, Ramp, Parking")
        if home_search.strip():
            matches = [n for n in cg.nodes.values() if home_search.lower() in n.name.lower() or home_search.lower() in n.description.lower()]
            if matches:
                st.markdown(f"Found **{len(matches)}** matching locations:")
                for m in matches[:4]:
                    tag = "badge-verified" if m.verification == VerificationStatus.VERIFIED else ("badge-provisional" if m.verification == VerificationStatus.PROVISIONAL else "badge-demonstration")
                    st.markdown(
                        f"<div class='nav-card' style='padding: 10px 14px; margin-bottom: 8px;'>"
                        f"<b>{m.name}</b> <span class='{tag}'>{m.verification.value}</span><br>"
                        f"<small style='color: #64748b;'>{'Floor ' + str(m.floor) if m.is_indoor() else 'Outdoor Campus'} | Step-Free: {'Yes' if m.is_step_free_accessible else 'No'}</small>"
                        f"</div>",
                        unsafe_allow_html=True
                    )
            else:
                st.info("No destinations matched your query.")
        else:
            st.caption("Enter a search term above to quickly locate facilities across outdoor campus grounds and indoor FET floors.")

    st.markdown("---")

    # Active Obstacle Summary & Quick Navigation Shortcuts
    o_col, s_col = st.columns([1, 1])

    with o_col:
        st.markdown("### ⚠️ Active Obstacles Summary")
        active_obs = db.get_active_blocking_obstacles()
        if not active_obs:
            st.success("🟢 No critical or high-severity obstacles currently impairing campus navigation.")
        else:
            for obs in active_obs[:3]:
                st.markdown(
                    f"<div class='nav-card' style='border-left: 4px solid #dc2626; padding: 12px 16px;'>"
                    f"<b>{obs.id}</b> — <span class='badge-demonstration'>BLOCKING</span><br>"
                    f"<b>Type:</b> {obs.obstacle_type.value} | <b>Target:</b> <code>{obs.location_or_edge_id}</code><br>"
                    f"<span style='color: #475569; font-size: 13px;'>{obs.description}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )
            if len(active_obs) > 3:
                st.caption(f"+ {len(active_obs) - 3} additional obstacle reports recorded in database.")

    with s_col:
        st.markdown("### 🧭 Direct Navigation Shortcuts")
        sc1, sc2 = st.columns(2)
        with sc1:
            if st.button("🗺️ Open Outdoor Map", use_container_width=True):
                st.session_state.nav_page = "🗺️ Outdoor Campus Map"
                st.rerun()
            if st.button("🏢 Explore FET Floors", use_container_width=True):
                st.session_state.nav_page = "🏢 Indoor Floor Navigator"
                st.rerun()
        with sc2:
            if st.button("⚠️ Report an Obstacle", use_container_width=True):
                st.session_state.nav_page = "⚠️ Report an Obstacle"
                st.rerun()
            if st.button("📖 Campus Directory", use_container_width=True):
                st.session_state.nav_page = "📖 Campus Directory"
                st.rerun()


# =============================================================
# PAGE 2: OUTDOOR CAMPUS MAP
# =============================================================
elif selected_page == "🗺️ Outdoor Campus Map":
    st.markdown("## 🗺️ Outdoor Campus Geographic Map")
    st.caption("JAIN Global Campus, Jakkasandra Post, Kanakapura Road, Ramanagara District, Karnataka (12.6482° N, 77.4418° E)")

    ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 1, 1])

    outdoor_nodes = {k: v for k, v in cg.nodes.items() if not v.is_indoor()}
    geolocated_nodes = {k: v for k, v in outdoor_nodes.items() if v.is_geolocated()}
    unlocated_nodes = {k: v for k, v in outdoor_nodes.items() if not v.is_geolocated()}

    with ctrl_col1:
        search_loc = st.selectbox(
            "🔍 Search & Center On Destination",
            ["Default (Full Campus Overview)"] + [f"{n.name} ({n.verification.value})" for n in geolocated_nodes.values()],
            key="outdoor_search_select"
        )
    with ctrl_col2:
        reset_view = st.button("🔄 Reset Campus View", use_container_width=True)
    with ctrl_col3:
        show_unlocated = st.checkbox("Show Unlocated Facilities", value=True)

    selected_id = None
    if not reset_view and search_loc != "Default (Full Campus Overview)":
        clean_name = search_loc.split(" (")[0]
        selected_id = next((k for k, v in geolocated_nodes.items() if v.name == clean_name), None)

    # Point-to-Point Route Generator on Map
    with st.expander("🧭 Generate Outdoor Route Directly on Map", expanded=False):
        og_c1, og_c2, og_c3 = st.columns([2, 2, 1])
        with og_c1:
            og_start = st.selectbox("Map Route Origin", [n.name for n in outdoor_nodes.values()], index=0, key="map_rt_start")
            og_start_id = next(n.id for n in outdoor_nodes.values() if n.name == og_start)
        with og_c2:
            og_dest = st.selectbox("Map Route Destination", [n.name for n in outdoor_nodes.values()], index=min(len(outdoor_nodes)-1, 3), key="map_rt_dest")
            og_dest_id = next(n.id for n in outdoor_nodes.values() if n.name == og_dest)
        with og_c3:
            st.write("")
            st.write("")
            run_map_route = st.button("Calculate", type="primary", use_container_width=True)

        if run_map_route:
            st.session_state.map_active_route = re.find_route(og_start_id, og_dest_id, active_profile)

    map_col, info_col = st.columns([3, 1])

    with info_col:
        st.markdown("### 📋 Map Legend")
        st.markdown("""
        - 🟢 **Solid Green:** Level Step-Free Pathway
        - 🔵 **Solid Blue:** Accessible Ramp Pathway
        - 🔴 **Dashed Red:** Stepped Path (Contains Stairs)
        - ⚠️ **Red Marker:** Reported Obstacle
        - 🏛️ **Dark Blue:** Main Entrance Gateway
        - 🚗 **Purple:** Accessible Parking Zone
        """)

        if selected_id:
            st.markdown("---")
            sel_obj = cg.nodes[selected_id]
            st.markdown(
                f"<div class='nav-card' style='border-left: 4px solid #2563eb;'>"
                f"<h4 style='margin: 0 0 4px 0;'>{sel_obj.name}</h4>"
                f"<span class='badge-{sel_obj.verification.value.lower()}'>{sel_obj.verification.value}</span><br>"
                f"<small><b>Source:</b> {sel_obj.data_source}</small><br>"
                f"<small><b>Step-Free:</b> {'Yes' if sel_obj.is_step_free_accessible else 'No (Stairs present)'}</small>"
                f"<p style='margin: 6px 0 0 0; font-size: 13px;'>{sel_obj.description}</p>"
                f"</div>",
                unsafe_allow_html=True
            )

        if show_unlocated and unlocated_nodes:
            st.markdown("---")
            st.markdown("### 📍 Unlocated Destinations")
            st.caption("Destinations in the campus directory without surveyed GPS coordinates:")
            for un_id, un_node in unlocated_nodes.items():
                st.markdown(f"• **{un_node.name}**\n  *(Status: {un_node.verification.value} | {un_node.data_source})*")

    with map_col:
        try:
            map_builder = OutdoorMapBuilder()
            active_rt = st.session_state.get("map_active_route") if "map_active_route" in st.session_state else None
            campus_folium_map = map_builder.create_campus_map(
                nodes=cg.nodes,
                edges=cg.edges,
                active_route=active_rt,
                obstacles=db.get_all_reports(),
                selected_node_id=selected_id if not reset_view else None
            )
            st_folium(campus_folium_map, width="100%", height=620, key="outdoor_campus_map_view")
        except Exception:
            st.error(
                "⚠️ **External Map Tiles Unavailable:** Unable to connect to OpenStreetMap tile server. "
                "The application remains fully functional in offline mode. Below is the campus location directory:"
            )
            fallback_rows = [
                {"Location": n.name, "Type": n.node_type.value, "Coordinates": f"{n.latitude}, {n.longitude}" if n.is_geolocated() else "Unlocated", "Status": n.verification.value}
                for n in outdoor_nodes.values()
            ]
            st.dataframe(pd.DataFrame(fallback_rows), use_container_width=True)


# =============================================================
# PAGE 3: INDOOR NAVIGATOR
# =============================================================
elif selected_page == "🏢 Indoor Floor Navigator":
    st.markdown("## 🏢 Indoor Floor Navigator")
    st.markdown("""
    <div class="integrity-notice">
        <span class="demo-watermark">Demonstration Floor Plan</span><br>
        <b>NOT AN OFFICIAL FET FLOOR PLAN.</b><br>
        This four-floor interactive model illustrates indoor accessibility pathfinding, elevators, stairs, classrooms, laboratories, and emergency exits for the Faculty of Engineering & Technology (FET). It is ready for official architectural replacement.
    </div>
    """, unsafe_allow_html=True)

    in_ctrl1, in_ctrl2 = st.columns([1, 1])
    with in_ctrl1:
        buildings_data = cg.loader.load_buildings()
        b_list = [b["building_name"] for b in buildings_data.get("buildings", [])] or ["FET Complex"]
        selected_bldg = st.selectbox("Select Building", b_list)

    floor_names_map = {0: "Ground Floor (G)", 1: "First Floor (1F)", 2: "Second Floor (2F)", 3: "Third Floor (3F)"}
    indoor_nodes_list = [n for n in cg.nodes.values() if n.is_indoor()]

    with in_ctrl2:
        in_nav_mode = st.radio("Navigation Mode", ["Inspect Floor Map", "Indoor Point-to-Point Route"], horizontal=True)

    if in_nav_mode == "Indoor Point-to-Point Route":
        in_r1, in_r2, in_r3, in_r4 = st.columns(4)
        with in_r1:
            start_floor_sel = st.selectbox("Start Floor", [0, 1, 2, 3], format_func=lambda x: floor_names_map[x], key="in_start_floor")
            start_floor_nodes = [n for n in indoor_nodes_list if n.floor == start_floor_sel]
            start_in_node = st.selectbox("Start Room / Facility", [n.name for n in start_floor_nodes], key="in_start_node")
            start_in_id = next(n.id for n in start_floor_nodes if n.name == start_in_node)

        with in_r2:
            dest_floor_sel = st.selectbox("Destination Floor", [0, 1, 2, 3], index=1, format_func=lambda x: floor_names_map[x], key="in_dest_floor")
            dest_floor_nodes = [n for n in indoor_nodes_list if n.floor == dest_floor_sel]
            dest_in_node = st.selectbox("Destination Room / Facility", [n.name for n in dest_floor_nodes], key="in_dest_node")
            dest_in_id = next(n.id for n in dest_floor_nodes if n.name == dest_in_node)

        with in_r3:
            in_prof_name = st.selectbox("Mobility Profile", ["Wheelchair User", "Avoid Stairs", "General Walking"], key="in_profile_sel")
            if in_prof_name == "Wheelchair User":
                in_prof = AccessibilityProfile.wheelchair_user()
            elif in_prof_name == "Avoid Stairs":
                in_prof = AccessibilityProfile.avoid_stairs()
            else:
                in_prof = AccessibilityProfile.general_walking()

        with in_r4:
            st.write("")
            st.write("")
            calc_in_route = st.button("🧭 Navigate Indoor", type="primary", use_container_width=True)

        if calc_in_route:
            in_route_res = re.find_route(start_in_id, dest_in_id, in_prof)
            st.session_state.in_route_res = in_route_res

        if "in_route_res" in st.session_state:
            in_res: RouteResult = st.session_state.in_route_res
            if not in_res.success:
                st.error(f"❌ {in_res.failure_reason}")
            else:
                st.success(f"✅ Route Found: {in_res.total_distance_m}m | Elevators: {in_res.elevators_used_count} | Stairs: {in_res.stairs_count}")

    # Schematic 2D Visualizer
    f_col1, f_col2 = st.columns([1, 4])
    with f_col1:
        st.markdown("### Floor Selector")
        floor_level = st.radio(
            "Select Floor Level:",
            [0, 1, 2, 3],
            format_func=lambda x: floor_names_map[x],
            key="indoor_main_floor_radio"
        )

        st.markdown("---")
        st.markdown("### Floor Legend")
        st.markdown("""
        - 🟢 **Green:** Step-Free Entrance / Ramp
        - 🔵 **Blue:** Classroom / Seminar Hall
        - 🟣 **Purple:** Computing & AI Labs
        - 🟡 **Amber:** Elevator Bank
        - 🔴 **Red:** Staircase (Stairs)
        - 🌐 **Cyan:** Accessible Restroom
        - ⚠️ **Red Marker:** Reported Obstacle
        """)

        st.markdown("---")
        st.markdown("### Focus on Room")
        floor_nodes = [n for n in cg.nodes.values() if n.floor == floor_level]
        selected_room_focus = st.selectbox("Select Destination", ["None"] + [fn.name for fn in floor_nodes])
        focus_room_id = next((fn.id for fn in floor_nodes if fn.name == selected_room_focus), None) if selected_room_focus != "None" else None

    with f_col2:
        viz = FloorPlanVisualizer()
        current_active_route = st.session_state.get("in_route_res") if in_nav_mode == "Indoor Point-to-Point Route" else None
        fig = viz.render_floor(
            floor_level=floor_level,
            nodes=cg.nodes,
            edges=cg.edges,
            active_route=current_active_route,
            obstacles=db.get_all_reports(),
            highlight_node_id=focus_room_id
        )
        st.plotly_chart(fig, use_container_width=True)

        if current_active_route and current_active_route.success:
            st.markdown("#### 🚶 Step-by-Step Directions for Current Floor:")
            steps_on_floor = [s for s in current_active_route.steps if s.floor == floor_level]
            if steps_on_floor:
                for step in steps_on_floor:
                    st.markdown(f"• **{step.node_name}**: {step.transition_instruction}")
            else:
                st.info("The selected route passes through other floors; no transit steps on this level.")


# =============================================================
# PAGE 4: FIND A ROUTE
# =============================================================
elif selected_page == "🧭 Find Accessible Route":
    st.markdown("## 🧭 Find Accessible Route")
    st.caption("Accessibility-aware multi-modal pathfinding across outdoor campus grounds and indoor building floors.")

    all_nodes_sorted = sorted(cg.nodes.values(), key=lambda n: n.name)
    node_options = {f"{n.name} ({'Floor ' + str(n.floor) if n.is_indoor() else 'Outdoor'})": n.id for n in all_nodes_sorted}

    # Support prefilled endpoints from Quick Route
    default_start_idx = 0
    default_dest_idx = min(len(node_options) - 1, 10)

    if "pending_start_id" in st.session_state:
        for idx, (label, nid) in enumerate(node_options.items()):
            if nid == st.session_state.pending_start_id:
                default_start_idx = idx
                break

    if "pending_dest_id" in st.session_state:
        for idx, (label, nid) in enumerate(node_options.items()):
            if nid == st.session_state.pending_dest_id:
                default_dest_idx = idx
                break

    r_col1, r_col2 = st.columns(2)
    with r_col1:
        start_label = st.selectbox("Start Location", list(node_options.keys()), index=default_start_idx)
        start_id = node_options[start_label]

    with r_col2:
        dest_label = st.selectbox("Destination", list(node_options.keys()), index=default_dest_idx)
        dest_id = node_options[dest_label]

    # Additional Preferences
    pref_col1, pref_col2, pref_col3 = st.columns(3)
    with pref_col1:
        route_algo_choice = st.radio(
            "Routing Engine",
            ["Dijkstra (Accessibility-Weighted Optimal)", "BFS (Unweighted Minimum Hops)"],
            horizontal=True
        )
    with pref_col2:
        strict_mode = st.checkbox("Strict Mode (Exclude UNKNOWN/Provisional Paths)", value=False, help="When enabled, requires strict verified step-free certifications on all edges.")
    with pref_col3:
        opt_criterion = st.radio("Optimization Criterion", ["distance", "time"], horizontal=True)

    # Apply preference overrides
    run_profile = AccessibilityProfile(
        name=active_profile.name,
        permit_stairs=active_profile.permit_stairs,
        require_step_free=active_profile.require_step_free,
        prefer_ramps=active_profile.prefer_ramps,
        allow_elevators=active_profile.allow_elevators,
        max_walking_distance_m=active_profile.max_walking_distance_m,
        optimize_for=opt_criterion,
        strict_mode=strict_mode
    )

    if st.button("🚀 Calculate Accessible Route", type="primary", use_container_width=True):
        if start_id == dest_id:
            st.warning("Start and destination are identical. Please choose distinct locations.")
        else:
            with st.spinner("Computing accessibility-constrained path..."):
                if "BFS" in route_algo_choice:
                    route_res = re.find_bfs_route(start_id, dest_id, run_profile)
                else:
                    route_res = re.find_route(start_id, dest_id, run_profile)
                st.session_state.current_route = route_res

    if "current_route" in st.session_state:
        route_res: RouteResult = st.session_state.current_route

        if not route_res.success:
            st.error(f"❌ **Route Cannot Be Formed:** {route_res.failure_reason}")
            if route_res.rejection_explanations:
                with st.expander("🔍 View Accessibility Constraint Rejections"):
                    for rj in route_res.rejection_explanations[:10]:
                        st.write(f"• {rj}")
        else:
            st.success(f"✅ Route Found via **{route_res.algorithm}**!")

            # Metric Summary Cards
            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Total Distance", f"{route_res.total_distance_m} m")
            m2.metric("Est. Travel Time", f"{int(route_res.estimated_travel_time_sec // 60)}m {int(route_res.estimated_travel_time_sec % 60)}s")
            m3.metric("Stairs Count", route_res.stairs_count, delta="0 required" if route_res.stairs_count == 0 else "Contains stairs", delta_color="normal" if route_res.stairs_count == 0 else "inverse")
            m4.metric("Elevators Used", route_res.elevators_used_count)
            m5.metric("Floors Traversed", route_res.floor_transitions_count)

            # Step-by-Step Directions
            st.markdown("### 🚶 Step-by-Step Navigation Instructions")
            for idx, step in enumerate(route_res.steps):
                step_class = "route-step-card"
                icon = "📍"
                if step.edge_taken:
                    if step.edge_taken.is_elevator:
                        step_class += " elevator"
                        icon = "🛗"
                    elif step.edge_taken.has_ramp:
                        step_class += " ramp"
                        icon = "♿"
                    elif step.edge_taken.has_stairs:
                        step_class += " stairs"
                        icon = "🪜"

                floor_tag = f"[Floor {step.floor}]" if step.is_indoor else "[Outdoor]"
                st.markdown(
                    f"<div class='{step_class}'>"
                    f"<b>Step {idx + 1}: {icon} {step.node_name}</b> <span style='color: #64748b;'>{floor_tag}</span><br>"
                    f"<span style='font-size: 14px; color: #1e293b;'>{step.transition_instruction}</span>"
                    f"</div>",
                    unsafe_allow_html=True
                )

            # Explainability & Audit Trail
            explanation = re.explain_route(route_res, run_profile)
            with st.expander("💡 Why was this route recommended? (Explainability & Audit)"):
                st.markdown(f"**Profile:** {explanation['accessibility_profile']}")
                st.markdown("**Accessibility Justifications:**")
                for just in explanation["justifications"]:
                    st.markdown(f"- ✅ {just}")
                if explanation["transparency_notices"]:
                    st.markdown("**Data Integrity Disclosures:**")
                    for notice in explanation["transparency_notices"]:
                        st.markdown(f"- ℹ️ {notice}")

            # Map Renderers
            tab_outdoor, tab_indoor = st.tabs(["🗺️ Outdoor Route Map", "🏢 Indoor Route Visualizer"])
            with tab_outdoor:
                try:
                    mb = OutdoorMapBuilder()
                    folium_route_map = mb.create_campus_map(
                        nodes=cg.nodes,
                        edges=cg.edges,
                        active_route=route_res,
                        obstacles=db.get_all_reports()
                    )
                    st_folium(folium_route_map, width="100%", height=500, key="route_outdoor_map")
                except Exception:
                    st.warning("Outdoor map tiles temporarily offline. Step-by-step directions remain available above.")

            with tab_indoor:
                fv = FloorPlanVisualizer()
                route_floors = {step.floor for step in route_res.steps if step.floor is not None}
                if route_floors:
                    display_floor = st.selectbox("Inspect Floor Level on Route:", sorted(list(route_floors)))
                    fig_route = fv.render_floor(
                        floor_level=display_floor,
                        nodes=cg.nodes,
                        edges=cg.edges,
                        active_route=route_res
                    )
                    st.plotly_chart(fig_route, use_container_width=True)
                else:
                    st.info("This route is entirely outdoor. No indoor floor traversal needed.")

            # Alternative Routes
            with st.expander("🔄 View Alternative Routes"):
                alts = re.find_alternative_routes(start_id, dest_id, run_profile, max_alternatives=3)
                if len(alts) <= 1:
                    st.info("No additional alternative paths meet the current accessibility criteria.")
                else:
                    for i, alt in enumerate(alts[1:], 2):
                        st.markdown(f"**Alternative Option #{i}:** Distance: {alt.total_distance_m}m | Elevators: {alt.elevators_used_count} | Stairs: {alt.stairs_count}")
                        st.caption(" → ".join([cg.nodes[n].name for n in alt.path_nodes]))


# =============================================================
# PAGE 5: REPORT AN OBSTACLE
# =============================================================
elif selected_page == "⚠️ Report an Obstacle":
    st.markdown("## ⚠️ Report a Physical or Operational Obstacle")
    st.caption("Help maintain real-time barrier-free navigation for students and wheelchair users.")

    st.markdown("""
    <div class="integrity-notice">
        <b>PERSISTENCE & VERIFICATION NOTICE:</b><br>
        Reports are saved persistently to SQLite. Severe reports (Critical/High) immediately update the active routing graph to protect mobility-impaired users, while retaining distinct status flags (<code>SUBMITTED</code>, <code>UNDER_REVIEW</code>, <code>VERIFIED</code>, <code>RESOLVED</code>). User submissions are <b>NOT automatically verified</b> until reviewed by authorized campus administration.
    </div>
    """, unsafe_allow_html=True)

    rep_col1, rep_col2 = st.columns([1, 1])

    with rep_col1:
        st.markdown("### Submit New Report")
        with st.form("obstacle_form"):
            target_scope = st.radio("Target Type", ["Pathway (Corridor, Ramp, Walkway)", "Specific Room / Location"], horizontal=True)
            if "Pathway" in target_scope:
                pathway_options = {f"{e.id} ({cg.nodes[e.source].name} ↔ {cg.nodes[e.target].name})": e.id for e in cg.edges.values()}
                selected_edge_label = st.selectbox("Select Pathway", list(pathway_options.keys()))
                target_id = pathway_options[selected_edge_label]
                pathway_id = target_id
                location_id = None
            else:
                node_options = {f"{n.name} ({n.id})": n.id for n in cg.nodes.values()}
                selected_node_label = st.selectbox("Select Location", list(node_options.keys()))
                target_id = node_options[selected_node_label]
                location_id = target_id
                pathway_id = None

            b_col1, b_col2 = st.columns(2)
            with b_col1:
                bldg_val = st.selectbox("Building (if applicable)", ["None (Outdoor Campus)", "FET_MAIN (FET Complex)"])
                building_id = None if "None" in bldg_val else "FET_MAIN"
            with b_col2:
                floor_val = st.selectbox("Floor (if applicable)", ["None (Outdoor)", "Ground Floor (0)", "1st Floor (1)", "2nd Floor (2)", "3rd Floor (3)"])
                floor_id = None if "None" in floor_val else int(floor_val.split("(")[1].replace(")", ""))

            obs_type = st.selectbox("Obstacle Category", [t.value for t in ObstacleType])
            severity = st.selectbox("Severity Level", [s.value for s in ObstacleSeverity], index=2)
            reporter_role = st.selectbox("Reporter Role", ["Student", "Faculty Member", "Wheelchair User", "Campus Visitor", "Facilities Staff"])
            exp_choice = st.selectbox("Optional Temporary Expiration", ["No Expiration (Persistent until manual resolution)", "4 Hours (Temporary Work)", "24 Hours (Daily Maintenance)", "48 Hours"])
            description = st.text_area("Detailed Description", placeholder="E.g., Ramp is blocked by construction scaffolding.")

            submitted = st.form_submit_button("Submit Obstacle Report", type="primary")

            if submitted:
                if not description.strip():
                    st.error("Validation Error: Please provide a description of the obstacle.")
                else:
                    exp_time = None
                    if "4 Hours" in exp_choice:
                        exp_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=4)).isoformat()
                    elif "24 Hours" in exp_choice:
                        exp_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=24)).isoformat()
                    elif "48 Hours" in exp_choice:
                        exp_time = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=48)).isoformat()

                    report_id = f"OBS-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    new_report = ObstacleReport(
                        id=report_id,
                        location_or_edge_id=target_id,
                        obstacle_type=ObstacleType(obs_type),
                        description=description.strip(),
                        severity=ObstacleSeverity(severity),
                        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        status=ObstacleStatus.SUBMITTED,
                        reported_by_role=reporter_role,
                        expiration_time=exp_time,
                        location_id=location_id,
                        pathway_id=pathway_id,
                        building_id=building_id,
                        floor_id=floor_id,
                        verification_status=VerificationStatus.PROVISIONAL
                    )
                    db.add_report(new_report)
                    st.success(f"Report `{report_id}` successfully submitted! Status: **SUBMITTED** (Pending administrator review).")

    with rep_col2:
        st.markdown("### Recorded Obstacles")
        all_reports = db.get_all_reports()
        if not all_reports:
            st.info("No obstacles currently recorded.")
        else:
            for rep in all_reports:
                st_color = {
                    ObstacleStatus.SUBMITTED: "#d97706",
                    ObstacleStatus.UNDER_REVIEW: "#2563eb",
                    ObstacleStatus.VERIFIED: "#dc2626",
                    ObstacleStatus.RESOLVED: "#16a34a",
                    ObstacleStatus.REJECTED: "#6b7280"
                }.get(rep.status, "#6b7280")

                st.markdown(
                    f"<div class='nav-card' style='border-left: 5px solid {st_color};'>"
                    f"<b>{rep.id}</b> — <span style='color: {st_color}; font-weight: bold;'>[{rep.status.value}]</span> "
                    f"<span class='badge-{rep.verification_status.value.lower()}'>{rep.verification_status.value}</span><br>"
                    f"<b>Type:</b> {rep.obstacle_type.value} | <b>Severity:</b> {rep.severity.value}<br>"
                    f"<b>Target:</b> <code>{rep.location_or_edge_id}</code><br>"
                    f"<p style='margin: 4px 0; font-size: 14px;'>{rep.description}</p>"
                    f"<small style='color: #64748b;'>Reported by: {rep.reported_by_role} on {rep.timestamp[:19]}</small>"
                    f"</div>",
                    unsafe_allow_html=True
                )


# =============================================================
# PAGE 6: CAMPUS DIRECTORY
# =============================================================
elif selected_page == "📖 Campus Directory":
    st.markdown("## 📖 Campus Directory & Facility Search")
    st.caption("Search, filter, and inspect verified vs provisional locations at JAIN Global Campus.")

    search_query = st.text_input("🔍 Search by building, room, lab name, or keyword", "")
    
    # Categorical filters aligned with Phase 6 requirements
    cat_col1, cat_col2 = st.columns(2)
    with cat_col1:
        cat_choices = [
            "Academic (Classrooms & Lecture Halls)",
            "Laboratory (Computing & Research Labs)",
            "Administration (Offices & Admissions)",
            "Accessibility Facilities (Ramps, Elevators, Restrooms)",
            "Entrances & Exits",
            "Parking & Transport",
            "Other Campus Services"
        ]
        selected_cats = st.multiselect("Filter by Functional Category", cat_choices, default=[])

    with cat_col2:
        verif_filter = st.multiselect("Filter by Verification Status", [v.value for v in VerificationStatus], default=[])

    def matches_category(n, filters):
        if not filters:
            return True
        for f in filters:
            if "Academic" in f and n.node_type in (LocationType.CLASSROOM,):
                return True
            if "Laboratory" in f and n.node_type in (LocationType.LABORATORY,):
                return True
            if "Administration" in f and n.node_type in (LocationType.OFFICE,):
                return True
            if "Accessibility" in f and n.node_type in (LocationType.ELEVATOR, LocationType.RAMP, LocationType.RESTROOM):
                return True
            if "Entrances" in f and n.node_type in (LocationType.OUTDOOR_ENTRANCE, LocationType.BUILDING_ENTRANCE, LocationType.EMERGENCY_EXIT):
                return True
            if "Parking" in f and n.node_type in (LocationType.PARKING,):
                return True
            if "Other" in f and n.node_type in (LocationType.FACILITY, LocationType.CORRIDOR, LocationType.BUILDING, LocationType.FLOOR_JUNCTION):
                return True
        return False

    records = []
    for node in cg.nodes.values():
        match_query = (
            not search_query or
            search_query.lower() in node.name.lower() or
            search_query.lower() in node.description.lower() or
            search_query.lower() in node.id.lower()
        )
        match_cat = matches_category(node, selected_cats)
        match_verif = not verif_filter or node.verification.value in verif_filter

        if match_query and match_cat and match_verif:
            records.append({
                "ID": node.id,
                "Name": node.name,
                "Category": node.node_type.value,
                "Floor": f"Floor {node.floor}" if node.floor is not None else "Outdoor",
                "Coordinates": f"{node.latitude:.4f}, {node.longitude:.4f}" if node.is_geolocated() else "Unlocated (No GPS)",
                "Verification": node.verification.value,
                "Step-Free Access": "Yes" if node.is_step_free_accessible else "No",
                "Tactile Guidance": "Yes" if node.has_tactile_paving else ("No" if node.has_tactile_paving is False else "Unknown"),
                "Data Source": node.data_source,
                "Description": node.description
            })

    st.markdown(f"**Showing {len(records)} matching destinations:**")
    df = pd.DataFrame(records)
    st.dataframe(df, use_container_width=True, hide_index=True)


# =============================================================
# PAGE 7: CAMPUS ACCESSIBILITY ANALYTICS
# =============================================================
elif selected_page == "📊 Accessibility Analytics":
    st.markdown("## 📊 Campus Accessibility Analytics & Inspection Dashboard")
    st.caption("Live statistical analysis using Pandas & Plotly calculated from actual obstacle reports and verified graph records.")

    analytics_engine = CampusAnalyticsEngine(
        nodes=cg.nodes,
        edges=cg.edges,
        reports=db.get_all_reports()
    )

    # Transparency Notice on Analytics Integrity
    st.markdown("""
    <div class="integrity-notice">
        <b>ANALYTICS & INSPECTION INTEGRITY DISCLOSURE:</b><br>
        • <b>Report Volume vs. Verified Defects:</b> A high count of reports signals high user traffic or community concern, not necessarily verified physical non-compliance until verified by administration.<br>
        • <b>Zero-Report Locations:</b> A location with zero reports is <b>NEVER automatically considered accessible</b>—it may merely be uninspected or rarely visited.<br>
        • <b>Real Records Only:</b> Statistics are computed strictly from stored records in SQLite and verified campus JSON datasets; simulated records and invented historical statistics are excluded.
    </div>
    """, unsafe_allow_html=True)

    # 1. High-level Summary Metrics Scorecard
    scorecard = analytics_engine.get_data_completeness_scorecard()
    m_col1, m_col2, m_col3, m_col4 = st.columns(4)
    with m_col1:
        st.metric(
            "Node Verification Rate",
            f"{scorecard['node_verification_pct']}%",
            help="Percentage of nodes with certified VERIFIED status."
        )
    with m_col2:
        st.metric(
            "Outdoor GPS Coverage",
            f"{scorecard['outdoor_gps_coverage_pct']}%",
            help="Percentage of outdoor facilities with surveyed GPS coordinates."
        )
    with m_col3:
        st.metric(
            "Pathway Verification Rate",
            f"{scorecard['pathway_verification_pct']}%",
            help="Percentage of pathways with verified step-free/stair attribution."
        )
    with m_col4:
        st.metric(
            "Corridor Width Measured",
            f"{scorecard['corridor_width_measured_pct']}%",
            help="Percentage of pathways with physical measured width (cm)."
        )

    st.markdown("---")

    # 2. Charts Row: Obstacle by Category & Active vs. Resolved
    c_row1, c_row2 = st.columns(2)
    with c_row1:
        st.markdown("### 1. Obstacle Reports by Category")
        fig_cat = analytics_engine.plot_reports_by_category()
        st.plotly_chart(fig_cat, use_container_width=True)

    with c_row2:
        st.markdown("### 2. Active vs. Resolved Reports")
        fig_status = analytics_engine.plot_active_vs_resolved()
        st.plotly_chart(fig_status, use_container_width=True)

    st.markdown("---")

    # 3. Repeat Reports & Resolution Metrics
    r_col1, r_col2 = st.columns(2)
    with r_col1:
        st.markdown("### 3. Locations with Repeated Reports")
        st.caption("Highlights facilities requiring on-site physical remediation:")
        rep_locs_df = analytics_engine.get_locations_with_repeated_reports()
        if rep_locs_df.empty:
            st.info("No repeated reports on file.")
        else:
            st.dataframe(rep_locs_df, use_container_width=True, hide_index=True)

    with r_col2:
        st.markdown("### 4. Resolution Response Time Metrics")
        st.caption("Time elapsed between obstacle submission and administrative resolution:")
        res_metrics = analytics_engine.get_resolution_time_metrics()
        if not res_metrics["has_data"]:
            st.info("ℹ️ No resolved obstacle records with complete lifecycle timestamps are available yet.")
        else:
            rc1, rc2 = st.columns(2)
            rc1.metric("Average Resolution Time", f"{res_metrics['mean_hours']} hrs")
            rc2.metric("Median Resolution Time", f"{res_metrics['median_hours']} hrs")
            st.write(f"• **Fastest Resolution:** {res_metrics['min_hours']} hrs")
            st.write(f"• **Longest Resolution:** {res_metrics['max_hours']} hrs")
            st.write(f"• **Resolved Sample Size:** {res_metrics['resolved_count_with_timestamps']} reports")

    st.markdown("---")

    # 4. Historical Trends Timeline
    st.markdown("### 5. Historical Report Ingestion Trends")
    st.caption("Timeline of actual recorded obstacle reports by calendar date:")
    fig_hist = analytics_engine.plot_historical_trends()
    st.plotly_chart(fig_hist, use_container_width=True)

    st.markdown("---")

    # 5. Inspection Priority: Pathways and Buildings Requiring Audit
    p_tab1, p_tab2 = st.tabs([
        "🔍 Pathways Requiring Accessibility Verification",
        "🏢 Building Data Completeness & Inspection Priorities"
    ])

    with p_tab1:
        st.markdown("#### Pathways Requiring Institutional Audit")
        st.caption("Pathways marked PROVISIONAL/DEMONSTRATION, having unmeasured widths, or unknown surface materials:")
        pathways_audit_df = analytics_engine.get_pathways_requiring_verification()
        if pathways_audit_df.empty:
            st.success("All campus pathways have verified accessibility attributes.")
        else:
            st.dataframe(pathways_audit_df, use_container_width=True, hide_index=True)

    with p_tab2:
        st.markdown("#### Building & Zone Inspection Priority Scorecard")
        st.caption("Identifies campus structures with missing accessibility data:")
        bldg_comp_df = analytics_engine.get_buildings_data_completeness()
        st.dataframe(bldg_comp_df, use_container_width=True, hide_index=True)


# =============================================================
# PAGE 8: ADMINISTRATION & DATA EDITOR
# =============================================================
elif selected_page == "⚙️ Administration":
    st.markdown("## ⚙️ Administration & Campus Data Editor")
    st.caption("Maintain verified geographic coordinates, pathways, indoor floor plans, and obstacle lifecycles without editing Python code.")

    # Honest development access control notice
    st.markdown("""
    <div class="integrity-notice" style="border-left-color: #3b82f6; background-color: #eff6ff; color: #1e40af;">
        <b>LOCAL ACADEMIC PROTOTYPE ACCESS CONTROL:</b><br>
        Administrative actions and dataset mutations are protected by an administrator passcode (Default: <code>jain_admin_2026</code> or <code>admin123</code>). Simulated mock logins are intentionally omitted for transparent security.
    </div>
    """, unsafe_allow_html=True)

    admin_pass = st.text_input("Enter Administrator Passcode", type="password", key="admin_passcode")
    valid_keys = {os.environ.get("CAMPUS_ADMIN_KEY", "admin123"), "admin123", "jain_admin_2026"}
    is_authorized = (admin_pass in valid_keys)

    if not is_authorized:
        st.info("🔒 Enter the administrative passcode above to unlock data-management and moderation tools.")
    else:
        st.success("🔓 Administrative Access Granted.")

        adm_tab1, adm_tab2, adm_tab3, adm_tab4, adm_tab5 = st.tabs([
            "1. Location Management",
            "2. Pathway Management",
            "3. Indoor Map Management",
            "4. Import / Export & Backup",
            "5. Obstacle Moderation"
        ])

        # ---------------------------------------------------------
        # TAB 1: LOCATION MANAGEMENT
        # ---------------------------------------------------------
        with adm_tab1:
            st.markdown("### 📍 Location Management")
            st.caption("Add or edit outdoor campus landmarks and entrances. Valid coordinates required for map placement.")

            loc_mode = st.radio("Action", ["Edit Existing Location", "Add New Location"], horizontal=True, key="loc_admin_mode")

            if loc_mode == "Edit Existing Location":
                all_loc_options = {f"{n.name} [{n.id}]": n.id for n in sorted(cg.nodes.values(), key=lambda x: x.name) if not n.is_indoor()}
                sel_loc_label = st.selectbox("Select Outdoor Location to Edit", list(all_loc_options.keys()), key="edit_loc_sel")
                sel_loc_id = all_loc_options[sel_loc_label]
                cur_node = cg.nodes[sel_loc_id]

                with st.form("edit_location_form"):
                    el_c1, el_c2 = st.columns(2)
                    with el_c1:
                        el_name = st.text_input("Location Name", value=cur_node.name)
                        el_type = st.selectbox(
                            "Category / Location Type",
                            [t.value for t in LocationType],
                            index=[t.value for t in LocationType].index(cur_node.node_type.value) if cur_node.node_type.value in [t.value for t in LocationType] else 0
                        )
                        el_verif = st.selectbox(
                            "Verification Status",
                            [v.value for v in VerificationStatus],
                            index=[v.value for v in VerificationStatus].index(cur_node.verification.value)
                        )
                        el_bldg = st.text_input("Indoor Building ID (if applicable)", value=cur_node.indoor_building_id or "")

                    with el_c2:
                        el_lat = st.number_input("Latitude (leave 0.0 if unlocated)", value=cur_node.latitude or 0.0, format="%.6f")
                        el_lon = st.number_input("Longitude (leave 0.0 if unlocated)", value=cur_node.longitude or 0.0, format="%.6f")
                        el_step_free = st.checkbox("Step-Free Accessible", value=cur_node.is_step_free_accessible)
                        el_tactile = st.checkbox("Tactile Paving Present", value=cur_node.has_tactile_paving or False)
                        el_source = st.text_input("Data Source / Survey Reference", value=cur_node.data_source)

                    el_desc = st.text_area("Description & Access Notes", value=cur_node.description)

                    if st.form_submit_button("Save Location Changes", type="primary"):
                        lat_val = el_lat if el_lat != 0.0 else None
                        lon_val = el_lon if el_lon != 0.0 else None
                        success, msg = editor.save_location(
                            node_id=cur_node.id,
                            name=el_name,
                            node_type=el_type,
                            verification=el_verif,
                            is_indoor=False,
                            latitude=lat_val,
                            longitude=lon_val,
                            building_id=el_bldg if el_bldg.strip() else None,
                            is_step_free=el_step_free,
                            has_tactile_paving=el_tactile,
                            description=el_desc,
                            data_source=el_source
                        )
                        if success:
                            st.success(f"✅ {msg}")
                            # Refresh application graph
                            st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                            st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            else:
                with st.form("add_location_form"):
                    nl_c1, nl_c2 = st.columns(2)
                    with nl_c1:
                        nl_id = st.text_input("Unique Node ID (e.g., OUT_NEW_GATE)", placeholder="OUT_LOC_...")
                        nl_name = st.text_input("Location Name", placeholder="E.g., North Pedestrian Gate")
                        nl_type = st.selectbox("Category", [t.value for t in LocationType])
                        nl_verif = st.selectbox("Verification Status", [v.value for v in VerificationStatus], index=1)  # Default PROVISIONAL
                        nl_bldg = st.text_input("Indoor Building ID (optional)", placeholder="FET_MAIN")

                    with nl_c2:
                        nl_lat = st.number_input("Latitude (0.0 if unlocated)", value=0.0, format="%.6f")
                        nl_lon = st.number_input("Longitude (0.0 if unlocated)", value=0.0, format="%.6f")
                        nl_step_free = st.checkbox("Step-Free Accessible", value=True)
                        nl_tactile = st.checkbox("Tactile Paving Present", value=False)
                        nl_source = st.text_input("Data Source", value="Field Survey / OpenStreetMap")

                    nl_desc = st.text_area("Description", placeholder="Access notes, surface details, nearby landmarks...")

                    if st.form_submit_button("Create Location", type="primary"):
                        lat_val = nl_lat if nl_lat != 0.0 else None
                        lon_val = nl_lon if nl_lon != 0.0 else None
                        success, msg = editor.save_location(
                            node_id=nl_id,
                            name=nl_name,
                            node_type=nl_type,
                            verification=nl_verif,
                            is_indoor=False,
                            latitude=lat_val,
                            longitude=lon_val,
                            building_id=nl_bldg if nl_bldg.strip() else None,
                            is_step_free=nl_step_free,
                            has_tactile_paving=nl_tactile,
                            description=nl_desc,
                            data_source=nl_source
                        )
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                            st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

        # ---------------------------------------------------------
        # TAB 2: PATHWAY MANAGEMENT
        # ---------------------------------------------------------
        with adm_tab2:
            st.markdown("### 🛣️ Pathway Management")
            st.caption("Manage navigable connections, step-free flags, stairs, ramps, and distances.")

            pw_mode = st.radio("Action", ["Edit Existing Pathway", "Add New Pathway"], horizontal=True, key="pw_admin_mode")

            if pw_mode == "Edit Existing Pathway":
                all_edge_options = {f"{e.id} ({cg.nodes[e.source].name} ↔ {cg.nodes[e.target].name})": e.id for e in cg.edges.values() if not e.is_indoor}
                sel_pw_label = st.selectbox("Select Outdoor Pathway", list(all_edge_options.keys()), key="edit_pw_sel")
                sel_pw_id = all_edge_options[sel_pw_label]
                cur_edge = cg.edges[sel_pw_id]

                with st.form("edit_pathway_form"):
                    ep_c1, ep_c2 = st.columns(2)
                    with ep_c1:
                        st.write(f"**Endpoints:** `{cur_edge.source}` ↔ `{cur_edge.target}`")
                        ep_dist = st.number_input("Distance (meters)", value=float(cur_edge.distance_m), min_value=0.1, step=1.0)
                        ep_time = st.number_input("Estimated Time (seconds)", value=float(cur_edge.estimated_time_sec), min_value=1.0, step=5.0)
                        ep_verif = st.selectbox(
                            "Verification Status",
                            [v.value for v in VerificationStatus],
                            index=[v.value for v in VerificationStatus].index(cur_edge.verification.value)
                        )
                        ep_surf = st.selectbox(
                            "Surface Material",
                            [s.value for s in SurfaceType],
                            index=[s.value for s in SurfaceType].index(cur_edge.surface.value) if cur_edge.surface.value in [s.value for s in SurfaceType] else 0
                        )

                    with ep_c2:
                        ep_step_free = st.checkbox("Step-Free Access", value=cur_edge.is_step_free)
                        ep_stairs = st.checkbox("Has Stairs", value=cur_edge.has_stairs)
                        ep_ramp = st.checkbox("Has Ramp", value=cur_edge.has_ramp)
                        ep_width = st.number_input("Clear Width (cm)", value=float(cur_edge.width_cm or 180.0), min_value=50.0)
                        ep_notes = st.text_input("Survey Notes", value=cur_edge.notes)

                    if st.form_submit_button("Update Pathway", type="primary"):
                        success, msg = editor.save_pathway(
                            edge_id=cur_edge.id,
                            source=cur_edge.source,
                            target=cur_edge.target,
                            distance_m=ep_dist,
                            estimated_time_sec=ep_time,
                            verification=ep_verif,
                            is_step_free=ep_step_free,
                            has_stairs=ep_stairs,
                            has_ramp=ep_ramp,
                            surface=ep_surf,
                            width_cm=ep_width,
                            is_indoor=False,
                            notes=ep_notes
                        )
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                            st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            else:
                outdoor_node_ids = sorted([n.id for n in cg.nodes.values() if not n.is_indoor()])
                with st.form("add_pathway_form"):
                    np_c1, np_c2 = st.columns(2)
                    with np_c1:
                        np_id = st.text_input("Unique Edge ID", placeholder="E_GATE_TO_NEW...")
                        np_src = st.selectbox("Source Node", outdoor_node_ids, key="np_src_sel")
                        np_tgt = st.selectbox("Target Node", outdoor_node_ids, index=min(1, len(outdoor_node_ids)-1), key="np_tgt_sel")
                        np_dist = st.number_input("Distance (meters)", value=25.0, min_value=0.5)
                        np_time = st.number_input("Estimated Time (seconds)", value=20.0, min_value=1.0)

                    with np_c2:
                        np_verif = st.selectbox("Verification", [v.value for v in VerificationStatus], index=1)
                        np_step_free = st.checkbox("Step-Free Access", value=True)
                        np_stairs = st.checkbox("Has Stairs", value=False)
                        np_ramp = st.checkbox("Has Ramp", value=False)
                        np_surf = st.selectbox("Surface Material", [s.value for s in SurfaceType], index=0)
                        np_notes = st.text_input("Notes", placeholder="Paved pathway with handrail")

                    if st.form_submit_button("Create Pathway", type="primary"):
                        success, msg = editor.save_pathway(
                            edge_id=np_id,
                            source=np_src,
                            target=np_tgt,
                            distance_m=np_dist,
                            estimated_time_sec=np_time,
                            verification=np_verif,
                            is_step_free=np_step_free,
                            has_stairs=np_stairs,
                            has_ramp=np_ramp,
                            surface=np_surf,
                            is_indoor=False,
                            notes=np_notes
                        )
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                            st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

        # ---------------------------------------------------------
        # TAB 3: INDOOR MAP MANAGEMENT
        # ---------------------------------------------------------
        with adm_tab3:
            st.markdown("### 🏢 Indoor Map & Demonstration Floor Plan Editor")
            st.caption("Edit rooms, adjust corridor coordinates, link floor transitions, and replace demonstration models with verified architectural data.")

            in_nodes = [n for n in cg.nodes.values() if n.is_indoor()]
            floor_opts = [0, 1, 2, 3]
            sel_in_floor = st.selectbox("Select Floor Level to Manage", floor_opts, format_func=lambda x: f"Floor {x}", key="admin_in_floor")

            floor_nodes = [n for n in in_nodes if n.floor == sel_in_floor]
            st.write(f"**Current Rooms/Nodes on Floor {sel_in_floor}:** {len(floor_nodes)}")

            in_action = st.radio("Indoor Action", ["Edit Room Coordinates & Attributes", "Add Room / Node", "Mark Demonstration Layout as Verified"], horizontal=True)

            if in_action == "Edit Room Coordinates & Attributes":
                r_names = {f"{n.name} [{n.id}]": n.id for n in floor_nodes}
                sel_r_label = st.selectbox("Select Room to Edit", list(r_names.keys()), key="adm_r_sel")
                sel_r_id = r_names[sel_r_label]
                r_node = cg.nodes[sel_r_id]

                with st.form("edit_indoor_room_form"):
                    ir_c1, ir_c2 = st.columns(2)
                    with ir_c1:
                        ir_name = st.text_input("Room Name", value=r_node.name)
                        ir_type = st.selectbox("Type", [t.value for t in LocationType], index=[t.value for t in LocationType].index(r_node.node_type.value) if r_node.node_type.value in [t.value for t in LocationType] else 0)
                        ir_verif = st.selectbox("Verification", [v.value for v in VerificationStatus], index=[v.value for v in VerificationStatus].index(r_node.verification.value))
                    with ir_c2:
                        ir_x = st.number_input("Floor Coordinate X (0 - 100)", value=float(r_node.x or 50.0), min_value=0.0, max_value=100.0)
                        ir_y = st.number_input("Floor Coordinate Y (0 - 100)", value=float(r_node.y or 50.0), min_value=0.0, max_value=100.0)
                        ir_step_free = st.checkbox("Step-Free Accessible", value=r_node.is_step_free_accessible)
                        ir_width = st.number_input("Door Width (cm)", value=float(r_node.door_width_cm or 90.0))

                    ir_desc = st.text_area("Description", value=r_node.description)

                    if st.form_submit_button("Update Indoor Room", type="primary"):
                        success, msg = editor.save_location(
                            node_id=r_node.id,
                            name=ir_name,
                            node_type=ir_type,
                            verification=ir_verif,
                            is_indoor=True,
                            floor=sel_in_floor,
                            building_id="FET_MAIN",
                            x=ir_x,
                            y=ir_y,
                            is_step_free=ir_step_free,
                            door_width_cm=ir_width,
                            description=ir_desc
                        )
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                            st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            elif in_action == "Add Room / Node":
                with st.form("add_indoor_room_form"):
                    nr_c1, nr_c2 = st.columns(2)
                    with nr_c1:
                        nr_id = st.text_input("Unique ID", placeholder=f"INDOOR_FET_{sel_in_floor}_...")
                        nr_name = st.text_input("Room / Facility Name", placeholder="E.g., Robotics Lab 202")
                        nr_type = st.selectbox("Category", [t.value for t in LocationType], index=1)
                        nr_verif = st.selectbox("Verification", [v.value for v in VerificationStatus], index=2)  # Default DEMONSTRATION
                    with nr_c2:
                        nr_x = st.number_input("X Coordinate (0-100)", value=50.0, min_value=0.0, max_value=100.0)
                        nr_y = st.number_input("Y Coordinate (0-100)", value=50.0, min_value=0.0, max_value=100.0)
                        nr_step_free = st.checkbox("Step-Free Access", value=True)
                        nr_width = st.number_input("Door Width (cm)", value=90.0)

                    nr_desc = st.text_area("Description", placeholder="Lab equipment, emergency exit notes...")

                    if st.form_submit_button("Add Room to Floor", type="primary"):
                        success, msg = editor.save_location(
                            node_id=nr_id,
                            name=nr_name,
                            node_type=nr_type,
                            verification=nr_verif,
                            is_indoor=True,
                            floor=sel_in_floor,
                            building_id="FET_MAIN",
                            x=nr_x,
                            y=nr_y,
                            is_step_free=nr_step_free,
                            door_width_cm=nr_width,
                            description=nr_desc
                        )
                        if success:
                            st.success(f"✅ {msg}")
                            st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                            st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                            st.rerun()
                        else:
                            st.error(f"❌ {msg}")

            else:
                st.markdown("#### Transition Demonstration Floor Plan to Verified Blueprint")
                st.warning(
                    "⚠️ **Institutional Certification Required:**\n"
                    "Marking demonstration data as verified will update the entire indoor building model to `VERIFIED`. "
                    "Do NOT proceed unless certified architectural blueprints and on-site door/elevator measurements have been audited."
                )
                if st.button("Mark All FET Indoor Nodes as VERIFIED", type="primary"):
                    raw_in = editor.get_raw_indoor_data()
                    editor.create_backup("pre_certify_indoor")
                    for n in raw_in.get("nodes", []):
                        n["verification"] = "VERIFIED"
                    for e in raw_in.get("edges", []):
                        e["verification"] = "VERIFIED"
                    raw_in["building_metadata"]["disclaimer"] = "VERIFIED FET BUILDING BLUEPRINT — Officially surveyed and institutionalized."
                    editor.loader.save_indoor_data(raw_in["building_metadata"], raw_in["nodes"], raw_in["edges"])
                    st.success("✅ All indoor FET entities upgraded to VERIFIED status!")
                    st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                    st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                    st.rerun()

        # ---------------------------------------------------------
        # TAB 4: IMPORT / EXPORT & BACKUP
        # ---------------------------------------------------------
        with adm_tab4:
            st.markdown("### 💾 Dataset Import, Export & Backups")
            st.caption("Safely export datasets, create manual backups, and preview/validate bulk JSON imports before committing.")

            bk_c1, bk_c2 = st.columns(2)
            with bk_c1:
                st.markdown("#### 📤 Export Working Datasets")
                out_json = editor.export_dataset_json("outdoor")
                in_json = editor.export_dataset_json("indoor")
                st.download_button(
                    "📥 Download Outdoor Campus Data (JSON)",
                    data=out_json,
                    file_name="campus_data_export.json",
                    mime="application/json",
                    use_container_width=True
                )
                st.download_button(
                    "📥 Download FET Indoor Data (JSON)",
                    data=in_json,
                    file_name="indoor_data_export.json",
                    mime="application/json",
                    use_container_width=True
                )

                st.write("")
                if st.button("🛡️ Create Instant Backup Snapshot", use_container_width=True):
                    b1, b2 = editor.create_backup(tag="manual")
                    st.success(f"Snapshot created successfully:\n• {os.path.basename(b1)}\n• {os.path.basename(b2)}")

            with bk_c2:
                st.markdown("#### 📥 Import Dataset with Preview & Validation")
                target_ds = st.radio("Import Target", ["Outdoor Campus Data", "Indoor Building Data"], horizontal=True)
                is_ind = "Indoor" in target_ds
                uploaded_file = st.file_uploader("Upload JSON File", type=["json"], key="admin_json_uploader")

                if uploaded_file is not None:
                    json_str = uploaded_file.read().decode("utf-8")
                    valid, v_msg, stats = editor.import_dataset(json_str, is_indoor=is_ind)

                    if not valid:
                        st.error(f"❌ {v_msg}")
                    else:
                        st.success("✅ JSON is syntactically valid and passed all graph schema constraints!")
                        st.markdown(
                            f"<div class='nav-card' style='padding: 12px 16px;'>"
                            f"<b>Staged Dataset Preview:</b><br>"
                            f"• Total Nodes: <b>{stats['nodes_count']}</b> (Verified: {stats['verified_nodes']}, Provisional: {stats['provisional_nodes']}, Demo: {stats['demo_nodes']})<br>"
                            f"• Total Pathways: <b>{stats['edges_count']}</b> (Step-Free: {stats['step_free_edges']})<br>"
                            f"</div>",
                            unsafe_allow_html=True
                        )

                        if st.button("⚠️ Confirm and Overwrite Working Dataset", type="primary"):
                            ok, app_msg = editor.apply_imported_dataset(stats["data"], is_indoor=is_ind)
                            if ok:
                                st.success(f"✅ {app_msg}")
                                st.session_state.graph = CampusGraph(obstacle_db=st.session_state.obstacle_db)
                                st.session_state.routing = RoutingEngine(campus_graph=st.session_state.graph)
                                st.rerun()
                            else:
                                st.error(f"❌ {app_msg}")

        # ---------------------------------------------------------
        # TAB 5: OBSTACLE MODERATION
        # ---------------------------------------------------------
        with adm_tab5:
            st.markdown("### ⚠️ Obstacle Moderation Workflow")
            st.caption("Review user-submitted reports and transition lifecycle states (SUBMITTED -> UNDER_REVIEW -> VERIFIED -> RESOLVED).")

            all_reports = db.get_all_reports()
            if not all_reports:
                st.info("No obstacle reports currently on file.")
            else:
                rep_select = st.selectbox(
                    "Select Report to Moderate",
                    [f"{r.id} - {r.obstacle_type.value} [{r.status.value}]" for r in all_reports],
                    key="admin_rep_select_p7"
                )
                selected_rep_id = rep_select.split(" - ")[0]
                cur_rep = db.get_report(selected_rep_id)

                mod_c1, mod_c2 = st.columns(2)
                with mod_c1:
                    st.write(f"**Target ID:** `{cur_rep.location_or_edge_id}`")
                    st.write(f"**Severity:** {cur_rep.severity.value}")
                    st.write(f"**Description:** {cur_rep.description}")
                    st.write(f"**Submitted By:** {cur_rep.reported_by_role} on {cur_rep.timestamp[:19]}")

                    new_status = st.selectbox(
                        "Update Lifecycle Status",
                        [s.value for s in ObstacleStatus],
                        index=[s.value for s in ObstacleStatus].index(cur_rep.status.value),
                        key="admin_mod_status"
                    )
                    new_verif = st.selectbox(
                        "Update Verification Status",
                        [VerificationStatus.PROVISIONAL.value, VerificationStatus.VERIFIED.value],
                        index=0 if cur_rep.verification_status == VerificationStatus.PROVISIONAL else 1,
                        key="admin_mod_verif"
                    )
                    v_notes = st.text_input("Moderator / Action Notes", value=cur_rep.verification_notes, key="admin_mod_notes")

                    if st.button("Save Moderation Decision", type="primary"):
                        db.update_report_status(
                            cur_rep.id,
                            new_status=ObstacleStatus(new_status),
                            verification_notes=v_notes,
                            verification_status=VerificationStatus(new_verif)
                        )
                        st.success(f"Report {cur_rep.id} updated!")
                        st.rerun()

                with mod_c2:
                    st.markdown("#### Delete / Purge Report")
                    st.caption("Remove false submissions permanently from SQLite:")
                    if st.button("🗑️ Delete Report", type="secondary", key="del_rep_btn"):
                        db.delete_report(cur_rep.id)
                        st.warning(f"Report {cur_rep.id} deleted.")
                        st.rerun()

