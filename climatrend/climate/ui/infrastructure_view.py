"""
Streamlit View Component for Feature 5: Climate-Resilient Infrastructure Planning.
Visualizes critical municipal assets on interactive Folium maps with elevation,
flood, heat, and fire exposure overlays.
Renders vulnerability rankings and engineering adaptation roadmaps.
"""

from typing import Any, Dict
import folium
import pandas as pd
import plotly.express as px
import streamlit as st

from climatrend.climate.infrastructure.service import (
    ASSET_CRITICALITY,
    InfrastructureService,
)
from climatrend.climate.ui.map_helper import get_folium_base_map

try:
    from streamlit_folium import folium_static
except ImportError:
    folium_static = None


def render_infrastructure_view(
    city_name: str = "Delhi",
    lat: float = 28.6139,
    lon: float = 77.2090,
    user_id: str = "user_default",
    translations: Dict[str, Any] = None,
) -> None:
    """Renders the Climate-Resilient Infrastructure Planning interface."""
    t = translations or {}

    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; color:#f8fafc;">🏗️ Climate-Resilient Infrastructure Planning</h3>
            <span style="color:#38bdf8; font-size:13px; font-weight:600;">Geospatial Asset Vulnerability • Engineering Adaptation</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    infra_service = InfrastructureService()

    # Ensure baseline assets exist
    infra_service.seed_default_assets_if_empty(user_id=user_id)
    assets = infra_service.get_assets(user_id=user_id)

    # Top summary metrics
    total_assets = len(assets)
    critical_assets = sum(1 for a in assets if a["vulnerability_score"] >= 50.0)
    avg_vuln = round(sum(a["vulnerability_score"] for a in assets) / total_assets, 1) if total_assets > 0 else 0.0

    st.markdown("---")
    m1, m2, m3, m4 = st.columns(4)

    with m1:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #38bdf8;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Monitored Assets</span>
                <div style="font-size:26px; font-weight:700; color:#38bdf8; margin-top:4px;">
                    {total_assets} Facilities
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    Critical Lifelines Tracked
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m2:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #ef4444;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">High / Critical Vulnerability</span>
                <div style="font-size:26px; font-weight:700; color:#ef4444; margin-top:4px;">
                    {critical_assets} Assets
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    Require Climate Hardening
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m3:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #f59e0b;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Portfolio Avg Vulnerability</span>
                <div style="font-size:26px; font-weight:700; color:#f59e0b; margin-top:4px;">
                    {avg_vuln:.1f} / 100
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    Multi-hazard weighted index
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m4:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:16px; border-radius:10px; border-left:5px solid #10b981;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Primary Vulnerability Driver</span>
                <div style="font-size:24px; font-weight:700; color:#10b981; margin-top:4px;">
                    Urban Flooding
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                    Low elevation river basins
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Interactive Geospatial Map
    st.markdown("##### 🗺️ Geospatial Asset Vulnerability & Hazard Overlay")
    map_center_lat = assets[0]["latitude"] if assets else lat
    map_center_lon = assets[0]["longitude"] if assets else lon

    infra_map = get_folium_base_map(
        location=[map_center_lat, map_center_lon],
        zoom_start=12,
        dark_mode=True,
    )

    # Add asset markers
    for a in assets:
        badge_color = a["badge_color"]
        color_name = "red" if badge_color == "#ef4444" else "orange" if badge_color == "#f97316" else "beige" if badge_color == "#f59e0b" else "green"

        measures_html = "".join([f"<li>{m}</li>" for m in a["resilience_measures"][:2]])

        popup_content = f"""
        <div style="font-family:sans-serif; min-width:220px;">
            <b style="font-size:14px; color:#0f172a;">{a['icon']} {a['name']}</b><br>
            <span style="color:#64748b; font-size:12px;">Type: <b>{a['asset_type']}</b></span><br>
            <span style="color:#64748b; font-size:12px;">Elevation: <b>{a['elevation_m']:.1f} m</b></span><hr style="margin:6px 0;">
            <b style="font-size:12px; color:#0f172a;">Vulnerability: <span style="color:{badge_color};">{a['vulnerability_score']:.1f} ({a['risk_tier']})</span></b><br>
            <div style="font-size:11px; color:#334155; margin-top:4px;">
                Flood: {a['flood_exposure_score']} | Heat: {a['heat_exposure_score']} | Fire: {a['fire_exposure_score']}
            </div>
            <div style="margin-top:6px; font-size:11px; color:#0284c7;"><b>Priority Adaptations:</b>
                <ul style="padding-left:14px; margin:2px 0;">{measures_html}</ul>
            </div>
        </div>
        """

        folium.Marker(
            location=[a["latitude"], a["longitude"]],
            popup=folium.Popup(popup_content, max_width=300),
            tooltip=f"{a['icon']} {a['name']} ({a['risk_tier']})",
            icon=folium.Icon(color=color_name, icon="info-sign"),
        ).add_to(infra_map)

        # Draw flood risk halo for assets below 210m elevation
        if a["elevation_m"] <= 210.0:
            folium.Circle(
                location=[a["latitude"], a["longitude"]],
                radius=600,
                color="#0284c7",
                weight=1,
                fill=True,
                fill_color="#38bdf8",
                fill_opacity=0.18,
                tooltip=f"Flood Risk Inundation Zone ({a['elevation_m']}m elev)",
            ).add_to(infra_map)

    if folium_static:
        folium_static(infra_map, width=1100, height=440)
    else:
        st.components.v1.html(infra_map._repr_html_(), height=440)

    # Asset Vulnerability & Prioritized Intervention Table
    st.markdown("##### 🛡️ Prioritized Engineering Adaptations & Asset Register")
    v_col1, v_col2 = st.columns([1.4, 1])

    with v_col1:
        for a in assets:
            measures_list = "".join([f"<li style='margin-bottom:4px;'>{m}</li>" for m in a["resilience_measures"]])
            st.markdown(
                f"""
                <div style="background-color:#1e293b; border-radius:8px; padding:16px; margin-bottom:12px; border-left:4px solid {a['badge_color']};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#f8fafc; font-size:15px;">{a['icon']} {a['name']}</span>
                        <span style="background-color:{a['badge_color']}22; color:{a['badge_color']}; font-weight:700; font-size:12px; padding:2px 8px; border-radius:4px;">
                            Priority #{a['priority_rank']} • {a['risk_tier']} ({a['vulnerability_score']:.1f})
                        </span>
                    </div>
                    <div style="margin-top:6px; font-size:12px; color:#94a3b8; display:flex; gap:16px;">
                        <span>Type: <b style="color:#cbd5e1;">{a['asset_type']}</b></span>
                        <span>Elevation: <b style="color:#cbd5e1;">{a['elevation_m']:.1f} m</b></span>
                        <span>Flood: <b style="color:#38bdf8;">{a['flood_exposure_score']}</b></span>
                        <span>Heat: <b style="color:#f97316;">{a['heat_exposure_score']}</b></span>
                    </div>
                    <div style="margin-top:10px; font-size:13px; color:#cbd5e1;">
                        <b style="color:#38bdf8;">Recommended Climate-Hardening Engineering:</b>
                        <ul style="margin:4px 0; padding-left:18px; color:#cbd5e1; font-size:12px;">
                            {measures_list}
                        </ul>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    with v_col2:
        st.markdown("##### 📊 Hazard Exposure Breakdown")
        df_assets = pd.DataFrame(assets)
        if not df_assets.empty:
            fig_bar = px.bar(
                df_assets,
                x="vulnerability_score",
                y="name",
                orientation="h",
                color="vulnerability_score",
                color_continuous_scale="Reds",
                labels={"vulnerability_score": "Vulnerability Score (0-100)", "name": "Asset"},
            )
            fig_bar.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color="#cbd5e1"),
                xaxis=dict(gridcolor='#334155', range=[0, 100]),
                yaxis=dict(gridcolor='#334155', tickfont=dict(size=11)),
                height=450,
                margin=dict(l=20, r=20, t=10, b=30),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # Form to add new asset
    with st.expander("➕ Register New Critical Infrastructure Asset"):
        with st.form("new_asset_form"):
            ac1, ac2 = st.columns(2)
            with ac1:
                new_name = st.text_input("Asset Name", value="South River Backup Substation")
                new_type = st.selectbox("Asset Classification", list(ASSET_CRITICALITY.keys()))
            with ac2:
                new_lat = st.number_input("Latitude", value=lat, format="%.4f")
                new_lon = st.number_input("Longitude", value=lon, format="%.4f")
                new_elev = st.number_input("Elevation (m, leave 0 for auto-lookup)", value=0.0, format="%.1f")

            submit_new_asset = st.form_submit_button("Register & Analyze Asset", type="primary")

            if submit_new_asset and new_name:
                elev_arg = new_elev if new_elev > 0 else None
                infra_service.add_asset(
                    name=new_name,
                    asset_type=new_type,
                    latitude=new_lat,
                    longitude=new_lon,
                    user_id=user_id,
                    elevation_m=elev_arg,
                )
                st.success(f"Asset '{new_name}' registered and analyzed successfully!")
                st.rerun()
