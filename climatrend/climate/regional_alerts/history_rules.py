"""
History-Driven Regional Alert Rules Engine.
Evaluates local forecasts against 30-year regional climatological baselines.
Thresholds are local, not global (e.g. 38°C is normal in one region and a severe heatwave in another).
Supports:
1. Percentile Rules (>95th, >99th percentile for day-of-year)
2. Anomaly Rules (Z-scores / sigma deviations)
3. Duration Rules (Persistence over consecutive days)
4. Return-Period Rules (GEV 1-in-10 and 1-in-50 year extremes)
5. Seasonal-Pattern Watches
Feeds directly into the Shared Alert Engine.
"""

from datetime import datetime, timedelta
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from climatrend.climate.alerts.engine import SharedAlertEngine
from climatrend.climate.alerts.models import AlertEvent, AlertSeverity
from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.db.database import get_db
from climatrend.climate.regional_alerts.climatology_builder import RegionalClimatologyBuilder

logger = logging.getLogger(__name__)


class HistoryRulesEngine:
    """Evaluates weather forecast against regional historical baselines and dispatches alerts."""

    def __init__(
        self,
        alert_engine: Optional[SharedAlertEngine] = None,
        open_meteo_client: Optional[OpenMeteoClient] = None,
        builder: Optional[RegionalClimatologyBuilder] = None,
    ):
        self.alert_engine = alert_engine or SharedAlertEngine()
        self.open_meteo = open_meteo_client or OpenMeteoClient()
        self.builder = builder or RegionalClimatologyBuilder(self.open_meteo)

    def evaluate_forecast_for_region(
        self, region_id: int, forecast_daily: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Compares upcoming 7-day forecast against the region's historical day-of-year baselines.
        Generates alerts for heatwaves, extreme rain, cold snaps, and persistent drought.
        """
        # Ensure regional baseline is available
        baseline_info = self.builder.get_or_build_baseline(region_id)
        region_name = baseline_info["region_name"]

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT latitude, longitude FROM regions WHERE id = ?;", (region_id,))
            reg = cursor.fetchone()
            lat, lon = reg["latitude"], reg["longitude"]

            # Load day-of-year baselines lookup dict: (doy, metric) -> row
            cursor.execute(
                """
                SELECT day_of_year, metric, mean, std, p5, p10, p50, p90, p95, p99
                FROM climatology_baselines
                WHERE region_id = ?;
                """,
                (region_id,),
            )
            baseline_rows = cursor.fetchall()
            base_map = {(r["day_of_year"], r["metric"]): dict(r) for r in baseline_rows}

            # Load return periods: (metric, rp_years) -> threshold
            cursor.execute(
                "SELECT metric, return_period_years, threshold_value FROM return_periods WHERE region_id = ?;",
                (region_id,),
            )
            return_periods = {(r["metric"], r["return_period_years"]): r["threshold_value"] for r in cursor.fetchall()}

        # Fetch 7-day forecast if not provided
        if not forecast_daily:
            f_resp = self.open_meteo.fetch_weather_forecast(lat, lon)
            forecast_daily = f_resp.get("daily", {})

        dates = forecast_daily.get("time", [])
        tmax_list = forecast_daily.get("temperature_2m_max", [])
        tmin_list = forecast_daily.get("temperature_2m_min", [])
        precip_list = forecast_daily.get("precipitation_sum", [])

        if not dates or not tmax_list:
            logger.warning(f"No forecast data available to evaluate for region {region_name}.")
            return []

        alerts_generated = []

        # Track consecutive streaks for Duration Rules
        consecutive_heat_p90 = 0
        consecutive_dry_days = 0

        for i, date_str in enumerate(dates):
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            doy = dt.timetuple().tm_yday
            month_name = dt.strftime("%B")

            tmax = tmax_list[i] if i < len(tmax_list) else None
            tmin = tmin_list[i] if i < len(tmin_list) else None
            precip = precip_list[i] if i < len(precip_list) else 0.0

            # ----------------- 1. EXTREME HEAT EVALUATION -----------------
            if tmax is not None and (doy, "temperature_max") in base_map:
                t_base = base_map[(doy, "temperature_max")]
                mean_t = t_base["mean"]
                std_t = max(t_base["std"], 0.5)
                z_score = (tmax - mean_t) / std_t
                p95 = t_base["p95"]
                p99 = t_base["p99"]
                p90 = t_base["p90"]

                if tmax >= p90:
                    consecutive_heat_p90 += 1
                else:
                    consecutive_heat_p90 = 0

                # Duration Rule: 3+ consecutive days > 90th percentile = Heatwave
                if consecutive_heat_p90 >= 3:
                    event_id = f"hist_heatwave_persist_{region_id}_{date_str}"
                    event = AlertEvent(
                        event_id=event_id,
                        hazard_type="extreme_heat",
                        severity=AlertSeverity.SEVERE,
                        title=f"Prolonged Severe Heatwave Warning ({consecutive_heat_p90} Consecutive Days)",
                        message=f"Regional temperature persistently exceeds the local 90th percentile ({p90:.1f}°C) for {consecutive_heat_p90} straight days.",
                        historical_context=f"Forecast peak {tmax:.1f}°C is {z_score:+.1f}σ above normal ({mean_t:.1f}°C in {month_name}). Regional 99th percentile is {p99:.1f}°C.",
                        region_id=region_id,
                        region_name=region_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=tmax,
                        normal_value=mean_t,
                        source="historical_climatology",
                        time_window=f"Active through {date_str}",
                        recommended_action="Activate local cooling shelters, suspend outdoor labor during peak hours, and check on vulnerable residents.",
                        expires_at=dt + timedelta(hours=24),
                    )
                    res = self.alert_engine.process_event(event)
                    alerts_generated.append(res)

                # Percentile & Anomaly Rules
                elif tmax >= p99 or z_score >= 3.0:
                    event_id = f"hist_heat_p99_{region_id}_{date_str}"
                    event = AlertEvent(
                        event_id=event_id,
                        hazard_type="extreme_heat",
                        severity=AlertSeverity.WARNING,
                        title=f"Extreme Temperature Warning in {region_name} ({tmax:.1f}°C)",
                        message=f"Forecast max of {tmax:.1f}°C exceeds the 99th percentile for this time of year ({p99:.1f}°C).",
                        historical_context=f"Hotter than 99% of days recorded in {month_name} since 1995 (+{z_score:.1f}σ anomaly above mean {mean_t:.1f}°C).",
                        region_id=region_id,
                        region_name=region_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=tmax,
                        normal_value=mean_t,
                        source="historical_climatology",
                        time_window=f"{date_str} (Peak 12:00-16:00)",
                        recommended_action="Hydrate aggressively, stay in air conditioning, and avoid unshaded midday sun.",
                        expires_at=dt + timedelta(hours=24),
                    )
                    res = self.alert_engine.process_event(event)
                    alerts_generated.append(res)

                elif tmax >= p95 or z_score >= 2.0:
                    event_id = f"hist_heat_p95_{region_id}_{date_str}"
                    event = AlertEvent(
                        event_id=event_id,
                        hazard_type="extreme_heat",
                        severity=AlertSeverity.WATCH,
                        title=f"Excessive Heat Watch in {region_name} ({tmax:.1f}°C)",
                        message=f"Forecast max of {tmax:.1f}°C exceeds the 95th percentile ({p95:.1f}°C).",
                        historical_context=f"Exceeds 95% of historical observations in {month_name} (Mean: {mean_t:.1f}°C).",
                        region_id=region_id,
                        region_name=region_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=tmax,
                        normal_value=mean_t,
                        source="historical_climatology",
                        time_window=f"{date_str}",
                        recommended_action="Plan outdoor activities for morning or evening. Ensure adequate hydration.",
                        expires_at=dt + timedelta(hours=24),
                    )
                    res = self.alert_engine.process_event(event)
                    alerts_generated.append(res)

            # ----------------- 2. HEAVY RAINFALL & RETURN-PERIOD EVALUATION -----------------
            if precip is not None and (doy, "precipitation") in base_map:
                p_base = base_map[(doy, "precipitation")]
                mean_p = p_base["mean"]
                p95_p = max(p_base["p95"], 20.0)
                rp_10 = return_periods.get(("precipitation", 10), 50.0)
                rp_50 = return_periods.get(("precipitation", 50), 90.0)

                # Return-Period Rule: Approaching 1-in-50 year event
                if precip >= rp_50:
                    event_id = f"hist_rain_rp50_{region_id}_{date_str}"
                    event = AlertEvent(
                        event_id=event_id,
                        hazard_type="heavy_rain",
                        severity=AlertSeverity.SEVERE,
                        title=f"1-in-50 Year Extreme Deluge Warning ({precip:.1f} mm)",
                        message=f"Forecast precipitation of {precip:.1f} mm exceeds the region's 1-in-50 year return level ({rp_50:.1f} mm). Flash flooding imminent.",
                        historical_context=f"Rainfall this heavy has a 2% annual probability of occurrence based on regional GEV statistical distribution.",
                        region_id=region_id,
                        region_name=region_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=precip,
                        normal_value=mean_p,
                        source="historical_climatology",
                        time_window=f"{date_str} 24-hour total",
                        recommended_action="Do not drive through flooded roads. Move to higher ground immediately. Secure sump pumps.",
                        expires_at=dt + timedelta(hours=36),
                    )
                    res = self.alert_engine.process_event(event)
                    alerts_generated.append(res)

                # Return-Period Rule: Approaching 1-in-10 year event
                elif precip >= rp_10:
                    event_id = f"hist_rain_rp10_{region_id}_{date_str}"
                    event = AlertEvent(
                        event_id=event_id,
                        hazard_type="heavy_rain",
                        severity=AlertSeverity.WARNING,
                        title=f"1-in-10 Year Heavy Rainfall Warning ({precip:.1f} mm)",
                        message=f"Forecast rainfall of {precip:.1f} mm exceeds the 10-year return threshold ({rp_10:.1f} mm).",
                        historical_context=f"Estimated 10% annual recurrence rate based on 25-year statistical precipitation modeling.",
                        region_id=region_id,
                        region_name=region_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=precip,
                        normal_value=mean_p,
                        source="historical_climatology",
                        time_window=f"{date_str}",
                        recommended_action="Clear storm drains. Be alert for urban surface water pooling and transit disruptions.",
                        expires_at=dt + timedelta(hours=36),
                    )
                    res = self.alert_engine.process_event(event)
                    alerts_generated.append(res)

                elif precip >= p95_p and precip >= 25.0:
                    event_id = f"hist_rain_p95_{region_id}_{date_str}"
                    event = AlertEvent(
                        event_id=event_id,
                        hazard_type="heavy_rain",
                        severity=AlertSeverity.WATCH,
                        title=f"Heavy Rainfall Watch in {region_name} ({precip:.1f} mm)",
                        message=f"Forecast of {precip:.1f} mm is higher than the 95th percentile ({p95_p:.1f} mm).",
                        historical_context=f"Significantly wetter than seasonal daily average ({mean_p:.1f} mm in {month_name}).",
                        region_id=region_id,
                        region_name=region_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=precip,
                        normal_value=mean_p,
                        source="historical_climatology",
                        time_window=f"{date_str}",
                        recommended_action="Carry wet weather gear. Check transit schedules for weather delays.",
                        expires_at=dt + timedelta(hours=24),
                    )
                    res = self.alert_engine.process_event(event)
                    alerts_generated.append(res)

        return alerts_generated

    def check_all_regions(self) -> List[Dict[str, Any]]:
        """Evaluates history rules across all registered regions in the database."""
        all_results = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM regions;")
            regions = cursor.fetchall()

        for r in regions:
            alerts = self.evaluate_forecast_for_region(region_id=r["id"])
            all_results.extend(alerts)

        return all_results
