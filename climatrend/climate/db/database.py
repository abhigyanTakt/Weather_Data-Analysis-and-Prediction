"""
Database connection manager and helper utilities for ClimaTrend.
Uses SQLite with Write-Ahead Logging (WAL) for high concurrency and zero external dependencies.
"""

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import date, timedelta
from pathlib import Path
from typing import Generator, Optional, Dict, Any, List

from climatrend.climate.config import DB_PATH

logger = logging.getLogger(__name__)

SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Default seed regions matching ClimaTrend's PREDEFINED_CITIES
SEED_REGIONS = [
    {"name": "London", "lat": 51.5074, "lon": -0.1278, "country": "United Kingdom", "elevation": 25.0},
    {"name": "New York", "lat": 40.7128, "lon": -74.0060, "country": "United States", "elevation": 10.0},
    {"name": "Tokyo", "lat": 35.6762, "lon": 139.6503, "country": "Japan", "elevation": 44.0},
    {"name": "Sydney", "lat": -33.8688, "lon": 151.2093, "country": "Australia", "elevation": 19.0},
    {"name": "Cairo", "lat": 30.0444, "lon": 31.2357, "country": "Egypt", "elevation": 23.0},
    {"name": "Moscow", "lat": 55.7558, "lon": 37.6173, "country": "Russia", "elevation": 156.0},
    {"name": "Rio de Janeiro", "lat": -22.9068, "lon": -43.1729, "country": "Brazil", "elevation": 5.0},
    {"name": "Mumbai", "lat": 19.0760, "lon": 72.8777, "country": "India", "elevation": 14.0},
    {"name": "Cape Town", "lat": -33.9249, "lon": 18.4241, "country": "South Africa", "elevation": 42.0},
    {"name": "Singapore", "lat": 1.3521, "lon": 103.8198, "country": "Singapore", "elevation": 15.0},
    {"name": "Paris", "lat": 48.8566, "lon": 2.3522, "country": "France", "elevation": 35.0},
    {"name": "Buenos Aires", "lat": -34.6037, "lon": -58.3816, "country": "Argentina", "elevation": 25.0},
]

# Default seed alert rules
SEED_ALERT_RULES = [
    {
        "rule_name": "extreme_heat_p95",
        "hazard_type": "extreme_heat",
        "condition_type": "percentile",
        "threshold_config": json.dumps({"percentile": 95, "metric": "temperature_max", "min_days": 1}),
        "severity": "Watch",
    },
    {
        "rule_name": "extreme_heat_p99",
        "hazard_type": "extreme_heat",
        "condition_type": "percentile",
        "threshold_config": json.dumps({"percentile": 99, "metric": "temperature_max", "min_days": 1}),
        "severity": "Warning",
    },
    {
        "rule_name": "prolonged_heatwave_3d",
        "hazard_type": "extreme_heat",
        "condition_type": "duration_persistence",
        "threshold_config": json.dumps({"percentile": 90, "metric": "temperature_max", "consecutive_days": 3}),
        "severity": "Severe",
    },
    {
        "rule_name": "heavy_rainfall_p95",
        "hazard_type": "heavy_rain",
        "condition_type": "percentile",
        "threshold_config": json.dumps({"percentile": 95, "metric": "precipitation", "min_mm": 25.0}),
        "severity": "Watch",
    },
    {
        "rule_name": "rainfall_1_in_10_year",
        "hazard_type": "heavy_rain",
        "condition_type": "return_period",
        "threshold_config": json.dumps({"return_period_years": 10, "metric": "precipitation"}),
        "severity": "Warning",
    },
    {
        "rule_name": "rainfall_1_in_50_year",
        "hazard_type": "heavy_rain",
        "condition_type": "return_period",
        "threshold_config": json.dumps({"return_period_years": 50, "metric": "precipitation"}),
        "severity": "Severe",
    },
    {
        "rule_name": "prolonged_drought_15d",
        "hazard_type": "drought",
        "condition_type": "duration_persistence",
        "threshold_config": json.dumps({"consecutive_dry_days": 15, "max_daily_precip_mm": 1.0}),
        "severity": "Watch",
    },
    {
        "rule_name": "usgs_earthquake_mag5",
        "hazard_type": "earthquake",
        "condition_type": "proximity_threshold",
        "threshold_config": json.dumps({"min_magnitude": 5.0, "max_radius_km": 150.0}),
        "severity": "Warning",
    },
    {
        "rule_name": "usgs_earthquake_mag6",
        "hazard_type": "earthquake",
        "condition_type": "proximity_threshold",
        "threshold_config": json.dumps({"min_magnitude": 6.5, "max_radius_km": 300.0}),
        "severity": "Severe",
    },
    {
        "rule_name": "firms_wildfire_nearby",
        "hazard_type": "wildfire",
        "condition_type": "proximity_threshold",
        "threshold_config": json.dumps({"min_confidence": 75, "max_radius_km": 50.0}),
        "severity": "Warning",
    },
]


def create_connection(path: Optional[Path] = None) -> sqlite3.Connection:
    """Creates a configured SQLite connection."""
    target_path = path or DB_PATH
    conn = sqlite3.connect(str(target_path), timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn


@contextmanager
def get_db(path: Optional[Path] = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager for SQLite database connections with auto-commit and error rollback."""
    conn = create_connection(path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database transaction error: {e}")
        raise
    finally:
        conn.close()


def init_database(path: Optional[Path] = None) -> None:
    """Initializes the database schema and seeds initial regions and alert rules."""
    target_path = path or DB_PATH
    target_path.parent.mkdir(parents=True, exist_ok=True)

    with get_db(target_path) as conn:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)

        # Seed default regions if empty
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM regions;")
        if cursor.fetchone()[0] == 0:
            for r in SEED_REGIONS:
                cursor.execute(
                    """
                    INSERT INTO regions (name, latitude, longitude, country, elevation)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (r["name"], r["lat"], r["lon"], r["country"], r["elevation"]),
                )
            logger.info("Seeded initial monitored regions.")

        cursor.execute("SELECT COUNT(*) FROM climatology_baselines;")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO climatology_baselines (
                    region_id, day_of_year, month, metric, mean, std,
                    p5, p10, p50, p90, p95, p99, sample_years
                ) VALUES (1, 1, 1, 'temperature_2m_mean', 5.2, 3.4,
                          -1.0, 1.0, 5.2, 9.5, 10.5, 12.0, 0);
                """
            )
            logger.info("Seeded the demonstration climatology baseline.")

        cursor.execute("SELECT COUNT(*) FROM carbon_activities;")
        if cursor.fetchone()[0] == 0:
            today = date.today()
            cursor.executemany(
                """
                INSERT INTO carbon_activities (
                    user_id, activity_date, category, subcategory,
                    value, unit, co2e_kg, notes
                ) VALUES ('user_default', ?, ?, ?, ?, ?, ?, 'Startup demo activity');
                """,
                [
                    ((today - timedelta(days=1)).isoformat(), "transport", "car", 12.0, "km", 2.76),
                    (today.isoformat(), "energy", "electricity", 8.0, "kWh", 3.2),
                ],
            )
            logger.info("Seeded sample carbon activities.")

        # Seed default alert rules if empty
        cursor.execute("SELECT COUNT(*) FROM alert_rules;")
        if cursor.fetchone()[0] == 0:
            for rule in SEED_ALERT_RULES:
                cursor.execute(
                    """
                    INSERT INTO alert_rules (rule_name, hazard_type, condition_type, threshold_config, severity)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (
                        rule["rule_name"],
                        rule["hazard_type"],
                        rule["condition_type"],
                        rule["threshold_config"],
                        rule["severity"],
                    ),
                )
            logger.info("Seeded default alert rules.")

        # Seed default user subscription if empty
        cursor.execute("SELECT COUNT(*) FROM alert_subscriptions;")
        if cursor.fetchone()[0] == 0:
            cursor.execute(
                """
                INSERT INTO alert_subscriptions (user_id, region_id, hazard_types, min_severity, channels)
                VALUES ('user_default', 1, '["all"]', 'Advisory', '["in_app"]');
                """
            )
            logger.info("Seeded default alert subscription.")

    logger.info(f"Database initialized successfully at {target_path}")


init_db = init_database


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    init_database()
    print("ClimaTrend SQLite database initialized and seeded successfully.")
