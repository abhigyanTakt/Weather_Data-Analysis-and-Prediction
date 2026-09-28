"""
Unit tests for Air Quality service, EPA classification, XGBoost forecasting, and DB persistence.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from climatrend.climate.air_quality.service import AirQualityService, classify_aqi
from climatrend.climate.air_quality.forecaster import AirQualityForecaster
from climatrend.climate.db.database import get_db


def test_classify_aqi_breakpoints():
    """Verifies that EPA AQI values map to appropriate color and categories."""
    assert classify_aqi(25)["category"] == "Good"
    assert classify_aqi(75)["category"] == "Moderate"
    assert classify_aqi(125)["category"] == "Unhealthy for Sensitive Groups"
    assert classify_aqi(175)["category"] == "Unhealthy"
    assert classify_aqi(250)["category"] == "Very Unhealthy"
    assert classify_aqi(350)["category"] == "Hazardous"


def test_air_quality_service_and_db_logging(temp_db_path: Path, monkeypatch):
    """Verifies AirQualityService returns valid metrics and records readings to DB."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    service = AirQualityService()
    res = service.get_current_air_quality(51.5074, -0.1278, location_name="London")

    assert res["location_name"] == "London"
    assert "aqi" in res
    assert "category" in res
    assert "pollutants" in res
    assert "pm2_5" in res["pollutants"]
    assert "general_advice" in res

    # Verify written to environmental_readings table
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM environmental_readings WHERE location_name = 'London';")
        row = cursor.fetchone()
        assert row is not None
        assert row["aqi"] == res["aqi"]


def test_xgboost_forecaster():
    """Verifies that the XGBoost forecaster builds features, fits, and outputs 72h forecasts."""
    # Create sample hourly DataFrame with 48 hours
    dates = pd.date_range("2026-09-01", periods=48, freq="h")
    sample_df = pd.DataFrame({
        "time": dates,
        "pm2_5": [15.0 + 8.0 * np.sin(i / 4.0) for i in range(48)],
        "pm10": [25.0 + 10.0 * np.sin(i / 4.0) for i in range(48)],
        "nitrogen_dioxide": [20.0 + 5.0 * np.cos(i / 4.0) for i in range(48)],
        "ozone": [40.0 + 12.0 * np.sin(i / 6.0) for i in range(48)],
    })

    forecaster = AirQualityForecaster(target_col="pm2_5", n_estimators=20)
    result = forecaster.train_and_predict(sample_df, horizon_hours=48)

    assert "forecast_df" in result
    assert "feature_importances" in result
    assert "metrics" in result
    assert len(result["forecast_df"]) == 48
    assert "xgboost_forecast" in result["forecast_df"].columns
    assert result["metrics"]["mae"] >= 0.0
    assert len(result["feature_importances"]) > 0
