"""
Climate UI Views Package for Streamlit dashboard integration.
"""

from climatrend.climate.ui.air_quality_view import render_air_quality_view
from climatrend.climate.ui.disaster_view import render_disaster_view
from climatrend.climate.ui.regional_alert_view import render_regional_alert_view
from climatrend.climate.ui.carbon_view import render_carbon_view

__all__ = [
    "render_air_quality_view",
    "render_disaster_view",
    "render_regional_alert_view",
    "render_carbon_view",
]
