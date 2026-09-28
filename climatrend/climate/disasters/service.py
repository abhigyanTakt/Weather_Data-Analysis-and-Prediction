"""
Disaster Early-Warning Service.
Ingests multi-source disaster indicators (USGS earthquakes, NASA FIRMS wildfires,
GDACS events, Open-Meteo flood indicators), evaluates threshold rules,
and feeds into the Shared Alert Engine for deduplication, multi-channel dispatch,
and persistent logging in alert_log.
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from climatrend.climate.alerts.engine import SharedAlertEngine
from climatrend.climate.alerts.models import AlertEvent, AlertSeverity
from climatrend.climate.clients.disaster_client import DisasterClient, haversine_distance
from climatrend.climate.clients.open_meteo_client import OpenMeteoClient
from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)


class DisasterService:
    """Ingests disaster feeds, applies threshold rules, and routes into the Shared Alert Engine."""

    def __init__(
        self,
        disaster_client: Optional[DisasterClient] = None,
        open_meteo_client: Optional[OpenMeteoClient] = None,
        alert_engine: Optional[SharedAlertEngine] = None,
    ):
        self.disaster_client = disaster_client or DisasterClient()
        self.open_meteo = open_meteo_client or OpenMeteoClient()
        self.alert_engine = alert_engine or SharedAlertEngine()

    def evaluate_earthquake_severity(self, magnitude: float, distance_km: float) -> Optional[AlertSeverity]:
        """Maps earthquake magnitude and proximity to standard alert severity."""
        if distance_km <= 100.0:
            if magnitude >= 7.0:
                return AlertSeverity.SEVERE
            elif magnitude >= 6.0:
                return AlertSeverity.WARNING
            elif magnitude >= 5.0:
                return AlertSeverity.WATCH
            elif magnitude >= 4.0:
                return AlertSeverity.ADVISORY
        elif distance_km <= 300.0:
            if magnitude >= 7.5:
                return AlertSeverity.SEVERE
            elif magnitude >= 6.5:
                return AlertSeverity.WARNING
            elif magnitude >= 5.5:
                return AlertSeverity.WATCH
        elif distance_km <= 600.0:
            if magnitude >= 7.5:
                return AlertSeverity.WARNING
            elif magnitude >= 6.8:
                return AlertSeverity.WATCH
        return None

    def evaluate_wildfire_severity(self, distance_km: float, brightness: float) -> Optional[AlertSeverity]:
        """Maps active fire proximity and thermal radiance to severity."""
        if distance_km <= 15.0:
            return AlertSeverity.SEVERE
        elif distance_km <= 40.0:
            return AlertSeverity.WARNING
        elif distance_km <= 80.0:
            return AlertSeverity.WATCH
        elif distance_km <= 150.0 and brightness > 330.0:
            return AlertSeverity.ADVISORY
        return None

    def evaluate_flood_severity(self, current_discharge: float, median_discharge: float) -> Optional[AlertSeverity]:
        """Calculates discharge anomaly ratio for riverine flooding."""
        if median_discharge <= 0.1:
            ratio = current_discharge / 1.0
        else:
            ratio = current_discharge / median_discharge

        if ratio >= 4.0:
            return AlertSeverity.SEVERE
        elif ratio >= 2.5:
            return AlertSeverity.WARNING
        elif ratio >= 1.8:
            return AlertSeverity.WATCH
        elif ratio >= 1.4:
            return AlertSeverity.ADVISORY
        return None

    def scan_location_hazards(
        self,
        lat: float,
        lon: float,
        location_name: str = "Monitored Area",
        region_id: Optional[int] = None,
        radius_km: float = 300.0,
    ) -> List[Dict[str, Any]]:
        """
        Scans all hazard sources for a specific location, generates AlertEvent objects,
        and submits them to the Shared Alert Engine.
        """
        generated_alerts: List[Dict[str, Any]] = []

        # 1. Check USGS Earthquakes
        try:
            quakes = self.disaster_client.fetch_recent_earthquakes(
                center_lat=lat, center_lon=lon, max_radius_km=radius_km, min_magnitude=4.0
            )
            for q in quakes:
                mag = q["magnitude"]
                dist = q["distance_km"]
                severity = self.evaluate_earthquake_severity(mag, dist)
                if severity:
                    event = AlertEvent(
                        event_id=f"quake_{q['event_id']}_{round(lat, 2)}_{round(lon, 2)}",
                        hazard_type="earthquake",
                        severity=severity,
                        title=f"M{mag:.1f} Earthquake Detected {dist:.0f}km from {location_name}",
                        message=f"A magnitude {mag:.1f} seismic event occurred near {q['place']} at depth {q['depth_km']}km ({dist:.0f}km away).",
                        historical_context=f"Significant seismic event detected by USGS network within {radius_km:.0f}km monitoring zone.",
                        region_id=region_id,
                        region_name=location_name,
                        latitude=q["latitude"],
                        longitude=q["longitude"],
                        forecast_value=mag,
                        normal_value=0.0,
                        source="usgs",
                        time_window="Occurred within past 24 hours",
                        recommended_action="Drop, cover, and hold on. Inspect structures for damage. Stay clear of compromised buildings.",
                        expires_at=datetime.utcnow() + timedelta(hours=24),
                    )
                    res = self.alert_engine.process_event(event)
                    generated_alerts.append({"type": "earthquake", "details": q, "alert_result": res})
        except Exception as e:
            logger.error(f"Error processing earthquake alerts: {e}")

        # 2. Check NASA FIRMS Wildfires
        try:
            fires = self.disaster_client.fetch_active_wildfires(
                center_lat=lat, center_lon=lon, radius_km=min(radius_km, 150.0)
            )
            if fires:
                # Group fires and pick closest / highest intensity
                closest_fire = min(fires, key=lambda f: f["distance_km"])
                f_dist = closest_fire["distance_km"]
                f_bright = closest_fire.get("brightness", 310.0)
                severity = self.evaluate_wildfire_severity(f_dist, f_bright)
                if severity:
                    event = AlertEvent(
                        event_id=f"wildfire_{round(lat, 2)}_{round(lon, 2)}_{closest_fire.get('acquisition_date', '')}",
                        hazard_type="wildfire",
                        severity=severity,
                        title=f"Active Wildfire Cluster Detected {f_dist:.0f}km from {location_name}",
                        message=f"NASA FIRMS thermal sensors detected {len(fires)} active thermal anomaly hotspots. Closest hotspot is {f_dist:.0f}km away (Brightness: {f_bright:.0f}K).",
                        historical_context="Thermal satellite imaging detected high-confidence active fire signature.",
                        region_id=region_id,
                        region_name=location_name,
                        latitude=closest_fire["latitude"],
                        longitude=closest_fire["longitude"],
                        forecast_value=float(len(fires)),
                        source="nasa_firms",
                        time_window="Active detection (Past 24-48 hours)",
                        recommended_action="Monitor local emergency evacuation notices. Prepare go-bags and seal indoor air against smoke.",
                        expires_at=datetime.utcnow() + timedelta(hours=18),
                    )
                    res = self.alert_engine.process_event(event)
                    generated_alerts.append({"type": "wildfire", "count": len(fires), "alert_result": res})
        except Exception as e:
            logger.error(f"Error processing wildfire alerts: {e}")

        # 3. Check Open-Meteo Flood Indicators
        try:
            flood_data = self.open_meteo.fetch_flood_indicators(lat, lon)
            daily = flood_data.get("daily", {})
            discharges = daily.get("river_discharge", [])
            if discharges:
                curr_q = discharges[0]
                median_q = daily.get("river_discharge_median", [curr_q])[0] if daily.get("river_discharge_median") else curr_q
                severity = self.evaluate_flood_severity(curr_q, median_q)
                if severity and severity >= AlertSeverity.WATCH:
                    event = AlertEvent(
                        event_id=f"flood_{round(lat, 2)}_{round(lon, 2)}_{datetime.utcnow().strftime('%Y%m%d')}",
                        hazard_type="flood",
                        severity=severity,
                        title=f"Elevated River Discharge & Flood Risk in {location_name}",
                        message=f"River discharge forecast indicates flow of {curr_q:.1f} m³/s vs baseline {median_q:.1f} m³/s (Ratio: {curr_q/max(median_q, 0.1):.1f}x).",
                        historical_context="Discharge anomaly exceeds seasonal median benchmark.",
                        region_id=region_id,
                        region_name=location_name,
                        latitude=lat,
                        longitude=lon,
                        forecast_value=curr_q,
                        normal_value=median_q,
                        source="open_meteo_flood",
                        time_window="Next 48-96 hours",
                        recommended_action="Avoid low-lying riverbanks. Relocate valuable equipment above flood levels. Monitor local stream gauges.",
                        expires_at=datetime.utcnow() + timedelta(hours=48),
                    )
                    res = self.alert_engine.process_event(event)
                    generated_alerts.append({"type": "flood", "discharge": curr_q, "alert_result": res})
        except Exception as e:
            logger.error(f"Error processing flood alerts: {e}")

        return generated_alerts

    def check_all_monitored_regions(self) -> List[Dict[str, Any]]:
        """Scans all registered regions in the database for disaster events."""
        all_results = []
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, latitude, longitude FROM regions;")
            regions = cursor.fetchall()

        for r in regions:
            alerts = self.scan_location_hazards(
                lat=r["latitude"],
                lon=r["longitude"],
                location_name=r["name"],
                region_id=r["id"],
            )
            all_results.extend(alerts)

        return all_results
