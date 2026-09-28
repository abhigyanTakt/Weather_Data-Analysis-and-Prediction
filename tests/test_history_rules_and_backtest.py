"""
Unit tests for history-driven rules engine, duration rules, ML SHAP model, and backtesting.
"""

from pathlib import Path
import numpy as np
import pandas as pd
import pytest

from climatrend.climate.regional_alerts.climatology_builder import RegionalClimatologyBuilder
from climatrend.climate.regional_alerts.history_rules import HistoryRulesEngine
from climatrend.climate.regional_alerts.ml_alert_model import MLAlertModel
from climatrend.climate.regional_alerts.backtester import RegionalBacktester
from climatrend.climate.db.database import get_db


def test_history_rules_evaluation(temp_db_path: Path, monkeypatch):
    """Verifies percentile, duration, and return-period rules generate expected severity alerts."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    builder = RegionalClimatologyBuilder()
    builder.get_or_build_baseline(region_id=1, years_back=5, force_refresh=True)

    rules_engine = HistoryRulesEngine(builder=builder)

    # Simulate 7-day extreme heat forecast (36°C)
    extreme_forecast = {
        "time": ["2026-07-15", "2026-07-16", "2026-07-17", "2026-07-18", "2026-07-19", "2026-07-20", "2026-07-21"],
        "temperature_2m_max": [35.0, 36.5, 37.0, 37.5, 36.0, 34.0, 32.0],
        "temperature_2m_min": [20.0] * 7,
        "precipitation_sum": [0.0] * 7,
    }

    alerts = rules_engine.evaluate_forecast_for_region(region_id=1, forecast_daily=extreme_forecast)
    assert len(alerts) >= 1

    severities = [a["severity"] for a in alerts]
    assert "Warning" in severities or "Severe" in severities


def test_ml_alert_model_and_shap():
    """Verifies that the ML alert model trains and generates SHAP explanations."""
    dates = pd.date_range("2026-01-01", periods=90, freq="D")
    df = pd.DataFrame({
        "time": dates,
        "temperature_2m_max": 20.0 + 8.0 * np.sin(np.arange(90) / 10.0),
        "precipitation_sum": np.random.exponential(3.0, 90),
    })

    model = MLAlertModel(n_estimators=15)
    fitted = model.fit(df)
    assert fitted is True

    pred = model.predict_extreme_probability(df.tail(10))
    assert 0.0 <= pred["probability"] <= 1.0
    assert "shap_explanations" in pred
    assert len(pred["shap_explanations"]) > 0
    assert "explanation_text" in pred


def test_regional_backtester(temp_db_path: Path, monkeypatch):
    """Verifies that the backtester replays 10-year verification and computes metrics."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    backtester = RegionalBacktester()
    res = backtester.run_backtest(region_id=1, historical_df=pd.DataFrame(), hazard_type="extreme_heat", test_years=5)

    assert "hit_rate" in res
    assert "false_alarm_rate" in res
    assert 0.0 <= res["hit_rate"] <= 1.0
    assert 0.0 <= res["false_alarm_rate"] <= 1.0
    assert res["lead_time_hours"] == 48.0
    assert Path(res["report_path"]).exists()

    # Verify recorded in backtest_results table
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM backtest_results WHERE region_id = 1;")
        row = cursor.fetchone()
        assert row is not None
        assert row["hit_rate"] == res["hit_rate"]
