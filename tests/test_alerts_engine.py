"""
Unit tests for Shared Alert Engine, severity ordering, deduplication, and escalation.
"""

from pathlib import Path
import pytest
from unittest.mock import MagicMock

from climatrend.climate.alerts.engine import SharedAlertEngine
from climatrend.climate.alerts.models import AlertEvent, AlertSeverity
from climatrend.climate.alerts.delivery import AlertDeliveryManager
from climatrend.climate.db.database import get_db, init_db


def test_alert_severity_ordering():
    """Verifies 4-tier alert severity hierarchy."""
    assert AlertSeverity.ADVISORY < AlertSeverity.WATCH
    assert AlertSeverity.WATCH < AlertSeverity.WARNING
    assert AlertSeverity.WARNING < AlertSeverity.SEVERE
    assert AlertSeverity.SEVERE >= AlertSeverity.WARNING
    assert AlertSeverity.from_str("warning") == AlertSeverity.WARNING
    assert AlertSeverity.from_str("invalid") == AlertSeverity.ADVISORY


def test_shared_alert_engine_deduplication_and_escalation(temp_db_path: Path, monkeypatch):
    """
    Verifies that the shared engine:
    1. Dispatches a new alert
    2. Suppresses identical duplicate alerts
    3. Escalates when an updated event has higher severity
    """
    # Point DB_PATH in database module to our temp DB
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    mock_delivery = MagicMock(spec=AlertDeliveryManager)
    mock_delivery.dispatch.return_value = ["in_app", "telegram"]

    engine = SharedAlertEngine(delivery_manager=mock_delivery)

    event_id = "test_heatwave_20260928_london"

    # Step 1: Initial alert at 'Watch' severity
    event1 = AlertEvent(
        event_id=event_id,
        hazard_type="extreme_heat",
        severity=AlertSeverity.WATCH,
        title="Excessive Heat Watch",
        message="Forecast predicts temperature exceeding 95th percentile.",
        source="historical_climatology",
        region_id=1,
        region_name="London",
        forecast_value=32.5,
        normal_value=22.0,
    )

    res1 = engine.process_event(event1)
    assert res1["status"] == "dispatched"
    assert res1["severity"] == "Watch"

    # Verify written to database
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_log WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        assert row is not None
        assert row["severity"] == "Watch"
        assert row["status"] == "active"

    # Step 2: Identical alert received again -> Must be suppressed (deduplication)
    event2 = AlertEvent(
        event_id=event_id,
        hazard_type="extreme_heat",
        severity=AlertSeverity.WATCH,
        title="Excessive Heat Watch",
        message="Forecast predicts temperature exceeding 95th percentile.",
        source="historical_climatology",
        region_id=1,
    )
    res2 = engine.process_event(event2)
    assert res2["status"] == "suppressed"
    assert "Duplicate" in res2["reason"]

    # Step 3: Heat escalates to 'Severe' -> Must trigger escalation!
    event3 = AlertEvent(
        event_id=event_id,
        hazard_type="extreme_heat",
        severity=AlertSeverity.SEVERE,
        title="Catastrophic Heatwave Emergency",
        message="Persistence: 3+ consecutive days above 99th percentile.",
        source="historical_climatology",
        region_id=1,
        forecast_value=36.0,
    )
    res3 = engine.process_event(event3)
    assert res3["status"] == "escalated"
    assert res3["severity"] == "Severe"

    # Verify alert_log updated with escalation
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM alert_log WHERE event_id = ?", (event_id,))
        row = cursor.fetchone()
        assert row["severity"] == "Severe"
        assert row["status"] == "escalated"
        assert "ESCALATED" in row["title"]
