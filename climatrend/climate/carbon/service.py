"""
Carbon Footprint Tracking Service.
Handles logging of user emission activities across travel, electricity, food, and waste,
calculates CO2e using authoritative emission factors, performs aggregations,
and manages activity persistence.
"""

from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from climatrend.climate.clients.emission_client import EmissionClient, OFFLINE_EMISSION_FACTORS
from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)


class CarbonService:
    """Service for logging and aggregating user carbon emissions."""

    def __init__(self, emission_client: Optional[EmissionClient] = None):
        self.emission_client = emission_client or EmissionClient()

    def log_activity(
        self,
        user_id: str,
        activity_date: str,
        category: str,
        subcategory: str,
        value: float,
        unit: Optional[str] = None,
        notes: str = "",
    ) -> Dict[str, Any]:
        """
        Converts activity value into kg CO2e and persists into the database.
        """
        factor_info = self.emission_client.get_factor_info(subcategory)
        resolved_unit = unit or (factor_info["unit"] if factor_info else "unit")
        co2e = self.emission_client.calculate_co2e(subcategory, value)

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO carbon_activities (
                    user_id, activity_date, category, subcategory, value, unit, co2e_kg, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (user_id, activity_date, category, subcategory, value, resolved_unit, co2e, notes),
            )
            activity_id = cursor.lastrowid

        logger.info(f"Logged activity #{activity_id} for user '{user_id}': {value} {resolved_unit} -> {co2e} kg CO2e")
        return {
            "id": activity_id,
            "user_id": user_id,
            "activity_date": activity_date,
            "category": category,
            "subcategory": subcategory,
            "value": value,
            "unit": resolved_unit,
            "co2e_kg": co2e,
            "notes": notes,
        }

    def get_user_activities(
        self, user_id: str = "user_default", start_date: Optional[str] = None, end_date: Optional[str] = None
    ) -> pd.DataFrame:
        """Retrieves user activity history as a pandas DataFrame."""
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM carbon_activities WHERE user_id = ?"
            params: List[Any] = [user_id]

            if start_date:
                query += " AND activity_date >= ?"
                params.append(start_date)
            if end_date:
                query += " AND activity_date <= ?"
                params.append(end_date)

            query += " ORDER BY activity_date DESC, id DESC;"
            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame([dict(r) for r in rows])
        df["activity_date"] = pd.to_datetime(df["activity_date"])
        return df

    def get_aggregated_metrics(self, user_id: str = "user_default") -> Dict[str, Any]:
        """Calculates daily, weekly, monthly totals and category breakdowns."""
        df = self.get_user_activities(user_id)
        if df.empty:
            return {
                "total_co2e_kg": 0.0,
                "total_co2e_tonnes": 0.0,
                "monthly_co2e_kg": 0.0,
                "weekly_avg_kg": 0.0,
                "anomaly_count": 0,
                "category_breakdown": {},
                "monthly_summary": pd.DataFrame(),
                "daily_trend": pd.DataFrame(),
            }

        total_co2e = float(df["co2e_kg"].sum())
        total_tonnes = total_co2e / 1000.0

        # Current month totals
        current_month = datetime.utcnow().strftime("%Y-%m")
        df["year_month"] = df["activity_date"].dt.strftime("%Y-%m")
        month_df = df[df["year_month"] == current_month]
        monthly_co2e = float(month_df["co2e_kg"].sum()) if not month_df.empty else 0.0

        # Weekly average
        date_span_days = max(1, (df["activity_date"].max() - df["activity_date"].min()).days)
        weeks = max(1.0, date_span_days / 7.0)
        weekly_avg = round(total_co2e / weeks, 1)

        # Anomaly count
        anomaly_count = int(df["is_anomaly"].sum()) if "is_anomaly" in df.columns else 0

        # Category breakdown
        cat_breakdown = df.groupby("category")["co2e_kg"].sum().to_dict()

        # Monthly summary
        monthly_summary = (
            df.groupby("year_month")["co2e_kg"]
            .sum()
            .reset_index()
            .sort_values("year_month")
        )

        # Daily trend
        daily_trend = (
            df.groupby("activity_date")["co2e_kg"]
            .sum()
            .reset_index()
            .sort_values("activity_date")
        )

        return {
            "total_co2e_kg": round(total_co2e, 1),
            "total_co2e_tonnes": round(total_tonnes, 2),
            "monthly_co2e_kg": round(monthly_co2e, 1),
            "weekly_avg_kg": weekly_avg,
            "anomaly_count": anomaly_count,
            "category_breakdown": {k: round(v, 1) for k, v in cat_breakdown.items()},
            "monthly_summary": monthly_summary,
            "daily_trend": daily_trend,
        }

    def seed_sample_activities_if_empty(self, user_id: str = "user_default") -> int:
        """Populates demonstration activities if user activity table is empty."""
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM carbon_activities WHERE user_id = ?;", (user_id,))
            if cursor.fetchone()[0] > 0:
                return 0

        logger.info(f"Seeding realistic demonstration carbon activities for '{user_id}'...")
        today = datetime.utcnow().date()
        sample_records = [
            # Regular daily commutes and energy
            (2, "travel", "car_petrol", 25.0, "km", "Daily suburban commute"),
            (3, "electricity", "grid_average", 14.5, "kWh", "Household daily electricity consumption"),
            (4, "food", "vegetarian_meal", 2.0, "meal", "Vegetarian lunch and dinner"),
            (5, "food", "beef_meal", 1.0, "meal", "Steak dinner"),
            (7, "waste", "landfill_waste", 4.2, "kg", "Weekly household residual waste"),
            (8, "travel", "train", 45.0, "km", "Commuter rail round trip"),
            (10, "electricity", "grid_average", 16.0, "kWh", "High AC heating consumption"),
            (12, "food", "poultry_meal", 2.0, "meal", "Chicken Caesar salad lunch"),
            (14, "travel", "bus", 12.0, "km", "City bus trip to shopping center"),
            (18, "waste", "recycled_waste", 8.0, "kg", "Cardboard and paper recycling"),
            (22, "travel", "car_petrol", 70.0, "km", "Weekend countryside excursion"),
            (25, "food", "vegan_meal", 3.0, "meal", "Plant-based meal day"),
            (28, "electricity", "grid_average", 13.0, "kWh", "Normal weekday power draw"),
            # Anomaly: Long-haul commercial flight
            (32, "travel", "flight_business", 2400.0, "km", "International business flight to conference"),
            (35, "travel", "flight_economy", 1100.0, "km", "Return domestic flight"),
            (40, "electricity", "grid_average", 18.0, "kWh", "Server and home office power"),
            (45, "food", "beef_meal", 2.0, "meal", "Barbecue gathering"),
            (50, "travel", "car_petrol", 30.0, "km", "Client site visit"),
        ]

        inserted = 0
        for days_ago, cat, subcat, val, unit, notes in sample_records:
            act_date = (today - timedelta(days=days_ago)).strftime("%Y-%m-%d")
            self.log_activity(
                user_id=user_id,
                activity_date=act_date,
                category=cat,
                subcategory=subcat,
                value=val,
                unit=unit,
                notes=notes,
            )
            inserted += 1

        return inserted
