"""
Isolation Forest Carbon Anomaly Detector.
Identifies statistical outliers in user carbon activity streams
(e.g., unusual flight spikes, power surges, abnormal waste disposal).
"""

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)


class CarbonAnomalyDetector:
    """Detects unusual activity emissions using Isolation Forest."""

    def __init__(self, contamination: float = 0.08, random_state: int = 42):
        self.contamination = contamination
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100,
        )
        self.feature_cols: List[str] = []
        self.is_fitted: bool = False

    def _prepare_feature_matrix(self, df: pd.DataFrame) -> pd.DataFrame:
        """Transforms activity records into tabular numerical representation."""
        data = df.copy()
        if "activity_date" in data.columns:
            data["activity_date"] = pd.to_datetime(data["activity_date"])
            data["day_of_week"] = data["activity_date"].dt.dayofweek
            data["day_of_month"] = data["activity_date"].dt.day
        else:
            data["day_of_week"] = 0
            data["day_of_month"] = 1

        # One-hot encode category
        cats = ["travel", "electricity", "food", "waste"]
        for c in cats:
            data[f"cat_{c}"] = (data["category"] == c).astype(int) if "category" in data.columns else 0

        feature_cols = ["co2e_kg", "value", "day_of_week", "day_of_month"] + [f"cat_{c}" for c in cats]
        self.feature_cols = feature_cols
        return data[feature_cols].fillna(0.0)

    def fit_and_detect(self, df: pd.DataFrame, update_db: bool = True) -> pd.DataFrame:
        """
        Fits the Isolation Forest on the user's activities and flags outliers.
        Outliers receive label -1; inliers receive label 1.
        Updates `is_anomaly` and `anomaly_score` in the database.
        """
        if df.empty or len(df) < 5:
            logger.warning("Insufficient activity history to run Isolation Forest.")
            result_df = df.copy()
            result_df["is_anomaly"] = 0
            result_df["anomaly_score"] = 0.0
            return result_df

        result_df = df.copy()
        X = self._prepare_feature_matrix(result_df)

        self.model.fit(X)
        self.is_fitted = True

        preds = self.model.predict(X)
        # raw decision function: lower means more abnormal
        raw_scores = self.model.decision_function(X)
        # Invert so higher score = higher severity anomaly
        anomaly_scores = -raw_scores

        result_df["is_anomaly"] = (preds == -1).astype(int)
        result_df["anomaly_score"] = np.round(anomaly_scores, 3)

        if update_db and "id" in result_df.columns:
            with get_db() as conn:
                cursor = conn.cursor()
                for _, row in result_df.iterrows():
                    cursor.execute(
                        "UPDATE carbon_activities SET is_anomaly = ?, anomaly_score = ? WHERE id = ?;",
                        (int(row["is_anomaly"]), float(row["anomaly_score"]), int(row["id"])),
                    )

        anom_count = int(result_df["is_anomaly"].sum())
        logger.info(f"Isolation Forest flagged {anom_count} anomalies out of {len(result_df)} activities.")
        return result_df
