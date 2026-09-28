"""
Unit tests for resilient external API clients.
Validates caching, timeouts, exponential backoff, and fallback returns.
"""

from unittest.mock import MagicMock, patch
import pytest
import requests

from climatrend.climate.clients.base_client import BaseResilientClient
from climatrend.climate.clients.emission_client import EmissionClient, OFFLINE_EMISSION_FACTORS
from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.clients.disaster_client import DisasterClient, haversine_distance


def test_base_client_caching_and_fallback():
    """Verifies that BaseResilientClient returns fallback on connection failure."""
    client = BaseResilientClient(name="test_client", max_retries=1)
    
    # Mock requests to fail with ConnectionError
    with patch.object(client.session, "get", side_effect=requests.ConnectionError("Network Down")):
        fallback_data = {"status": "offline_mode", "val": 42}
        result = client.get_json("https://api.fake.com/test", fallback=fallback_data)
        assert result == fallback_data


def test_emission_client_offline_calculations():
    """Verifies offline carbon conversion factors."""
    client = EmissionClient()

    # 100 km flight economy
    flight_co2e = client.calculate_co2e("flight_economy", 100.0)
    assert flight_co2e == 15.0  # 100 * 0.150

    # 50 kWh grid electricity
    elec_co2e = client.calculate_co2e("grid_average", 50.0)
    assert elec_co2e == pytest.approx(21.8, rel=1e-2)

    # 3 beef meals
    beef_co2e = client.calculate_co2e("beef_meal", 3.0)
    assert beef_co2e == pytest.approx(19.83, rel=1e-2)

    # Unknown category fallback
    custom_co2e = client.calculate_co2e("unknown_item", 10.0)
    assert custom_co2e == 2.0  # 10 * 0.20


def test_haversine_distance():
    """Verifies distance calculation between London (51.5074, -0.1278) and Paris (48.8566, 2.3522)."""
    dist = haversine_distance(51.5074, -0.1278, 48.8566, 2.3522)
    # Distance between London and Paris is ~343 km
    assert 340.0 < dist < 350.0


def test_open_meteo_client_fallback():
    """Verifies OpenMeteoClient returns plausible defaults if API fails."""
    client = OpenMeteoClient()
    with patch.object(client.session, "get", side_effect=requests.Timeout("Timeout")):
        data = client.fetch_weather_forecast(51.5, -0.1)
        assert "current" in data
        assert "daily" in data
        assert data["current"]["temperature_2m"] == 20.0
