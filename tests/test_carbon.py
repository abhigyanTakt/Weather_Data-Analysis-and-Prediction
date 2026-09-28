"""
Unit tests for Carbon Footprint Tracking, emission conversions,
Isolation Forest anomaly detection, and SHAP explanation.
"""

from pathlib import Path
import pandas as pd
import pytest

from climatrend.climate.carbon.service import CarbonService
from climatrend.climate.carbon.anomaly_detector import CarbonAnomalyDetector
from climatrend.climate.carbon.explainer import CarbonSHAPExplainer
from climatrend.climate.db.database import get_db


def test_carbon_service_logging_and_aggregations(temp_db_path: Path, monkeypatch):
    """Verifies that carbon activities are logged with accurate CO2e conversion and aggregated."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    service = CarbonService()

    # Log 1: Car trip (20 km petrol = 20 * 0.170 = 3.4 kg)
    r1 = service.log_activity(
        user_id="user_test",
        activity_date="2026-09-01",
        category="travel",
        subcategory="car_petrol",
        value=20.0,
    )
    assert r1["co2e_kg"] == 3.4

    # Log 2: Electricity (100 kWh grid average = 100 * 0.436 = 43.6 kg)
    r2 = service.log_activity(
        user_id="user_test",
        activity_date="2026-09-02",
        category="electricity",
        subcategory="grid_average",
        value=100.0,
    )
    assert r2["co2e_kg"] == 43.6

    # Log 3: Food (2 beef meals = 2 * 6.61 = 13.22 kg)
    r3 = service.log_activity(
        user_id="user_test",
        activity_date="2026-09-03",
        category="food",
        subcategory="beef_meal",
        value=2.0,
    )
    assert r3["co2e_kg"] == 13.22

    # Query metrics
    metrics = service.get_aggregated_metrics(user_id="user_test")
    assert metrics["total_co2e_kg"] == pytest.approx(60.22, rel=1e-2)
    assert "travel" in metrics["category_breakdown"]
    assert "electricity" in metrics["category_breakdown"]
    assert "food" in metrics["category_breakdown"]


def test_carbon_anomaly_detection_and_shap(temp_db_path: Path, monkeypatch):
    """Verifies that Isolation Forest flags an extreme emission outlier and SHAP explains it."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    service = CarbonService()

    # Create 20 baseline small daily activities
    for i in range(1, 21):
        service.log_activity(
            user_id="user_anomaly_test",
            activity_date=f"2026-08-{i:02d}",
            category="travel",
            subcategory="bus",
            value=10.0,  # ~0.89 kg CO2e
        )

    # Insert an extreme outlier (long-haul business flight 6000 km = ~1524 kg CO2e)
    service.log_activity(
        user_id="user_anomaly_test",
        activity_date="2026-08-25",
        category="travel",
        subcategory="flight_business",
        value=6000.0,
    )

    df = service.get_user_activities(user_id="user_anomaly_test")
    detector = CarbonAnomalyDetector(contamination=0.10)
    df_flagged = detector.fit_and_detect(df, update_db=True)

    anomalies = df_flagged[df_flagged["is_anomaly"] == 1]
    assert len(anomalies) >= 1

    # Verify outlier row is the long-haul flight
    outlier = anomalies.iloc[0]
    assert outlier["subcategory"] == "flight_business"
    assert outlier["co2e_kg"] > 1000.0

    # Test SHAP explainer on the outlier
    explainer = CarbonSHAPExplainer()
    explainer.fit_surrogate(df_flagged, detector.feature_cols)
    explanation = explainer.explain_activity(outlier, detector.feature_cols)

    assert "shap_values" in explanation
    assert "summary" in explanation
    assert len(explanation["shap_values"]) > 0
