"""
Unit tests for Feature 3: Climate-Risk & Extreme-Weather Prediction.
"""

from unittest.mock import MagicMock
import pytest

from climatrend.climate.risk.service import ClimateRiskService, classify_risk_score


def test_classify_risk_score():
    assert classify_risk_score(15.0)[0] == "Low"
    assert classify_risk_score(35.0)[0] == "Medium"
    assert classify_risk_score(60.0)[0] == "High"
    assert classify_risk_score(85.0)[0] == "Severe"


def test_evaluate_location_risk_and_db_persistence():
    mock_client = MagicMock()
    # High heat and high rain forecast
    mock_client.fetch_weather_forecast.return_value = {
        "daily": {
            "temperature_2m_max": [36.0, 37.5, 38.0, 35.0, 34.0, 31.0, 30.0],
            "precipitation_sum": [15.0, 30.0, 45.0, 5.0, 0.0, 0.0, 0.0],
            "wind_speed_10m_max": [45.0, 60.0, 35.0, 20.0, 15.0, 10.0, 12.0],
        }
    }

    service = ClimateRiskService(open_meteo_client=mock_client)
    res = service.evaluate_location_risk(
        lat=28.6139,
        lon=77.2090,
        location_name="New Delhi",
        region_id=1,
        population_density=1.2,
        infrastructure_resilience=1.1,
    )

    assert res["location_name"] == "New Delhi"
    assert 0 <= res["overall_risk_score"] <= 100
    assert res["overall_risk_level"] in ["Low", "Medium", "High", "Severe"]

    hazards = res["hazards"]
    assert "extreme_heat" in hazards
    assert "heavy_rain_flood" in hazards
    assert "storm_wind" in hazards
    assert "drought" in hazards

    # Heat hazard should be notable given 36-38 C
    assert hazards["extreme_heat"]["hazard_score"] > 5.0
    # Flood hazard should be notable given 95mm total
    assert hazards["heavy_rain_flood"]["hazard_score"] > 5.0

    # Test retrieval from database
    recent = service.get_recent_risk_assessments(region_id=1, limit=5)
    assert len(recent) >= 4
    assert recent[0]["hazard_type"] in hazards
