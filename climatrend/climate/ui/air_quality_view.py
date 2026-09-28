"""
Streamlit View Component for Feature 2: Air Pollution & Environmental Monitoring.
Displays live AQI, pollutant breakdown, health advisory badges, interactive Folium map,
and a 24-72h forecast chart with XGBoost baseline comparison.
"""

from typing import Any, Dict
import folium
import plotly.graph_objects as go
import streamlit as st

from climatrend.climate.air_quality.forecaster import AirQualityForecaster
from climatrend.climate.air_quality.service import AirQualityService
from climatrend.climate.ui.map_helper import get_folium_base_map

try:
    from streamlit_folium import folium_static
except ImportError:
    folium_static = None


def render_air_quality_view(
    city_name: str,
    lat: float,
    lon: float,
    temp_unit: str = "°C",
    translations: Dict[str, Any] = None,
) -> None:
    """Renders the Air Pollution Monitoring dashboard."""
    t = translations or {}

    st.markdown(
        f"""
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:15px;">
            <h3 style="margin:0; color:#f8fafc;">🍃 Air Pollution & Environmental Monitoring: <b>{city_name}</b></h3>
            <span style="color:#00ffff; font-size:13px; font-weight:600;">Data Source: Open-Meteo & OpenAQ</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

    service = AirQualityService()

    with st.spinner("Fetching real-time air quality & pollutant data..."):
        current_data = service.get_current_air_quality(lat, lon, location_name=city_name)
        forecast_df = service.get_forecast_72h(lat, lon)

    aqi_val = current_data["aqi"]
    category = current_data["category"]
    cat_color = current_data["color"]
    pollutants = current_data["pollutants"]

    # Top Section: AQI Gauge Card & Medical / Public Health Guidance Banner
    col_aqi, col_guidance = st.columns([1.2, 2.8])

    with col_aqi:
        st.markdown(
            f"""
            <div class="metric-card" style="text-align:center; padding: 24px 16px; border: 2px solid {cat_color};">
                <div class="metric-lbl" style="letter-spacing: 0.1em;">US AIR QUALITY INDEX (AQI)</div>
                <div style="font-size: 56px; font-weight: 800; color: {cat_color}; margin: 8px 0; text-shadow: 0 0 15px {cat_color}66;">
                    {aqi_val}
                </div>
                <div style="font-size: 18px; font-weight: 700; color: {cat_color}; text-transform: uppercase;">
                    {category}
                </div>
                <div style="font-size: 11px; color: #94a3b8; margin-top: 8px;">
                    Observed for {city_name} ({lat:.2f}, {lon:.2f})
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_guidance:
        st.markdown(
            f"""
            <div class="metric-card" style="padding: 18px;">
                <div style="font-size: 15px; font-weight: 700; color: #f8fafc; margin-bottom: 6px;">
                    🏥 Health Guidance & Advisory
                </div>
                <div style="color: #cbd5e1; font-size: 13px; margin-bottom: 10px;">
                    {current_data['description']}
                </div>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 12px;">
                    <div style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px; border-left: 3px solid #00ffff;">
                        <b>🏃 General Public:</b><br>{current_data['general_advice']}
                    </div>
                    <div style="background: rgba(15, 23, 42, 0.6); padding: 8px; border-radius: 6px; border-left: 3px solid #f59e0b;">
                        <b>🫁 Sensitive Groups:</b><br>{current_data['sensitive_advice']}
                    </div>
                </div>
                <div style="margin-top: 8px; font-size: 12px; color: #94a3b8;">
                    🪟 <b>Indoor Ventilation:</b> {current_data['ventilation']}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("---")

    # Criteria Pollutant Metric Breakdown
    st.markdown("#### 🔬 Criteria Air Pollutants Breakdown")
    p_cols = st.columns(6)

    pollutant_specs = [
        ("PM2.5 (Fine Particles)", pollutants.get("pm2_5", 0.0), "µg/m³", "WHO Limit: 15 µg/m³"),
        ("PM10 (Coarse Dust)", pollutants.get("pm10", 0.0), "µg/m³", "WHO Limit: 45 µg/m³"),
        ("NO2 (Nitrogen Dioxide)", pollutants.get("no2", 0.0), "µg/m³", "WHO Limit: 25 µg/m³"),
        ("O3 (Ground Ozone)", pollutants.get("o3", 0.0), "µg/m³", "WHO Limit: 100 µg/m³"),
        ("CO (Carbon Monoxide)", pollutants.get("co", 0.0), "µg/m³", "WHO Limit: 4000 µg/m³"),
        ("SO2 (Sulfur Dioxide)", pollutants.get("so2", 0.0), "µg/m³", "WHO Limit: 40 µg/m³"),
    ]

    for idx, (p_name, p_val, p_unit, p_limit) in enumerate(pollutant_specs):
        with p_cols[idx]:
            val_float = float(p_val) if p_val is not None else 0.0
            st.markdown(
                f"""
                <div class="metric-card" style="padding: 12px; text-align: center;">
                    <div class="metric-lbl" style="font-size: 10px;">{p_name.split(' ')[0]}</div>
                    <div class="metric-val" style="font-size: 20px; margin: 4px 0;">{val_float:.1f}</div>
                    <div style="font-size: 11px; color: #64748b;">{p_unit}</div>
                    <div style="font-size: 9px; color: #94a3b8; margin-top: 4px;">{p_limit}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown("---")

    # Map & 72-Hour Forecast Section
    col_map, col_chart = st.columns([1.2, 1.8])

    with col_map:
        st.markdown(f"#### 🗺️ Sensor Station Location: **{city_name}**")
        m = get_folium_base_map(location=[lat, lon], zoom_start=9, dark_mode=True)
        folium.CircleMarker(
            location=[lat, lon],
            radius=16,
            color=cat_color,
            fill=True,
            fill_color=cat_color,
            fill_opacity=0.7,
            popup=f"<b>{city_name}</b><br>AQI: {aqi_val} ({category})<br>PM2.5: {pollutants.get('pm2_5', 0):.1f} µg/m³",
        ).add_to(m)

        if folium_static:
            folium_static(m, width=420, height=350)
        else:
            st.info("Map rendered via HTML iframe:")
            st.components.v1.html(m._repr_html_(), height=360)

    with col_chart:
        st.markdown("#### 📈 72-Hour AQI & PM2.5 Forecast (XGBoost Baseline)")

        forecaster = AirQualityForecaster(target_col="pm2_5")
        ml_results = forecaster.train_and_predict(forecast_df, horizon_hours=72)
        f_res_df = ml_results["forecast_df"]

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=forecast_df["time"],
                y=forecast_df["pm2_5"] if "pm2_5" in forecast_df.columns else f_res_df["actual"],
                name="Open-Meteo Meteorological Forecast",
                line=dict(color="#38bdf8", width=2),
            )
        )
        fig.add_trace(
            go.Scatter(
                x=f_res_df["time"],
                y=f_res_df["xgboost_forecast"],
                name="XGBoost Baseline Model",
                line=dict(color="#f59e0b", width=2, dash="dot"),
            )
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis_title="Timeline (Next 72 Hours)",
            yaxis_title="PM2.5 (µg/m³)",
            hovermode="x unified",
            height=340,
            margin=dict(l=10, r=10, t=20, b=20),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        st.plotly_chart(fig, use_container_width=True)

    # Feature Importance Breakdown
    with st.expander("🧠 XGBoost Model Feature Importances & Diagnostics"):
        f_cols = st.columns([2, 1])
        with f_cols[0]:
            imp_dict = ml_results["feature_importances"]
            fig_imp = go.Figure(
                go.Bar(
                    x=list(imp_dict.values())[:8],
                    y=list(imp_dict.keys())[:8],
                    orientation="h",
                    marker=dict(color="#00ffff"),
                )
            )
            fig_imp.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=220,
                margin=dict(l=10, r=10, t=10, b=10),
                yaxis=dict(autorange="reversed"),
                xaxis_title="Relative Feature Importance Score",
            )
            st.plotly_chart(fig_imp, use_container_width=True)
        with f_cols[1]:
            st.markdown(
                f"""
                <div class="metric-card" style="margin-top: 15px;">
                    <div class="metric-lbl">MODEL VALIDATION METRICS</div>
                    <div style="font-size:14px; margin-top:8px;"><b>MAE:</b> {ml_results['metrics']['mae']} µg/m³</div>
                    <div style="font-size:14px; margin-top:4px;"><b>RMSE:</b> {ml_results['metrics']['rmse']} µg/m³</div>
                    <div style="font-size:11px; color:#94a3b8; margin-top:8px;">
                        Gradient-boosted regressor fitting autoregressive lag terms (lag_1, lag_2) and temporal cyclical features.
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
