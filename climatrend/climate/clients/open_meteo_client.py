"""
Resilient Open-Meteo Client for weather forecast, historical archive, air quality, flood, and elevation.
No API key required; rate-limited to 10,000 req/day with graceful offline fallbacks.
"""

import datetime
import logging
from typing import Any, Dict, List, Optional

from climatrend.climate.clients.base_client import BaseResilientClient
from climatrend.climate.config import (
    DEFAULT_CACHE_TTL_DAILY,
    DEFAULT_CACHE_TTL_HOURLY,
    DEFAULT_CACHE_TTL_STATIC,
    OPEN_METEO_AIR_QUALITY_URL,
    OPEN_METEO_ARCHIVE_URL,
    OPEN_METEO_BASE_URL,
    OPEN_METEO_ELEVATION_URL,
    OPEN_METEO_FLOOD_URL,
)

logger = logging.getLogger(__name__)


class OpenMeteoClient(BaseResilientClient):
    """Client for Open-Meteo services with intelligent caching and realistic fallback data."""

    def __init__(self):
        super().__init__(name="open_meteo", cache_ttl=DEFAULT_CACHE_TTL_HOURLY)

    def fetch_weather_forecast(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetches 7-day weather forecast, hourly parameters, and current conditions."""
        url = f"{OPEN_METEO_BASE_URL}/forecast"
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,is_day",
            "hourly": "temperature_2m,relative_humidity_2m,precipitation_probability,weather_code,wind_speed_10m",
            "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max",
            "timezone": "auto",
        }
        fallback = {
            "latitude": lat,
            "longitude": lon,
            "current": {
                "temperature_2m": 20.0,
                "relative_humidity_2m": 50,
                "apparent_temperature": 20.0,
                "precipitation": 0.0,
                "weather_code": 0,
                "surface_pressure": 1013.0,
                "wind_speed_10m": 10.0,
                "wind_direction_10m": 180,
                "is_day": 1,
            },
            "daily": {
                "time": [(datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)],
                "temperature_2m_max": [22.0] * 7,
                "temperature_2m_min": [14.0] * 7,
                "precipitation_sum": [0.0] * 7,
                "precipitation_probability_max": [10] * 7,
                "wind_speed_10m_max": [15.0] * 7,
                "uv_index_max": [5.0] * 7,
            },
        }
        return self.get_json(url, params=params, fallback=fallback)

    def fetch_historical_daily(
        self, lat: float, lon: float, start_date: str, end_date: str
    ) -> Dict[str, Any]:
        """Fetches long-term historical daily parameters back to 1940 for climatology building."""
        url = OPEN_METEO_ARCHIVE_URL
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "start_date": start_date,
            "end_date": end_date,
            "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum,wind_speed_10m_max",
            "timezone": "auto",
        }
        return self.get_json(url, params=params, fallback={"daily": {}}, use_cache=True)

    def fetch_air_quality(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetches European/US AQI and criterion pollutants (PM2.5, PM10, NO2, O3, CO, SO2)."""
        url = OPEN_METEO_AIR_QUALITY_URL
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "current": "european_aqi,us_aqi,pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone",
            "hourly": "pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,ozone,us_aqi",
            "timezone": "auto",
        }
        fallback = {
            "latitude": lat,
            "longitude": lon,
            "current": {
                "us_aqi": 42,
                "european_aqi": 25,
                "pm2_5": 10.2,
                "pm10": 18.5,
                "nitrogen_dioxide": 22.1,
                "ozone": 45.0,
                "carbon_monoxide": 310.0,
                "sulphur_dioxide": 5.2,
            },
            "hourly": {
                "time": [(datetime.datetime.now() + datetime.timedelta(hours=i)).strftime("%Y-%m-%dT%H:00") for i in range(24)],
                "pm2_5": [10.0 + (i % 5) for i in range(24)],
                "us_aqi": [40 + (i % 10) for i in range(24)],
            },
        }
        return self.get_json(url, params=params, fallback=fallback)

    def fetch_flood_indicators(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fetches river discharge indicators and flood risk forecasts."""
        url = OPEN_METEO_FLOOD_URL
        params = {
            "latitude": round(lat, 4),
            "longitude": round(lon, 4),
            "daily": "river_discharge,river_discharge_mean,river_discharge_median,river_discharge_max",
            "forecast_days": 10,
        }
        fallback = {
            "daily": {
                "time": [(datetime.date.today() + datetime.timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10)],
                "river_discharge": [12.5] * 10,
                "river_discharge_max": [15.0] * 10,
            }
        }
        return self.get_json(url, params=params, fallback=fallback)

    def fetch_elevation(self, lat: float, lon: float) -> float:
        """Fetches terrain elevation in meters."""
        url = OPEN_METEO_ELEVATION_URL
        params = {"latitude": round(lat, 4), "longitude": round(lon, 4)}
        data = self.get_json(url, params=params, fallback={"elevation": [25.0]})
        try:
            return float(data.get("elevation", [25.0])[0])
        except Exception:
            return 25.0
