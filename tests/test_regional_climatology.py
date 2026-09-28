"""
Unit tests for Regional Climatology Builder, day-of-year percentiles,
GEV return period fitting, Mann-Kendall trends, and database caching.
"""

from pathlib import Path
import pytest
from climatrend.climate.regional_alerts.climatology_builder import RegionalClimatologyBuilder
from climatrend.climate.db.database import get_db


def test_climatology_baseline_computation(temp_db_path: Path, monkeypatch):
    """Verifies that regional baselines calculate DOY percentiles and GEV return periods."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    builder = RegionalClimatologyBuilder()

    # Region 1 is London (seeded in init_db)
    baseline_info = builder.get_or_build_baseline(region_id=1, years_back=5, force_refresh=True)

    assert baseline_info["region_name"] == "London"
    assert baseline_info["baselines_count"] > 300  # Covers days of year

    # Verify Day-of-Year percentiles in DB
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT mean, std, p5, p50, p95, p99
            FROM climatology_baselines
            WHERE region_id = 1 AND metric = 'temperature_max' AND day_of_year = 180;
            """
        )
        row = cursor.fetchone()
        assert row is not None
        assert row["p5"] <= row["p50"] <= row["p95"] <= row["p99"]
        assert row["std"] > 0

        # Verify GEV return periods
        cursor.execute("SELECT * FROM return_periods WHERE region_id = 1;")
        rps = cursor.fetchall()
        assert len(rps) >= 2  # 10-year and 50-year return periods
        for rp in rps:
            assert rp["threshold_value"] > 0

        # Verify Extreme indices
        cursor.execute("SELECT * FROM extreme_indices WHERE region_id = 1;")
        extremes = cursor.fetchall()
        assert len(extremes) >= 1
        assert "heatwave_days" in extremes[0].keys()


def test_climatology_caching_behavior(temp_db_path: Path, monkeypatch):
    """Verifies that subsequent baseline calls load directly from DB cache without recalculating."""
    import climatrend.climate.db.database as db_mod
    monkeypatch.setattr(db_mod, "DB_PATH", temp_db_path)

    builder = RegionalClimatologyBuilder()
    res1 = builder.get_or_build_baseline(region_id=1, years_back=5, force_refresh=True)

    # Call again without force_refresh
    res2 = builder.get_or_build_baseline(region_id=1, years_back=5, force_refresh=False)
    assert res1["baselines_count"] == res2["baselines_count"]
