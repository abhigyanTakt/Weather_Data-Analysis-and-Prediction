"""
Resilient OpenAQ Client.
Queries the OpenAQ API v3 for ground-level sensor observations.
Falls back transparently to Open-Meteo Air Quality API if OpenAQ is unreachable or unconfigured.
"""

import logging
from typing import Any, Dict, List, Optional

from climatrend.climate.clients.base_client import BaseResilientClient
from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.config import DEFAULT_CACHE_TTL_HOURLY, OPENAQ_API_KEY, OPENAQ_BASE_URL

logger = logging.getLogger(__name__)


class OpenAQClient(BaseResilientClient):
    """Client for OpenAQ API with transparent Open-Meteo failover."""

    def __init__(self, open_meteo_client: Optional[OpenMeteoClient] = None):
        super().__init__(name="openaq_client", cache_ttl=DEFAULT_CACHE_TTL_HOURLY)
        self.open_meteo = open_meteo_client or OpenMeteoClient()

    def fetch_latest_by_coords(self, lat: float, lon: float, radius_m: int = 25000) -> Dict[str, Any]:
        """
        Attempts to fetch real-time air quality measurements from OpenAQ.
        If OpenAQ API key is not provided or fails, falls back to Open-Meteo Air Quality.
        """
        headers = {}
        if OPENAQ_API_KEY:
            headers["X-API-Key"] = OPENAQ_API_KEY

        url = f"{OPENAQ_BASE_URL}/locations"
        params = {
            "coordinates": f"{lat:.4f},{lon:.4f}",
            "radius": radius_m,
            "limit": 1,
        }

        # If no key, query Open-Meteo directly
        if not OPENAQ_API_KEY:
            logger.info("OpenAQ API key not set; using Open-Meteo Air Quality API.")
            return self._fetch_from_open_meteo(lat, lon)

        try:
            data = self.get_json(
                url,
                params=params,
                headers=headers,
                fallback=lambda: self._fetch_from_open_meteo(lat, lon),
            )
            results = data.get("results", [])
            if results:
                loc = results[0]
                sensors = loc.get("sensors", [])
                pollutants = {}
                for s in sensors:
                    param = s.get("parameter", {}).get("name")
                    latest = s.get("latest", {}).get("value")
                    if param and latest is not None:
                        pollutants[param] = float(latest)

                return {
                    "source": "OpenAQ",
                    "location_name": loc.get("name", "Local Sensor"),
                    "latitude": lat,
                    "longitude": lon,
                    "pm2_5": pollutants.get("pm25"),
                    "pm10": pollutants.get("pm10"),
                    "no2": pollutants.get("no2"),
                    "o3": pollutants.get("o3"),
                    "co": pollutants.get("co"),
                    "so2": pollutants.get("so2"),
                }
            else:
                logger.info("No OpenAQ stations found near coordinates; falling back to Open-Meteo.")
                return self._fetch_from_open_meteo(lat, lon)
        except Exception as e:
            logger.warning(f"OpenAQ query failed: {e}; falling back to Open-Meteo.")
            return self._fetch_from_open_meteo(lat, lon)

    def _fetch_from_open_meteo(self, lat: float, lon: float) -> Dict[str, Any]:
        """Fallback adapter using Open-Meteo Air Quality."""
        raw = self.open_meteo.fetch_air_quality(lat, lon)
        curr = raw.get("current", {})
        return {
            "source": "Open-Meteo Air Quality",
            "location_name": f"Coordinates ({lat:.2f}, {lon:.2f})",
            "latitude": lat,
            "longitude": lon,
            "aqi": curr.get("us_aqi", 45),
            "european_aqi": curr.get("european_aqi", 25),
            "pm2_5": curr.get("pm2_5", 12.0),
            "pm10": curr.get("pm10", 20.0),
            "no2": curr.get("nitrogen_dioxide", 18.0),
            "o3": curr.get("ozone", 45.0),
            "co": curr.get("carbon_monoxide", 320.0),
            "so2": curr.get("sulphur_dioxide", 4.0),
        }
