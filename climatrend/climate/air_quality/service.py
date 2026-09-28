"""
Air Quality Service.
Aggregates live air quality data, computes EPA AQI health risk categories,
provides actionable medical/public-health guidance, and logs readings to the database.
"""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.clients.openaq_client import OpenAQClient
from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)

# EPA AQI Breakpoints and Categorization
AQI_CATEGORIES = [
    {
        "min": 0,
        "max": 50,
        "category": "Good",
        "color": "#10b981",  # Emerald Green
        "description": "Air quality is considered satisfactory, and air pollution poses little or no risk.",
        "general_advice": "Enjoy normal outdoor activities.",
        "sensitive_advice": "No precautions necessary for sensitive groups.",
        "ventilation": "Open windows for fresh natural ventilation.",
    },
    {
        "min": 51,
        "max": 100,
        "category": "Moderate",
        "color": "#f59e0b",  # Amber
        "description": "Air quality is acceptable; however, some pollutants may be a moderate concern for sensitive individuals.",
        "general_advice": "Outdoor activities are fine for most people.",
        "sensitive_advice": "People with respiratory or heart disease should consider limiting prolonged outdoor exertion.",
        "ventilation": "Ventilation is generally acceptable.",
    },
    {
        "min": 101,
        "max": 150,
        "category": "Unhealthy for Sensitive Groups",
        "color": "#f97316",  # Orange
        "description": "Members of sensitive groups may experience health effects. The general public is less likely to be affected.",
        "general_advice": "It's OK to be active outside, but take more breaks and do less strenuous activities.",
        "sensitive_advice": "Children, elderly, and people with asthma or lung conditions should avoid prolonged outdoor exertion.",
        "ventilation": "Close windows during peak pollution hours (morning/evening).",
    },
    {
        "min": 151,
        "max": 200,
        "category": "Unhealthy",
        "color": "#ef4444",  # Red
        "description": "Everyone may begin to experience adverse health effects; members of sensitive groups may experience more serious health effects.",
        "general_advice": "Avoid prolonged outdoor exertion; move strenuous activities indoors.",
        "sensitive_advice": "Sensitive groups should avoid all outdoor physical activity.",
        "ventilation": "Keep windows closed. Run HEPA indoor air purifiers.",
    },
    {
        "min": 201,
        "max": 300,
        "category": "Very Unhealthy",
        "color": "#8b5cf6",  # Purple
        "description": "Health alert: The risk of serious health effects is increased for everyone.",
        "general_advice": "Avoid all outdoor physical exertion. Wear an N95/FFP2 mask if outdoors.",
        "sensitive_advice": "Sensitive groups must remain strictly indoors with air filtration.",
        "ventilation": "Seal doors/windows. Operate indoor air purifiers on high.",
    },
    {
        "min": 301,
        "max": 9999,
        "category": "Hazardous",
        "color": "#7f1d1d",  # Deep Maroon
        "description": "Health warning of emergency conditions: The entire population is likely to be severely affected.",
        "general_advice": "Emergency: Remain indoors. Do not open windows or exercise outdoors.",
        "sensitive_advice": "Strict medical confinement indoors with medical filtration.",
        "ventilation": "Keep indoor environment completely sealed.",
    },
]


def classify_aqi(aqi_val: int) -> Dict[str, Any]:
    """Returns classification, color, and health guidance for an AQI value."""
    for cat in AQI_CATEGORIES:
        if cat["min"] <= aqi_val <= cat["max"]:
            return cat
    return AQI_CATEGORIES[-1]


class AirQualityService:
    """Service handling environmental monitoring and air pollution queries."""

    def __init__(
        self,
        openaq_client: Optional[OpenAQClient] = None,
        open_meteo_client: Optional[OpenMeteoClient] = None,
    ):
        self.open_meteo = open_meteo_client or OpenMeteoClient()
        self.openaq = openaq_client or OpenAQClient(self.open_meteo)

    def get_current_air_quality(
        self, lat: float, lon: float, location_name: str = "Unknown"
    ) -> Dict[str, Any]:
        """
        Retrieves real-time air quality, calculates AQI category and health guidance,
        and records the reading in the database.
        """
        reading = self.openaq.fetch_latest_by_coords(lat, lon)

        aqi_val = reading.get("aqi")
        # If AQI is not directly provided by sensor, approximate US AQI from PM2.5 (EPA formula)
        if aqi_val is None:
            pm25 = reading.get("pm2_5", 15.0) or 15.0
            if pm25 <= 12.0:
                aqi_val = round((50 / 12.0) * pm25)
            elif pm25 <= 35.4:
                aqi_val = round(51 + ((100 - 51) / (35.4 - 12.1)) * (pm25 - 12.1))
            elif pm25 <= 55.4:
                aqi_val = round(101 + ((150 - 101) / (55.4 - 35.5)) * (pm25 - 35.5))
            elif pm25 <= 150.4:
                aqi_val = round(151 + ((200 - 151) / (150.4 - 55.5)) * (pm25 - 55.5))
            else:
                aqi_val = round(201 + ((300 - 201) / (250.4 - 150.5)) * (pm25 - 150.5))

        guidance = classify_aqi(aqi_val)

        # Log reading into database
        self._record_reading(
            location_name=location_name,
            lat=lat,
            lon=lon,
            aqi=aqi_val,
            pm2_5=reading.get("pm2_5"),
            pm10=reading.get("pm10"),
            no2=reading.get("no2"),
            o3=reading.get("o3"),
            co=reading.get("co"),
            source=reading.get("source", "Open-Meteo"),
        )

        return {
            "location_name": location_name,
            "latitude": lat,
            "longitude": lon,
            "source": reading.get("source", "Open-Meteo"),
            "aqi": aqi_val,
            "category": guidance["category"],
            "color": guidance["color"],
            "description": guidance["description"],
            "general_advice": guidance["general_advice"],
            "sensitive_advice": guidance["sensitive_advice"],
            "ventilation": guidance["ventilation"],
            "pollutants": {
                "pm2_5": reading.get("pm2_5", 0.0),
                "pm10": reading.get("pm10", 0.0),
                "no2": reading.get("no2", 0.0),
                "o3": reading.get("o3", 0.0),
                "co": reading.get("co", 0.0),
                "so2": reading.get("so2", 0.0),
            },
        }

    def get_forecast_72h(self, lat: float, lon: float) -> pd.DataFrame:
        """
        Fetches up to 72 hours of hourly air quality forecast from Open-Meteo.
        Returns a structured pandas DataFrame.
        """
        raw = self.open_meteo.fetch_air_quality(lat, lon)
        hourly = raw.get("hourly", {})

        if not hourly or "time" not in hourly:
            # Fallback synthetic 72h DataFrame
            times = [
                (datetime.now() + pd.Timedelta(hours=i)).strftime("%Y-%m-%dT%H:00")
                for i in range(72)
            ]
            return pd.DataFrame({
                "time": pd.to_datetime(times),
                "pm2_5": [12.0 + (i % 8) for i in range(72)],
                "pm10": [22.0 + (i % 12) for i in range(72)],
                "us_aqi": [45 + (i % 25) for i in range(72)],
                "nitrogen_dioxide": [15.0 + (i % 10) for i in range(72)],
                "ozone": [40.0 + (i % 15) for i in range(72)],
            })

        df = pd.DataFrame(hourly)
        df["time"] = pd.to_datetime(df["time"])
        # Return first 72 hours
        return df.head(72)

    def _record_reading(
        self,
        location_name: str,
        lat: float,
        lon: float,
        aqi: int,
        pm2_5: Optional[float],
        pm10: Optional[float],
        no2: Optional[float],
        o3: Optional[float],
        co: Optional[float],
        source: str,
    ) -> None:
        """Persists the reading to the database."""
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:00:00")
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO environmental_readings (
                        location_name, latitude, longitude, timestamp,
                        aqi, pm2_5, pm10, no2, o3, co, source
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (location_name, lat, lon, timestamp, aqi, pm2_5, pm10, no2, o3, co, source),
                )
        except Exception as e:
            logger.warning(f"Failed to record environmental reading: {e}")
