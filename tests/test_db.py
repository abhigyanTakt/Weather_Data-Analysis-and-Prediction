"""
Unit tests for ClimaTrend database initialization, schema integrity, and seeding.
"""

from pathlib import Path
import pytest
from climatrend.climate.db.database import get_db, init_db


def test_database_initialization(temp_db_path: Path):
    """Verifies that all required tables and default seeds are created."""
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row["name"] for row in cursor.fetchall()]

        required_tables = [
            "regions",
            "climatology_baselines",
            "extreme_indices",
            "return_periods",
            "alert_rules",
            "alert_subscriptions",
            "alert_log",
            "backtest_results",
            "carbon_activities",
            "environmental_readings",
            "climate_risk_scores",
            "infrastructure_assets",
        ]

        for req in required_tables:
            assert req in tables, f"Missing required table: {req}"

        # Verify seed counts
        cursor.execute("SELECT COUNT(*) FROM regions;")
        assert cursor.fetchone()[0] == 12, "Expected 12 predefined seed regions"

        cursor.execute("SELECT COUNT(*) FROM alert_rules;")
        assert cursor.fetchone()[0] >= 5, "Expected default alert rules to be seeded"

        cursor.execute("SELECT COUNT(*) FROM alert_subscriptions;")
        assert cursor.fetchone()[0] >= 1, "Expected default alert subscription"


def test_foreign_key_enforcement(temp_db_path: Path):
    """Verifies SQLite foreign key constraints are enforced."""
    with get_db(temp_db_path) as conn:
        cursor = conn.cursor()
        with pytest.raises(Exception):
            # Attempt inserting baseline for non-existent region 9999
            cursor.execute(
                """
                INSERT INTO climatology_baselines (
                    region_id, day_of_year, month, metric, mean, std, p5, p10, p50, p90, p95, p99
                ) VALUES (9999, 1, 1, 'temp', 10, 2, 5, 6, 10, 14, 15, 18);
                """
            )
