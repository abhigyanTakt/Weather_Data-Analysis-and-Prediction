"""
Climate Risk Assessment Service.
Computes multi-hazard risk scores (Hazard x Exposure x Vulnerability)
for heatwaves, extreme rainfall/flooding, severe storms/gales, and drought.
Classifies into Low / Medium / High / Severe with detailed explanations.
"""

from datetime import datetime
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)


def classify_risk_score(score: float) -> Tuple[str, str]:
    """Returns (Risk Level, Color Hex) for a 0-100 risk score."""
    if score >= 75.0:
        return "Severe", "#ef4444"
    elif score >= 50.0:
        return "High", "#f97316"
    elif score >= 25.0:
        return "Medium", "#f59e0b"
    return "Low", "#10b981"


class ClimateRiskService:
    """Service evaluating multi-hazard climate risk scores."""

    def __init__(self, open_meteo_client: Optional[OpenMeteoClient] = None):
        self.open_meteo = open_meteo_client or OpenMeteoClient()

    def evaluate_location_risk(
        self,
        lat: float,
        lon: float,
        location_name: str = "Target Area",
        region_id: Optional[int] = None,
        population_density: float = 1.0,  # Exposure multiplier (1.0 = normal, 1.5 = dense urban)
        infrastructure_resilience: float = 1.0,  # Vulnerability multiplier (0.8 = resilient, 1.2 = vulnerable)
    ) -> Dict[str, Any]:
        """
        Calculates multi-hazard risk across Heat, Flood, Storm, and Drought.
        Formula: Total Risk = Hazard x Exposure x Vulnerability (normalized to 0-100).
        """
        forecast = self.open_meteo.fetch_weather_forecast(lat, lon)
        daily = forecast.get("daily", {})

        tmax_list = daily.get("temperature_2m_max", [22.0] * 7)
        precip_list = daily.get("precipitation_sum", [0.0] * 7)
        wind_list = daily.get("wind_speed_10m_max", [15.0] * 7)

        # 1. Heatwave Hazard Score (0 - 10)
        max_t = max(tmax_list) if tmax_list else 22.0
        days_above_32 = sum(1 for t in tmax_list if t >= 32.0)
        heat_hazard = min(10.0, max(1.0, (max_t - 20.0) * 0.4 + days_above_32 * 0.8))

        # 2. Heavy Rain / Flood Hazard Score (0 - 10)
        tot_precip = sum(precip_list) if precip_list else 0.0
        max_daily_p = max(precip_list) if precip_list else 0.0
        flood_hazard = min(10.0, max(1.0, (tot_precip / 15.0) + (max_daily_p / 10.0)))

        # 3. Severe Storm / Wind Hazard Score (0 - 10)
        max_wind = max(wind_list) if wind_list else 15.0
        storm_hazard = min(10.0, max(1.0, (max_wind - 10.0) / 7.0))

        # 4. Drought Hazard Score (0 - 10)
        dry_days = sum(1 for p in precip_list if p < 0.5)
        drought_hazard = min(10.0, max(1.0, (dry_days / 7.0) * 8.0 if tot_precip < 5.0 else 2.0))

        hazards = {
            "extreme_heat": {
                "label": "Extreme Heatwave",
                "hazard_score": round(heat_hazard, 1),
                "exposure_score": round(population_density * 8.0, 1),
                "vulnerability_score": round(infrastructure_resilience * 8.0, 1),
                "metric_details": f"Forecast peak max {max_t:.1f}°C; {days_above_32} days >= 32°C.",
            },
            "heavy_rain_flood": {
                "label": "Heavy Rain & Flood",
                "hazard_score": round(flood_hazard, 1),
                "exposure_score": round(population_density * 7.5, 1),
                "vulnerability_score": round(infrastructure_resilience * 8.5, 1),
                "metric_details": f"7-day accumulated rain {tot_precip:.1f} mm; peak single day {max_daily_p:.1f} mm.",
            },
            "storm_wind": {
                "label": "Severe Storm & Gales",
                "hazard_score": round(storm_hazard, 1),
                "exposure_score": round(population_density * 7.0, 1),
                "vulnerability_score": round(infrastructure_resilience * 7.5, 1),
                "metric_details": f"Peak sustained wind gusts {max_wind:.1f} km/h.",
            },
            "drought": {
                "label": "Agricultural Drought",
                "hazard_score": round(drought_hazard, 1),
                "exposure_score": round(population_density * 6.5, 1),
                "vulnerability_score": round(infrastructure_resilience * 8.0, 1),
                "metric_details": f"{dry_days}/7 dry days with total precipitation {tot_precip:.1f} mm.",
            },
        }

        # Calculate composite scores
        total_risk_scores = {}
        for h_key, h_data in hazards.items():
            # Normalized Risk = (Hazard x Exposure x Vulnerability) / 10
            # Scale 0 to 100
            raw_risk = (h_data["hazard_score"] * h_data["exposure_score"] * h_data["vulnerability_score"]) / 10.0
            norm_risk = round(min(100.0, raw_risk), 1)
            level, color = classify_risk_score(norm_risk)
            h_data["total_risk"] = norm_risk
            h_data["risk_level"] = level
            h_data["color"] = color
            total_risk_scores[h_key] = norm_risk

            # Persist to database
            self._save_risk_record(
                region_id=region_id,
                hazard_type=h_key,
                h_score=h_data["hazard_score"],
                e_score=h_data["exposure_score"],
                v_score=h_data["vulnerability_score"],
                total=norm_risk,
                level=level,
                explanations=h_data["metric_details"],
            )

        overall_risk = round(float(np.mean(list(total_risk_scores.values()))), 1)
        overall_level, overall_color = classify_risk_score(overall_risk)

        return {
            "location_name": location_name,
            "latitude": lat,
            "longitude": lon,
            "overall_risk_score": overall_risk,
            "overall_risk_level": overall_level,
            "overall_color": overall_color,
            "hazards": hazards,
            "evaluation_date": datetime.utcnow().strftime("%Y-%m-%d"),
        }

    def _save_risk_record(
        self,
        region_id: Optional[int],
        hazard_type: str,
        h_score: float,
        e_score: float,
        v_score: float,
        total: float,
        level: str,
        explanations: str,
    ) -> None:
        """Persists risk assessment to climate_risk_scores table."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO climate_risk_scores (
                        region_id, assessment_date, hazard_type, hazard_score,
                        exposure_score, vulnerability_score, total_risk, risk_level, explanations_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        region_id,
                        datetime.utcnow().strftime("%Y-%m-%d"),
                        hazard_type,
                        h_score,
                        e_score,
                        v_score,
                        total,
                        level,
                        json.dumps({"details": explanations}),
                    ),
                )
        except Exception as e:
            logger.warning(f"Failed to record climate risk: {e}")

    def get_recent_risk_assessments(
        self, region_id: Optional[int] = None, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Retrieves recent climate risk score records from database."""
        try:
            with get_db() as conn:
                cursor = conn.cursor()
                if region_id:
                    cursor.execute(
                        """
                        SELECT id, assessment_date, hazard_type, hazard_score, exposure_score,
                               vulnerability_score, total_risk, risk_level, explanations_json
                        FROM climate_risk_scores
                        WHERE region_id = ?
                        ORDER BY id DESC LIMIT ?;
                        """,
                        (region_id, limit),
                    )
                else:
                    cursor.execute(
                        """
                        SELECT id, assessment_date, hazard_type, hazard_score, exposure_score,
                               vulnerability_score, total_risk, risk_level, explanations_json
                        FROM climate_risk_scores
                        ORDER BY id DESC LIMIT ?;
                        """,
                        (limit,),
                    )
                rows = cursor.fetchall()
                results = []
                for row in rows:
                    results.append({
                        "id": row[0],
                        "assessment_date": row[1],
                        "hazard_type": row[2],
                        "hazard_score": row[3],
                        "exposure_score": row[4],
                        "vulnerability_score": row[5],
                        "total_risk": row[6],
                        "risk_level": row[7],
                        "explanations": json.loads(row[8] or "{}"),
                    })
                return results
        except Exception as e:
            logger.warning(f"Failed to fetch risk records: {e}")
            return []

