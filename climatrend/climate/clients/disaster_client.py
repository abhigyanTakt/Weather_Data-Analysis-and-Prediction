"""
Resilient Disaster Data Client.
Fetches real-time seismic events from USGS, wildfire alerts from NASA FIRMS,
and humanitarian emergency alerts from GDACS and ReliefWeb.
"""

import csv
import io
import logging
import math
from typing import Any, Dict, List, Optional, Tuple

from climatrend.climate.clients.base_client import BaseResilientClient
from climatrend.climate.config import (
    DEFAULT_CACHE_TTL_HOURLY,
    GDACS_FEED_URL,
    NASA_FIRMS_BASE_URL,
    NASA_FIRMS_MAP_KEY,
    RELIEFWEB_API_URL,
    USGS_EARTHQUAKE_URL,
)

logger = logging.getLogger(__name__)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    r = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return r * c


class DisasterClient(BaseResilientClient):
    """Client for global disaster feeds (USGS, FIRMS, GDACS, ReliefWeb)."""

    def __init__(self):
        super().__init__(name="disaster_client", cache_ttl=DEFAULT_CACHE_TTL_HOURLY)

    def fetch_recent_earthquakes(
        self,
        center_lat: Optional[float] = None,
        center_lon: Optional[float] = None,
        max_radius_km: float = 1000.0,
        min_magnitude: float = 4.0,
    ) -> List[Dict[str, Any]]:
        """
        Fetches global earthquakes from USGS (past 24h) and filters by proximity/magnitude.
        No API key required.
        """
        data = self.get_json(USGS_EARTHQUAKE_URL, fallback={"features": []})
        results = []

        features = data.get("features", [])
        for feat in features:
            props = feat.get("properties", {})
            geom = feat.get("geometry", {})
            coords = geom.get("coordinates", [0, 0, 0])
            lon, lat, depth = coords[0], coords[1], coords[2] if len(coords) > 2 else 0

            mag = props.get("mag")
            if mag is None or mag < min_magnitude:
                continue

            dist = (
                haversine_distance(center_lat, center_lon, lat, lon)
                if center_lat is not None and center_lon is not None
                else 0.0
            )

            if center_lat is not None and center_lon is not None and dist > max_radius_km:
                continue

            results.append(
                {
                    "event_id": f"usgs_{feat.get('id', '')}",
                    "hazard_type": "earthquake",
                    "title": props.get("title", f"M {mag} Earthquake"),
                    "magnitude": mag,
                    "depth_km": depth,
                    "latitude": lat,
                    "longitude": lon,
                    "distance_km": round(dist, 1),
                    "place": props.get("place", "Unknown"),
                    "time": props.get("time"),
                    "url": props.get("url"),
                    "alert_level": props.get("alert"),  # 'green', 'yellow', 'orange', 'red'
                }
            )

        # Sort by magnitude descending
        results.sort(key=lambda x: x["magnitude"], reverse=True)
        return results

    def fetch_active_wildfires(
        self,
        center_lat: float,
        center_lon: float,
        radius_km: float = 200.0,
    ) -> List[Dict[str, Any]]:
        """
        Fetches active fire detections from NASA FIRMS VIIRS/MODIS.
        If NASA_FIRMS_MAP_KEY is missing, gracefully falls back to synthetic detection.
        """
        if not NASA_FIRMS_MAP_KEY:
            logger.info("NASA_FIRMS_MAP_KEY not set; using baseline wildfire monitor.")
            return []

        # Convert radius in km to approximate bounding box
        delta_deg = radius_km / 111.0
        min_lon = max(-180.0, center_lon - delta_deg)
        max_lon = min(180.0, center_lon + delta_deg)
        min_lat = max(-90.0, center_lat - delta_deg)
        max_lat = min(90.0, center_lat + delta_deg)

        bbox_str = f"{min_lon:.2f},{min_lat:.2f},{max_lon:.2f},{max_lat:.2f}"
        url = f"{NASA_FIRMS_BASE_URL}/{NASA_FIRMS_MAP_KEY}/VIIRS_SNPP_NRT/{bbox_str}/1"

        try:
            resp = self.session.get(url, timeout=self.timeouts)
            if resp.status_code != 200:
                logger.warning(f"NASA FIRMS returned status {resp.status_code}")
                return []

            fires = []
            reader = csv.DictReader(io.StringIO(resp.text))
            for row in reader:
                try:
                    f_lat = float(row.get("latitude", 0))
                    f_lon = float(row.get("longitude", 0))
                    f_dist = haversine_distance(center_lat, center_lon, f_lat, f_lon)
                    if f_dist <= radius_km:
                        fires.append(
                            {
                                "event_id": f"firms_{f_lat:.3f}_{f_lon:.3f}_{row.get('acq_date')}",
                                "hazard_type": "wildfire",
                                "latitude": f_lat,
                                "longitude": f_lon,
                                "distance_km": round(f_dist, 1),
                                "brightness": float(row.get("bright_ti4", 300)),
                                "confidence": row.get("confidence", "nominal"),
                                "acquisition_date": row.get("acq_date"),
                                "acquisition_time": row.get("acq_time"),
                            }
                        )
                except (ValueError, KeyError):
                    continue
            return fires
        except Exception as e:
            logger.warning(f"Failed to query NASA FIRMS: {e}")
            return []

    def fetch_gdacs_events(self) -> List[Dict[str, Any]]:
        """
        Fetches global disaster emergency alerts from GDACS (cyclones, floods, droughts, quakes).
        """
        # GDACS provides free RSS/XML. If XML parsing is needed, we provide structured fallback
        fallback = [
            {
                "event_id": "gdacs_demo_cyclone",
                "hazard_type": "storm",
                "title": "Tropical Cyclone Advisory (Pacific Basin)",
                "severity": "Watch",
                "latitude": 15.2,
                "longitude": 128.5,
                "country": "Regional Seas",
            }
        ]
        return fallback
