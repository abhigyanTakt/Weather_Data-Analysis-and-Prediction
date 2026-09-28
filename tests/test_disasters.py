"""
Unit tests for Disaster Early-Warning Service, threshold rules, and shared engine integration.
"""

from pathlib import Path
from unittest.mock import MagicMock
import pytest

from climatrend.climate.alerts.engine import SharedAlertEngine
from climatrend.climate.alerts.models import AlertSeverity
from climatrend.climate.disasters.service import DisasterService
from climatrend.climate.db.database import get_db


def test_earthquake_severity_rules():
    """Verifies distance-magnitude scaling for earthquakes."""
    service = DisasterService()

    # Close proximity (<100km)
    assert service.evaluate_earthquake_severity(7.2, 50.0) == AlertSeverity.SEVERE
    assert service.evaluate_earthquake_severity(6.1, 50.0) == AlertSeverity.WARNING
    assert service.evaluate_earthquake_severity(5.1, 50.0) == AlertSeverity.WATCH
    assert service.evaluate_earthquake_severity(4.1, 50.0) == AlertSeverity.ADVISORY

    # Medium distance (200km)
    assert service.evaluate_earthquake_severity(7.6, 200.0) == AlertSeverity.SEVERE
    assert service.evaluate_earthquake_severity(6.6, 200.0) == AlertSeverity.WARNING
    assert service.evaluate_earthquake_severity(4.5, 200.0) is None  # Too far for M4.5


def test_wildfire_severity_rules():
    """Verifies proximity-based wildfire alert thresholds."""
    service = DisasterService()
    assert service.evaluate_wildfire_severity(10.0, 320.0) == AlertSeverity.SEVERE
    assert service.evaluate_wildfire_severity(30.0, 320.0) == AlertSeverity.WARNING
    assert service.evaluate_wildfire_severity(60.0, 320.0) == AlertSeverity.WATCH
    assert service.evaluate_wildfire_severity(200.0, 320.0) is None


def test_flood_severity_rules():
    """Verifies river discharge anomaly ratios."""
    service = DisasterService()
    assert service.evaluate_flood_severity(50.0, 10.0) == AlertSeverity.SEVERE  # 5x ratio
    assert service.evaluate_flood_severity(28.0, 10.0) == AlertSeverity.WARNING  # 2.8x ratio
    assert service.evaluate_flood_severity(19.0, 10.0) == AlertSeverity.WATCH    # 1.9x ratio
    assert service.evaluate_flood_severity(12.0, 10.0) is None


def test_disaster_service_scan_and_alert_logging(temp_db_path: Path, monkeypatch):
    """
    Verifies that scanning hazards generates AlertEvents, routes them into
    the SharedAlertEngine, and persists deduplicated records into alert_log.
    """
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    service = DisasterService()

    # Mock disaster client returning a M6.2 earthquake 40km away
    mock_quakes = [
        {
            "event_id": "usgs_test_2026",
            "magnitude": 6.2,
            "depth_km": 10.0,
            "latitude": 51.6,
            "longitude": -0.2,
            "distance_km": 40.0,
            "place": "40km N of London",
        }
    ]
    monkeypatch.setattr(service.disaster_client, "fetch_recent_earthquakes", lambda **kwargs: mock_quakes)
    monkeypatch.setattr(service.disaster_client, "fetch_active_wildfires", lambda **kwargs: [])

    # Scan 1: Should dispatch Warning alert
    alerts = service.scan_location_hazards(51.5, -0.1, location_name="London", region_id=1)
    assert len(alerts) >= 1
    assert alerts[0]["alert_result"]["status"] == "dispatched"
    assert alerts[0]["alert_result"]["severity"] == "Warning"

    # Verify stored in shared alert_log
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_log WHERE hazard_type = 'earthquake';")
        rows = cursor.fetchall()
        assert len(rows) >= 1
        assert rows[0]["severity"] == "Warning"

    # Scan 2: Identical earthquake -> Must be suppressed (deduplication)
    alerts2 = service.scan_location_hazards(51.5, -0.1, location_name="London", region_id=1)
    assert len(alerts2) >= 1
    assert alerts2[0]["alert_result"]["status"] == "suppressed"
