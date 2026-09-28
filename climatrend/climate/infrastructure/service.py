"""
Climate-Resilient Infrastructure Planning Service.
Manages critical municipal and enterprise infrastructure assets (Hospitals,
Power Substations, Water Treatment Plants, Bridges, Emergency Response).
Evaluates elevation, flood exposure, heat stress, and wildfire proximity.
Calculates vulnerability scores and recommends tailored engineering resilience adaptations.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional
import requests

from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)

ASSET_CRITICALITY = {
    "Hospital": {"tier": 1, "weight": 1.35, "icon": "🏥"},
    "Emergency Response Center": {"tier": 1, "weight": 1.35, "icon": "🚒"},
    "Power Substation": {"tier": 1, "weight": 1.30, "icon": "⚡"},
    "Water Treatment Plant": {"tier": 1, "weight": 1.25, "icon": "💧"},
    "Bridge & Evacuation Route": {"tier": 2, "weight": 1.15, "icon": "🌉"},
    "Telecommunications Hub": {"tier": 2, "weight": 1.15, "icon": "📡"},
    "School / Community Shelter": {"tier": 2, "weight": 1.10, "icon": "🏫"},
    "Transit Station / Airport": {"tier": 3, "weight": 1.05, "icon": "🚆"},
    "Commercial Facility": {"tier": 3, "weight": 1.00, "icon": "🏢"},
}

RESILIENCE_CATALOG = {
    "Hospital": [
        "Elevate backup generators above 100-year flood line (+2.0m)",
        "Install redundant HVAC HEPA filtration for wildfire smoke",
        "Deploy rooftop solar PV microgrid with 48h battery storage",
    ],
    "Emergency Response Center": [
        "Reinforce communications antenna towers against Category 3 winds",
        "Dual-feed municipal power routing with automatic transfer switch",
        "Perimeter automated flood barriers and high-capacity sumps",
    ],
    "Power Substation": [
        "Substation perimeter water-deflection flood walls and seal penetrations",
        "Transformer cooling spray enhancements for extreme heatwaves (>45°C)",
        "Vegetation management buffer (30m clear zone) against wildfires",
    ],
    "Water Treatment Plant": [
        "Intake pump elevation and automated silt backwash mechanisms",
        "Overflow retention ponds to absorb 1-in-50 year flash flood spikes",
        "Redundant chlorination and emergency chemical storage containment",
    ],
    "Bridge & Evacuation Route": [
        "Scour sensors on bridge piers to monitor riverbed erosion in real time",
        "Permeable asphalt surfacing and rapid-drainage storm spillways",
        "Dynamic high-wind automated signage and vehicle wind-deflection barriers",
    ],
    "Telecommunications Hub": [
        "Cabinet thermal heat-dissipation retrofits and solar shades",
        "Underground fiber optic cable hardening in high-risk flood paths",
        "Dry-pipe fire suppression system and fuel-cell auxiliary power",
    ],
    "School / Community Shelter": [
        "Cool roof coatings (high solar reflectance index > 0.82)",
        "Designate secondary emergency gym shelter with independent backup power",
        "Permeable bioswales and rain gardens for local stormwater infiltration",
    ],
    "Transit Station / Airport": [
        "Rapid-deploy flood gates for underground concourse portals",
        "High-capacity dewatering pumps with secondary diesel generators",
        "Reflective tensile canopy structures over passenger waiting areas",
    ],
    "Commercial Facility": [
        "Exterior building envelope air-sealing and sun-louvers",
        "Basement perimeter sumps and water sensor telemetry",
        "Green roof installation for stormwater retention and insulation",
    ],
}


class InfrastructureService:
    """Service for climate-resilient infrastructure planning and asset management."""

    def __init__(self, open_meteo_client: Optional[OpenMeteoClient] = None):
        self.open_meteo = open_meteo_client or OpenMeteoClient()

    def fetch_elevation_meters(self, lat: float, lon: float) -> float:
        """Fetches topological elevation in meters from Open-Meteo elevation API with fallback."""
        url = f"https://api.open-meteo.com/v1/elevation?latitude={lat}&longitude={lon}"
        try:
            resp = requests.get(url, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                elev = data.get("elevation", [25.0])
                if isinstance(elev, list) and len(elev) > 0:
                    return float(elev[0])
                elif isinstance(elev, (int, float)):
                    return float(elev)
        except Exception as e:
            logger.warning(f"Failed to fetch elevation for ({lat}, {lon}): {e}")
        # Default fallback reasonable elevation
        return 35.0

    def evaluate_asset_vulnerability(
        self,
        asset_type: str,
        lat: float,
        lon: float,
        elevation_m: float,
    ) -> Dict[str, Any]:
        """
        Computes exposure across flood, heat, and fire hazards based on elevation and forecast,
        and generates prioritized resilience interventions.
        """
        # Fetch weather forecast for hazard context
        forecast = self.open_meteo.fetch_weather_forecast(lat, lon)
        daily = forecast.get("daily", {})

        precip_sum = sum(daily.get("precipitation_sum", [5.0] * 7))
        max_temp = max(daily.get("temperature_2m_max", [26.0] * 7))
        wind_max = max(daily.get("wind_speed_10m_max", [18.0] * 7))

        # 1. Flood Exposure (0-100): Lower elevation + higher rainfall = higher flood risk
        # Elevation below 15m is especially vulnerable to storm surge / riverine flooding
        base_flood = max(10.0, 85.0 - min(80.0, elevation_m * 1.5))
        rain_factor = min(30.0, (precip_sum / 20.0) * 15.0)
        flood_exposure = round(min(100.0, max(5.0, base_flood + rain_factor)), 1)

        # 2. Heat Exposure (0-100): High peak max temp + urban density
        heat_exposure = round(min(100.0, max(10.0, (max_temp - 20.0) * 4.5)), 1)

        # 3. Fire / Storm Exposure (0-100): High wind + dry conditions
        dry_factor = 25.0 if precip_sum < 5.0 else 10.0
        wind_factor = min(35.0, (wind_max / 15.0) * 12.0)
        fire_exposure = round(min(100.0, max(5.0, dry_factor + wind_factor)), 1)

        # Criticality weight
        crit_info = ASSET_CRITICALITY.get(asset_type, {"tier": 3, "weight": 1.0, "icon": "🏢"})
        weight = crit_info["weight"]

        # Composite Vulnerability Score (0-100)
        raw_composite = (0.45 * flood_exposure + 0.35 * heat_exposure + 0.20 * fire_exposure) * (weight / 1.1)
        composite_vuln = round(min(100.0, max(5.0, raw_composite)), 1)

        # Priority Rank: 1 (Urgent) to 4 (Routine)
        if composite_vuln >= 75.0:
            priority_rank = 1
            risk_tier = "Critical Vulnerability"
            badge_color = "#ef4444"
        elif composite_vuln >= 50.0:
            priority_rank = 2
            risk_tier = "High Vulnerability"
            badge_color = "#f97316"
        elif composite_vuln >= 30.0:
            priority_rank = 3
            risk_tier = "Moderate Vulnerability"
            badge_color = "#f59e0b"
        else:
            priority_rank = 4
            risk_tier = "Low Vulnerability"
            badge_color = "#10b981"

        recommended_measures = RESILIENCE_CATALOG.get(asset_type, RESILIENCE_CATALOG["Commercial Facility"])

        return {
            "flood_exposure_score": flood_exposure,
            "heat_exposure_score": heat_exposure,
            "fire_exposure_score": fire_exposure,
            "vulnerability_score": composite_vuln,
            "priority_rank": priority_rank,
            "risk_tier": risk_tier,
            "badge_color": badge_color,
            "resilience_measures": recommended_measures,
        }

    def add_asset(
        self,
        name: str,
        asset_type: str,
        latitude: float,
        longitude: float,
        user_id: str = "user_default",
        elevation_m: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Evaluates and persists a new infrastructure asset record to database."""
        if elevation_m is None:
            elevation_m = self.fetch_elevation_meters(latitude, longitude)

        vuln_data = self.evaluate_asset_vulnerability(asset_type, latitude, longitude, elevation_m)

        measures_json = json.dumps(vuln_data["resilience_measures"])

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO infrastructure_assets (
                    user_id, name, asset_type, latitude, longitude, elevation_m,
                    flood_exposure_score, heat_exposure_score, fire_exposure_score,
                    vulnerability_score, priority_rank, resilience_measures
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    user_id,
                    name,
                    asset_type,
                    latitude,
                    longitude,
                    elevation_m,
                    vuln_data["flood_exposure_score"],
                    vuln_data["heat_exposure_score"],
                    vuln_data["fire_exposure_score"],
                    vuln_data["vulnerability_score"],
                    vuln_data["priority_rank"],
                    measures_json,
                ),
            )
            asset_id = cursor.lastrowid

        return {
            "id": asset_id,
            "user_id": user_id,
            "name": name,
            "asset_type": asset_type,
            "latitude": latitude,
            "longitude": longitude,
            "elevation_m": elevation_m,
            **vuln_data,
        }

    def get_assets(self, user_id: str = "user_default") -> List[Dict[str, Any]]:
        """Retrieves all infrastructure assets for the specified user ordered by vulnerability."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, user_id, name, asset_type, latitude, longitude, elevation_m,
                       flood_exposure_score, heat_exposure_score, fire_exposure_score,
                       vulnerability_score, priority_rank, resilience_measures, created_at
                FROM infrastructure_assets
                WHERE user_id = ?
                ORDER BY vulnerability_score DESC;
                """,
                (user_id,),
            )
            rows = cursor.fetchall()

        assets = []
        for r in rows:
            asset_type = r[3]
            crit_info = ASSET_CRITICALITY.get(asset_type, {"tier": 3, "weight": 1.0, "icon": "🏢"})
            measures = json.loads(r[12]) if r[12] else []
            v_score = r[10]
            if v_score >= 75.0:
                tier, color = "Critical", "#ef4444"
            elif v_score >= 50.0:
                tier, color = "High", "#f97316"
            elif v_score >= 30.0:
                tier, color = "Moderate", "#f59e0b"
            else:
                tier, color = "Low", "#10b981"

            assets.append({
                "id": r[0],
                "user_id": r[1],
                "name": r[2],
                "asset_type": asset_type,
                "latitude": r[4],
                "longitude": r[5],
                "elevation_m": r[6],
                "flood_exposure_score": r[7],
                "heat_exposure_score": r[8],
                "fire_exposure_score": r[9],
                "vulnerability_score": v_score,
                "priority_rank": r[11],
                "resilience_measures": measures,
                "created_at": r[13],
                "icon": crit_info["icon"],
                "risk_tier": tier,
                "badge_color": color,
            })
        return assets

    def delete_asset(self, asset_id: int) -> bool:
        """Deletes an asset record from database."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM infrastructure_assets WHERE id = ?;", (asset_id,))
                return cursor.rowcount > 0
        except Exception as e:
            logger.warning(f"Failed to delete asset {asset_id}: {e}")
            return False

    def seed_default_assets_if_empty(self, user_id: str = "user_default") -> None:
        """Seeds realistic demonstration infrastructure assets if database table is empty."""
        existing = self.get_assets(user_id)
        if existing:
            return

        demo_assets = [
            ("City General Hospital & Trauma Center", "Hospital", 28.6250, 77.2180, 212.0),
            ("North Metropolitan Water Treatment Facility", "Water Treatment Plant", 28.7120, 77.1850, 204.0),
            ("Central Grid Power Substation 220kV", "Power Substation", 28.5980, 77.2410, 215.0),
            ("Civic Disaster Emergency Operations Base", "Emergency Response Center", 28.6310, 77.2250, 216.0),
            ("Yamuna River Expressway Suspension Bridge", "Bridge & Evacuation Route", 28.6180, 77.2530, 201.0),
            ("Regional Fiber & 5G Telecommunications Node", "Telecommunications Hub", 28.5830, 77.2020, 225.0),
            ("St. Jude Community High School Shelter", "School / Community Shelter", 28.6470, 77.1990, 218.0),
        ]

        for name, a_type, lat, lon, elev in demo_assets:
            self.add_asset(
                name=name,
                asset_type=a_type,
                latitude=lat,
                longitude=lon,
                user_id=user_id,
                elevation_m=elev,
            )
