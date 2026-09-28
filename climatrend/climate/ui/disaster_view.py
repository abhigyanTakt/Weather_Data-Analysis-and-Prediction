"""
Streamlit View Component for Feature 6: Disaster Early-Warning System.
Visualizes multi-hazard events (USGS earthquakes, NASA FIRMS wildfires, flood indicators),
renders an interactive geospatial hazard map with radius rings, displays deduplicated
shared alert logs, and provides a multi-channel subscription manager.
"""

import json
from typing import Any, Dict
import folium
import streamlit as st

from climatrend.climate.alerts.engine import SharedAlertEngine
from climatrend.climate.disasters.service import DisasterService
from climatrend.climate.db.database import get_db
from climatrend.climate.ui.map_helper import get_folium_base_map

try:
    from streamlit_folium import folium_static
except ImportError:
    folium_static = None


def render_disaster_view(
    city_name: str,
    lat: float,
    lon: float,
    translations: Dict[str, Any] = None,
) -> None:
    """Renders the Disaster Early-Warning and Hazard Management interface."""
    t = translations or {}

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; color:#f8fafc;">🚨 Disaster Forecasting & Early-Warning: <b>{city_name}</b></h3>
            <span style="color:#f59e0b; font-size:13px; font-weight:600;">Shared Alert Engine • Multi-Channel Delivery</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    service = DisasterService()
    engine = SharedAlertEngine()

    # Manual Hazard Scan trigger
    col_hdr1, col_hdr2 = st.columns([3, 1])
    with col_hdr1:
        st.write(
            "Continuously monitors USGS seismic networks, NASA FIRMS active fire sensors, and Open-Meteo flood indicators within your region."
        )
    with col_hdr2:
        if st.button("⚡ Run Live Hazard Scan", use_container_width=True):
            with st.spinner("Scanning USGS, NASA FIRMS, and River discharge models..."):
                scan_results = service.scan_location_hazards(
                    lat=lat, lon=lon, location_name=city_name, radius_km=500.0
                )
                if scan_results:
                    st.success(f"Hazard scan completed! Processed {len(scan_results)} event evaluations.")
                else:
                    st.info("Scan completed: No severe hazards detected exceeding alert thresholds.")
            st.rerun()

    # Retrieve live hazards for display
    with st.spinner("Loading regional hazard telemetry..."):
        recent_quakes = service.disaster_client.fetch_recent_earthquakes(
            center_lat=lat, center_lon=lon, max_radius_km=600.0, min_magnitude=3.5
        )
        active_fires = service.disaster_client.fetch_active_wildfires(
            center_lat=lat, center_lon=lon, radius_km=150.0
        )
        flood_data = service.open_meteo.fetch_flood_indicators(lat, lon)
        active_alerts = engine.get_recent_alerts(limit=20)

    # Top KPI Metrics Cards
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    with kpi1:
        q_count = len(recent_quakes)
        q_max_mag = max([q["magnitude"] for q in recent_quakes]) if recent_quakes else 0.0
        q_color = "#ef4444" if q_max_mag >= 5.5 else "#f59e0b" if q_max_mag >= 4.5 else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">EARTHQUAKES (<600km)</div>
                <div class="metric-val" style="color: {q_color};">{q_count} Events</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Max Mag: M{q_max_mag:.1f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi2:
        fire_count = len(active_fires)
        f_color = "#ef4444" if fire_count > 10 else "#f59e0b" if fire_count > 0 else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">WILDFIRE DETECTIONS (<150km)</div>
                <div class="metric-val" style="color: {f_color};">{fire_count} Hotspots</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">NASA FIRMS VIIRS/MODIS</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi3:
        discharges = flood_data.get("daily", {}).get("river_discharge", [10.0])
        curr_q = discharges[0] if discharges else 10.0
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">RIVER DISCHARGE LEVEL</div>
                <div class="metric-val">{curr_q:.1f} m³/s</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Riverine Flood Indicator</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with kpi4:
        active_count = len([a for a in active_alerts if a["status"] in ("active", "escalated")])
        a_color = "#ef4444" if active_count > 0 else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">DISPATCHED ALERTS LOG</div>
                <div class="metric-val" style="color: {a_color};">{active_count} Active</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Shared Engine Log</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Map & Live Hazard Feed
    col_map, col_feed = st.columns([1.3, 1.7])

    with col_map:
        st.markdown("#### 🗺️ Geospatial Hazard Radius Map")
        m = get_folium_base_map(location=[lat, lon], zoom_start=6, dark_mode=True)

        # Monitoring center
        folium.Marker(
            location=[lat, lon],
            popup=f"<b>{city_name}</b> (Monitoring Center)",
            icon=folium.Icon(color="blue", icon="home"),
        ).add_to(m)

        # Proximity buffer rings
        folium.Circle(
            location=[lat, lon],
            radius=100000,  # 100km
            color="#38bdf8",
            weight=1,
            fill=False,
            tooltip="100 km Radius",
        ).add_to(m)
        folium.Circle(
            location=[lat, lon],
            radius=300000,  # 300km
            color="#f59e0b",
            weight=1,
            fill=False,
            tooltip="300 km Radius",
        ).add_to(m)

        # Plot earthquakes
        for q in recent_quakes[:15]:
            q_color = "red" if q["magnitude"] >= 6.0 else "orange" if q["magnitude"] >= 5.0 else "yellow"
            folium.CircleMarker(
                location=[q["latitude"], q["longitude"]],
                radius=max(4, int(q["magnitude"] * 2)),
                color=q_color,
                fill=True,
                fill_color=q_color,
                fill_opacity=0.7,
                popup=f"<b>M{q['magnitude']:.1f} Earthquake</b><br>{q['place']}<br>Depth: {q['depth_km']}km<br>Distance: {q['distance_km']:.0f}km",
            ).add_to(m)

        # Plot active fires
        for f in active_fires[:20]:
            folium.CircleMarker(
                location=[f["latitude"], f["longitude"]],
                radius=5,
                color="#f97316",
                fill=True,
                fill_color="#f97316",
                fill_opacity=0.8,
                popup=f"<b>Active Wildfire</b><br>Dist: {f['distance_km']:.0f}km<br>Date: {f.get('acquisition_date')}",
            ).add_to(m)

        if folium_static:
            folium_static(m, width=460, height=420)
        else:
            st.components.v1.html(m._repr_html_(), height=430)

    with col_feed:
        st.markdown("#### 📡 Recent Seismic & Environmental Events")
        if recent_quakes:
            q_display = [
                {
                    "Magnitude": f"M {q['magnitude']:.1f}",
                    "Location": q["place"],
                    "Distance": f"{q['distance_km']:.0f} km",
                    "Depth": f"{q['depth_km']} km",
                }
                for q in recent_quakes[:8]
            ]
            st.dataframe(q_display, use_container_width=True)
        else:
            st.info("No seismic events detected within 600km in the past 24 hours.")

        st.markdown("#### 📋 Shared Alert Engine Log (Deduplicated)")
        if active_alerts:
            log_display = [
                {
                    "Time": a["detected_at"][:16],
                    "Severity": a["severity"],
                    "Hazard": a["hazard_type"].title(),
                    "Title": a["title"][:45] + "...",
                    "Channels": a["sent_channels"],
                    "Status": a["status"].upper(),
                }
                for a in active_alerts[:6]
            ]
            st.dataframe(log_display, use_container_width=True)
        else:
            st.info("Alert log is empty. Trigger a scan above to evaluate active hazards.")

    # Alert Subscriptions & Multi-Channel Settings
    st.markdown("---")
    with st.expander("🔔 Configure Alert Subscriptions & Delivery Channels"):
        st.markdown("Customize how the **Shared Alert Engine** delivers alerts for this location:")
        sub_c1, sub_c2, sub_c3 = st.columns(3)

        with sub_c1:
            hazards_selected = st.multiselect(
                "Hazard Types to Monitor",
                ["all", "earthquake", "wildfire", "flood", "extreme_heat", "heavy_rain", "drought"],
                default=["all"],
            )
        with sub_c2:
            min_sev = st.selectbox(
                "Minimum Alert Severity",
                ["Advisory", "Watch", "Warning", "Severe"],
                index=1,
            )
        with sub_c3:
            channels = st.multiselect(
                "Delivery Channels",
                ["in_app", "telegram", "email", "ntfy"],
                default=["in_app", "ntfy"],
            )

        dest_col1, dest_col2 = st.columns(2)
        with dest_col1:
            dest_input = st.text_input(
                "Destination (Optional Telegram Chat ID, Email, or ntfy topic)",
                placeholder="e.g. 123456789 or user@example.com",
            )
        with dest_col2:
            st.write("")
            st.write("")
            if st.button("💾 Save Subscription Settings", use_container_width=True):
                with get_db() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        """
                        INSERT INTO alert_subscriptions (
                            user_id, region_id, hazard_types, min_severity, channels, destination
                        ) VALUES (?, (SELECT id FROM regions WHERE name = ? LIMIT 1), ?, ?, ?, ?);
                        """,
                        (
                            "user_default",
                            city_name,
                            json.dumps(hazards_selected),
                            min_sev,
                            json.dumps(channels),
                            dest_input,
                        ),
                    )
                st.success(f"Subscription successfully updated for {city_name}!")
