"""
Unit tests for Feature 5: Climate-Resilient Infrastructure Planning.
"""

from unittest.mock import MagicMock, patch
import pytest

from climatrend.climate.infrastructure.service import (
    ASSET_CRITICALITY,
    RESILIENCE_CATALOG,
    InfrastructureService,
)


def test_elevation_fetch_and_fallback():
    service = InfrastructureService()
    # Test with patched requests
    with patch("requests.get") as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {"elevation": [185.5]}
        elev = service.fetch_elevation_meters(28.6139, 77.2090)
        assert elev == 185.5

    # Test with network error fallback
    with patch("requests.get", side_effect=Exception("Connection timeout")):
        fallback_elev = service.fetch_elevation_meters(28.6139, 77.2090)
        assert fallback_elev > 0


def test_asset_vulnerability_evaluation():
    mock_client = MagicMock()
    mock_client.fetch_weather_forecast.return_value = {
        "daily": {
            "temperature_2m_max": [41.0, 42.0, 40.0],
            "precipitation_sum": [50.0, 80.0, 30.0],
            "wind_speed_10m_max": [35.0, 45.0, 30.0],
        }
    }

    service = InfrastructureService(open_meteo_client=mock_client)

    # Low elevation hospital in high rain/heat zone
    res = service.evaluate_asset_vulnerability(
        asset_type="Hospital",
        lat=28.6250,
        lon=77.2180,
        elevation_m=12.0,
    )

    assert 0 <= res["flood_exposure_score"] <= 100
    assert 0 <= res["heat_exposure_score"] <= 100
    assert 0 <= res["fire_exposure_score"] <= 100
    assert 0 <= res["vulnerability_score"] <= 100
    assert res["priority_rank"] in [1, 2, 3, 4]
    assert len(res["resilience_measures"]) >= 2
    # Flood exposure should be high because elevation is only 12m and rainfall is high
    assert res["flood_exposure_score"] > 50.0


def test_asset_crud_and_seeding():
    service = InfrastructureService()
    user_test = "test_user_infra"

    # Seed demo assets
    service.seed_default_assets_if_empty(user_id=user_test)
    assets = service.get_assets(user_id=user_test)
    assert len(assets) >= 5

    # Add custom asset
    new_asset = service.add_asset(
        name="Test Emergency Station",
        asset_type="Emergency Response Center",
        latitude=28.6300,
        longitude=77.2200,
        user_id=user_test,
        elevation_m=210.0,
    )
    assert new_asset["id"] is not None
    assert new_asset["name"] == "Test Emergency Station"

    # Delete asset
    del_ok = service.delete_asset(new_asset["id"])
    assert del_ok is True
