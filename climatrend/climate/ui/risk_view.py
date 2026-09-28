"""
Streamlit View Component for Feature 3: Climate-Risk & Extreme-Weather Prediction.
Provides multi-hazard risk assessment (Hazard x Exposure x Vulnerability) for
heatwaves, heavy rainfall/floods, severe storms, and agricultural drought.
Renders radar charts, hazard-specific breakdown cards, and historical logs.
"""

from datetime import datetime
from typing import Any, Dict
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from climatrend.climate.db.database import get_db
from climatrend.climate.risk.service import ClimateRiskService, classify_risk_score


def render_risk_view(translations: Dict[str, Any] = None) -> None:
    """Renders the Climate-Risk & Extreme-Weather Prediction Dashboard."""
    t = translations or {}

    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; color:#f8fafc;">⚠️ Climate-Risk & Extreme-Weather Prediction</h3>
            <span style="color:#f59e0b; font-size:13px; font-weight:600;">IPCC AR6 Framework • Hazard × Exposure × Vulnerability</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    risk_service = ClimateRiskService()

    # Load seeded regions from DB
    seeded_regions = []
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, country, latitude, longitude FROM regions ORDER BY name;")
            seeded_regions = cursor.fetchall()
    except Exception:
        pass

    region_options = {f"{r[1]}, {r[2]}": (r[0], r[3], r[4]) for r in seeded_regions}
    region_options["Custom Coordinates..."] = (None, None, None)

    # Top Control Bar
    st.markdown("##### 📍 Target Location & Socio-Economic Exposure Parameters")
    c1, c2, c3, c4 = st.columns([2.5, 1.5, 1.5, 1.5])

    with c1:
        default_idx = 0
        loc_choice = st.selectbox(
            "Select Evaluation Region",
            options=list(region_options.keys()),
            index=default_idx,
            key="risk_loc_choice",
        )

    selected_reg_id, selected_lat, selected_lon = region_options[loc_choice]

    if selected_reg_id is None:
        with c2:
            selected_lat = st.number_input("Latitude", value=28.6139, format="%.4f", key="risk_custom_lat")
        with c3:
            selected_lon = st.number_input("Longitude", value=77.2090, format="%.4f", key="risk_custom_lon")
        location_label = "Custom Target Location"
    else:
        with c2:
            st.text_input("Latitude", value=f"{selected_lat:.4f}", disabled=True)
        with c3:
            st.text_input("Longitude", value=f"{selected_lon:.4f}", disabled=True)
        location_label = loc_choice

    with c4:
        st.write("")
        st.write("")
        run_assessment = st.button("⚡ Evaluate Risk", type="primary", use_container_width=True)

    # Advanced Exposure & Vulnerability Modifiers in expander
    with st.expander("🛠️ Advanced Exposure & Vulnerability Modifiers", expanded=False):
        ec1, ec2 = st.columns(2)
        with ec1:
            pop_density = st.slider(
                "Population & Asset Exposure Multiplier",
                min_value=0.5,
                max_value=2.0,
                value=1.0,
                step=0.1,
                help="0.5 = Sparse/Rural, 1.0 = Normal Urban, 2.0 = Dense Metropolis",
                key="risk_pop_slider",
            )
        with ec2:
            vuln_factor = st.slider(
                "Infrastructure Vulnerability Multiplier",
                min_value=0.5,
                max_value=1.5,
                value=1.0,
                step=0.1,
                help="0.5 = High Climate Resilience (Seawalls, AC, Drainage), 1.5 = Fragile / Aging Infrastructure",
                key="risk_vuln_slider",
            )

    # Perform evaluation or retrieve cached
    assessment_state_key = f"risk_assessment_{location_label}_{pop_density}_{vuln_factor}"
    if run_assessment or assessment_state_key not in st.session_state:
        with st.spinner("Analyzing 7-day meteorological hazards & socio-economic vulnerability..."):
            result = risk_service.evaluate_location_risk(
                lat=selected_lat,
                lon=selected_lon,
                location_name=location_label,
                region_id=selected_reg_id,
                population_density=pop_density,
                infrastructure_resilience=vuln_factor,
            )
            st.session_state[assessment_state_key] = result

    assessment = st.session_state[assessment_state_key]
    overall_score = assessment["overall_risk_score"]
    overall_level = assessment["overall_risk_level"]
    overall_color = assessment["overall_color"]
    hazards = assessment["hazards"]

    # Top summary cards
    st.markdown("---")
    m1, m2, m3, m4 = st.columns([1.5, 1, 1, 1])

    with m1:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:18px; border-radius:10px; border-left:6px solid {overall_color};">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Composite Climate Risk</span>
                <div style="font-size:28px; font-weight:700; color:{overall_color}; margin-top:4px;">
                    {overall_score:.1f} / 100
                </div>
                <div style="margin-top:6px; font-size:14px; font-weight:600; color:#f8fafc;">
                    Classification: <span style="background-color:{overall_color}22; padding:3px 8px; border-radius:4px; color:{overall_color};">{overall_level} Risk</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Find highest risk hazard
    sorted_hazards = sorted(hazards.items(), key=lambda x: x[1]["total_risk"], reverse=True)
    top_hazard_key, top_hazard_data = sorted_hazards[0]
    second_hazard_key, second_hazard_data = sorted_hazards[1]

    with m2:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:18px; border-radius:10px;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Primary Threat</span>
                <div style="font-size:20px; font-weight:700; color:{top_hazard_data['color']}; margin-top:4px;">
                    {top_hazard_data['label']}
                </div>
                <div style="font-size:13px; color:#cbd5e1; margin-top:6px;">
                    Risk Index: <b>{top_hazard_data['total_risk']}</b> ({top_hazard_data['risk_level']})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m3:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:18px; border-radius:10px;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Secondary Threat</span>
                <div style="font-size:20px; font-weight:700; color:{second_hazard_data['color']}; margin-top:4px;">
                    {second_hazard_data['label']}
                </div>
                <div style="font-size:13px; color:#cbd5e1; margin-top:6px;">
                    Risk Index: <b>{second_hazard_data['total_risk']}</b> ({second_hazard_data['risk_level']})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with m4:
        st.markdown(
            f"""
            <div style="background-color:#1e293b; padding:18px; border-radius:10px;">
                <span style="font-size:12px; color:#94a3b8; text-transform:uppercase;">Assessment Window</span>
                <div style="font-size:20px; font-weight:700; color:#38bdf8; margin-top:4px;">
                    7-Day Horizon
                </div>
                <div style="font-size:13px; color:#cbd5e1; margin-top:6px;">
                    Updated: {assessment['evaluation_date']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<br>", unsafe_allow_html=True)

    # Visualizations: Spider/Radar Chart & Risk Breakdown
    v_col1, v_col2 = st.columns([1.2, 1])

    with v_col1:
        st.markdown("##### 🕸️ Multi-Hazard Radar Analysis")
        categories = [h["label"] for h in hazards.values()]
        hazard_scores = [h["hazard_score"] * 10.0 for h in hazards.values()]
        exposure_scores = [h["exposure_score"] * 10.0 for h in hazards.values()]
        vuln_scores = [h["vulnerability_score"] * 10.0 for h in hazards.values()]
        risk_scores = [h["total_risk"] for h in hazards.values()]

        # Radar needs closed loop
        cat_closed = categories + [categories[0]]
        fig_radar = go.Figure()

        fig_radar.add_trace(go.Scatterpolar(
            r=hazard_scores + [hazard_scores[0]],
            theta=cat_closed,
            fill='toself',
            name='Hazard Intensity (0-100)',
            line=dict(color='#f97316', width=2),
            fillcolor='rgba(249, 115, 22, 0.2)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=exposure_scores + [exposure_scores[0]],
            theta=cat_closed,
            fill='toself',
            name='Exposure Score (0-100)',
            line=dict(color='#3b82f6', width=2),
            fillcolor='rgba(59, 130, 246, 0.2)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=vuln_scores + [vuln_scores[0]],
            theta=cat_closed,
            fill='toself',
            name='Vulnerability Score (0-100)',
            line=dict(color='#a855f7', width=2),
            fillcolor='rgba(168, 85, 247, 0.2)'
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=risk_scores + [risk_scores[0]],
            theta=cat_closed,
            fill='toself',
            name='Total Risk Score (0-100)',
            line=dict(color='#ef4444', width=3),
            fillcolor='rgba(239, 68, 68, 0.3)'
        ))

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(visible=True, range=[0, 100], tickfont=dict(color='#94a3b8', size=10)),
                angularaxis=dict(tickfont=dict(color='#f8fafc', size=11, family='sans-serif')),
                bgcolor='#0f172a',
            ),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            margin=dict(l=40, r=40, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="center", x=0.5, font=dict(color="#cbd5e1")),
            height=380,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with v_col2:
        st.markdown("##### 📊 Comparative Risk Breakdown")
        df_risk = pd.DataFrame([
            {
                "Hazard": h_data["label"],
                "Hazard (0-10)": h_data["hazard_score"],
                "Exposure (0-10)": h_data["exposure_score"],
                "Vulnerability (0-10)": h_data["vulnerability_score"],
                "Risk (0-100)": h_data["total_risk"],
                "Level": h_data["risk_level"],
            }
            for h_data in hazards.values()
        ])

        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=[h["label"] for h in hazards.values()],
            y=[h["total_risk"] for h in hazards.values()],
            marker_color=[h["color"] for h in hazards.values()],
            text=[f"{h['total_risk']:.1f} ({h['risk_level']})" for h in hazards.values()],
            textposition="auto",
        ))
        fig_bar.update_layout(
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            yaxis=dict(title="Risk Score (0-100)", range=[0, 100], gridcolor='#334155', color='#94a3b8'),
            xaxis=dict(gridcolor='#334155', color='#f8fafc'),
            margin=dict(l=30, r=20, t=20, b=30),
            height=380,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    # Detailed Hazard Action Cards
    st.markdown("##### 🛡️ Hazard Diagnostic & Resilience Guidance")
    h_col1, h_col2 = st.columns(2)

    hazard_items = list(hazards.items())
    for idx, (h_key, h_data) in enumerate(hazard_items):
        target_col = h_col1 if idx % 2 == 0 else h_col2
        with target_col:
            st.markdown(
                f"""
                <div style="background-color:#1e293b; border-radius:8px; padding:15px; margin-bottom:12px; border-left:4px solid {h_data['color']};">
                    <div style="display:flex; justify-content:space-between; align-items:center;">
                        <span style="font-weight:700; color:#f8fafc; font-size:15px;">{h_data['label']}</span>
                        <span style="background-color:{h_data['color']}22; color:{h_data['color']}; font-weight:700; font-size:12px; padding:2px 8px; border-radius:4px;">
                            {h_data['risk_level']} ({h_data['total_risk']})
                        </span>
                    </div>
                    <div style="margin-top:8px; font-size:13px; color:#cbd5e1;">
                        <b>Meteorological Driver:</b> {h_data['metric_details']}
                    </div>
                    <div style="margin-top:6px; font-size:12px; color:#94a3b8; display:flex; justify-content:space-between;">
                        <span>Hazard: <b>{h_data['hazard_score']}/10</b></span>
                        <span>Exposure: <b>{h_data['exposure_score']}/10</b></span>
                        <span>Vulnerability: <b>{h_data['vulnerability_score']}/10</b></span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # Historical Risk Log Table
    st.markdown("---")
    st.markdown("##### 📜 Recent Climate Risk Assessments")
    recent_records = risk_service.get_recent_risk_assessments(limit=15)
    if recent_records:
        df_records = pd.DataFrame(recent_records)
        df_records = df_records[["assessment_date", "hazard_type", "hazard_score", "exposure_score", "vulnerability_score", "total_risk", "risk_level"]]
        df_records.columns = ["Date", "Hazard Type", "Hazard", "Exposure", "Vulnerability", "Total Risk", "Risk Level"]
        st.dataframe(df_records, use_container_width=True, hide_index=True)
    else:
        st.info("No historical risk assessments recorded yet. Click 'Evaluate Risk' above to generate assessments.")
