"""
Streamlit View Component for Feature 1: Carbon-Footprint Tracking & Emission Analytics.
Provides interactive activity logging across Travel, Electricity, Food, and Waste,
visualizes daily/weekly/monthly trends and category breakdowns,
runs Isolation Forest anomaly detection, and displays SHAP explanations.
"""

from datetime import datetime
from typing import Any, Dict
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from climatrend.climate.carbon.anomaly_detector import CarbonAnomalyDetector
from climatrend.climate.carbon.explainer import CarbonSHAPExplainer
from climatrend.climate.carbon.service import CarbonService
from climatrend.climate.clients.emission_client import OFFLINE_EMISSION_FACTORS


def render_carbon_view(user_id: str = "user_default", translations: Dict[str, Any] = None) -> None:
    """Renders the Carbon-Footprint Tracking & Emission Analytics Dashboard."""
    t = translations or {}

    st.markdown(
        """
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; color:#f8fafc;">👣 Carbon-Footprint Tracking & Emission Analytics</h3>
            <span style="color:#10b981; font-size:13px; font-weight:600;">GHG Protocol • DEFRA & EPA Factors</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    service = CarbonService()
    detector = CarbonAnomalyDetector()
    explainer = CarbonSHAPExplainer()

    # Automatically seed demonstration activities if table is currently empty
    service.seed_sample_activities_if_empty(user_id=user_id)

    # 1. Activity Logging Form (Expander / Card)
    with st.expander("➕ Log New Carbon Emission Activity", expanded=False):
        c_form1, c_form2, c_form3 = st.columns(3)

        with c_form1:
            category = st.selectbox(
                "Activity Category",
                ["travel", "electricity", "food", "waste"],
                format_func=lambda x: {
                    "travel": "✈️ Travel & Commute",
                    "electricity": "⚡ Household Electricity",
                    "food": "🍽️ Dietary Choices",
                    "waste": "🗑️ Waste Disposal",
                }.get(x, x),
            )

        # Filter subcategories belonging to category
        available_subcats = {
            k: v for k, v in OFFLINE_EMISSION_FACTORS.items() if v["category"] == category
        }

        with c_form2:
            subcategory = st.selectbox(
                "Subcategory / Activity Type",
                list(available_subcats.keys()),
                format_func=lambda k: f"{available_subcats[k]['label']} ({available_subcats[k]['factor']} kg CO₂e/{available_subcats[k]['unit']})",
            )
            unit_label = available_subcats[subcategory]["unit"]

        with c_form3:
            val_input = st.number_input(f"Value ({unit_label})", min_value=0.1, value=10.0, step=1.0)

        f_d1, f_d2, f_d3 = st.columns([1.5, 2.5, 1])
        with f_d1:
            act_date = st.date_input("Activity Date", value=datetime.utcnow().date())
        with f_d2:
            notes_input = st.text_input("Notes / Context", placeholder="e.g. Commute to office, flight to Berlin")
        with f_d3:
            st.write("")
            st.write("")
            if st.button("💾 Record Activity", use_container_width=True):
                service.log_activity(
                    user_id=user_id,
                    activity_date=act_date.strftime("%Y-%m-%d"),
                    category=category,
                    subcategory=subcategory,
                    value=float(val_input),
                    unit=unit_label,
                    notes=notes_input,
                )
                st.success("Activity recorded successfully!")
                st.rerun()

    # Load and evaluate user activities
    df_raw = service.get_user_activities(user_id=user_id)

    # Run Isolation Forest anomaly detection
    df = detector.fit_and_detect(df_raw, update_db=True) if not df_raw.empty else df_raw
    metrics = service.get_aggregated_metrics(user_id=user_id)

    # 2. KPI Summary Cards
    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">TOTAL LIFETIME FOOTPRINT</div>
                <div class="metric-val" style="color:#00ffff;">{metrics['total_co2e_kg']:,.1f} kg</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">{metrics['total_co2e_tonnes']:.2f} Metric Tonnes CO₂e</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">CURRENT MONTH EMISSIONS</div>
                <div class="metric-val" style="color:#f59e0b;">{metrics['monthly_co2e_kg']:,.1f} kg</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Month of {datetime.utcnow().strftime('%B %Y')}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">WEEKLY RUN-RATE AVERAGE</div>
                <div class="metric-val">{metrics['weekly_avg_kg']:.1f} kg</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Rolling Weekly Average</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with k4:
        anom_c = metrics["anomaly_count"]
        anom_color = "#ef4444" if anom_c > 0 else "#10b981"
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-lbl">FLAGGED ANOMALIES</div>
                <div class="metric-val" style="color:{anom_color};">{anom_c} Events</div>
                <div style="font-size:11px; color:#94a3b8; margin-top:2px;">Isolation Forest Outliers</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # 3. Emission Analytics Charts
    col_trend, col_pie = st.columns([1.8, 1.2])

    with col_trend:
        st.markdown("#### 📈 Carbon Emission Trend Line (Daily Cumulative)")
        if not df.empty:
            daily_series = df.groupby("activity_date")["co2e_kg"].sum().reset_index().sort_values("activity_date")
            fig_trend = go.Figure()
            fig_trend.add_trace(
                go.Scatter(
                    x=daily_series["activity_date"],
                    y=daily_series["co2e_kg"],
                    mode="lines+markers",
                    line=dict(color="#10b981", width=2.5),
                    marker=dict(size=6, color="#00ffff"),
                    name="Daily CO₂e",
                )
            )

            # Highlight anomalies on the trend line
            anom_points = df[df["is_anomaly"] == 1]
            if not anom_points.empty:
                fig_trend.add_trace(
                    go.Scatter(
                        x=anom_points["activity_date"],
                        y=anom_points["co2e_kg"],
                        mode="markers",
                        marker=dict(size=12, color="#ef4444", symbol="triangle-up"),
                        name="Anomaly Outlier",
                    )
                )

            fig_trend.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Date",
                yaxis_title="Emissions (kg CO₂e)",
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                hovermode="x unified",
            )
            st.plotly_chart(fig_trend, use_container_width=True)

    with col_pie:
        st.markdown("#### 🥧 Category Emission Breakdown")
        cat_data = metrics["category_breakdown"]
        if cat_data:
            fig_pie = go.Figure(
                data=[
                    go.Pie(
                        labels=[k.title() for k in cat_data.keys()],
                        values=list(cat_data.values()),
                        hole=0.45,
                        marker=dict(colors=["#38bdf8", "#f59e0b", "#10b981", "#a855f7"]),
                    )
                ]
            )
            fig_pie.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=320,
                margin=dict(l=10, r=10, t=10, b=10),
                legend=dict(orientation="h", yanchor="bottom", y=-0.1, xanchor="center", x=0.5),
            )
            st.plotly_chart(fig_pie, use_container_width=True)

    st.markdown("---")

    # 4. Anomaly Detection & SHAP Explanations Panel
    st.markdown("#### 🧠 Anomaly Detection (Isolation Forest) & SHAP Explanations")
    anomalies = df[df["is_anomaly"] == 1] if not df.empty and "is_anomaly" in df.columns else pd.DataFrame()

    if not anomalies.empty:
        col_anom_table, col_shap = st.columns([1.6, 1.4])

        with col_anom_table:
            st.markdown(f"**Identified {len(anomalies)} statistical anomaly events:**")
            display_anom = anomalies[["activity_date", "category", "subcategory", "value", "unit", "co2e_kg"]].copy()
            display_anom.columns = ["Date", "Category", "Subcategory", "Value", "Unit", "CO₂e (kg)"]
            st.dataframe(display_anom, use_container_width=True)

        with col_shap:
            st.markdown("**SHAP Feature Contribution for Top Anomaly:**")
            top_anom = anomalies.iloc[0]
            feature_cols = detector.feature_cols
            explainer.fit_surrogate(df, feature_cols)
            exp_res = explainer.explain_activity(top_anom, feature_cols)

            st.info(f"💡 {exp_res['summary']}")
            shap_vals = exp_res["shap_values"]
            fig_shap = go.Figure(
                go.Bar(
                    x=list(shap_vals.values()),
                    y=list(shap_vals.keys()),
                    orientation="h",
                    marker=dict(color=["#ef4444" if v > 0 else "#10b981" for v in shap_vals.values()]),
                )
            )
            fig_shap.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=200,
                margin=dict(l=10, r=10, t=10, b=10),
                xaxis_title="SHAP Impact (kg CO₂e)",
            )
            st.plotly_chart(fig_shap, use_container_width=True)
    else:
        st.info("No unusual emission spikes detected. Activity patterns are consistent with normal baselines.")

    # 5. Full Activity Log
    with st.expander("📋 Full Activity Log & Raw Data"):
        if not df.empty:
            st.dataframe(
                df[["activity_date", "category", "subcategory", "value", "unit", "co2e_kg", "is_anomaly", "notes"]],
                use_container_width=True,
            )
            csv_data = df.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Download Carbon Log as CSV",
                data=csv_data,
                file_name=f"carbon_footprint_{user_id}_{datetime.utcnow().strftime('%Y%m%d')}.csv",
                mime="text/csv",
            )
