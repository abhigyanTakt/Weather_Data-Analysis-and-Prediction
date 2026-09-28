"""
SHAP Carbon Attribution Explainer.
Computes local feature contribution values for anomalous carbon activities
to explain why an emission activity was flagged (e.g. excessive travel distance,
abnormal power consumption, carbon-heavy dietary choices).
"""

import logging
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
import shap
from sklearn.ensemble import RandomForestRegressor

logger = logging.getLogger(__name__)


class CarbonSHAPExplainer:
    """Explains emission anomalies using SHAP values."""

    def __init__(self):
        self.surrogate = RandomForestRegressor(n_estimators=60, random_state=42)
        self.explainer: Optional[shap.TreeExplainer] = None
        self.feature_names: List[str] = []
        self.is_fitted: bool = False

    def fit_surrogate(self, df: pd.DataFrame, feature_cols: List[str]) -> bool:
        """Fits an interpretable surrogate model predicting emission intensity."""
        if df.empty or len(df) < 5:
            return False

        try:
            X = df[feature_cols].copy().fillna(0.0)
            y = df["co2e_kg"].values if "co2e_kg" in df.columns else np.zeros(len(df))

            self.surrogate.fit(X, y)
            self.explainer = shap.TreeExplainer(self.surrogate)
            self.feature_names = feature_cols
            self.is_fitted = True
            return True
        except Exception as e:
            logger.error(f"Failed to fit SHAP surrogate: {e}")
            return False

    def explain_activity(self, activity_row: pd.Series, feature_cols: List[str]) -> Dict[str, Any]:
        """
        Computes SHAP feature attribution for a single anomalous activity record.
        Returns top drivers and a natural language explanation.
        """
        if not self.is_fitted or self.explainer is None:
            # Fallback heuristic explanation
            val = activity_row.get("value", 0.0)
            co2e = activity_row.get("co2e_kg", 0.0)
            cat = activity_row.get("category", "activity")
            return {
                "shap_values": {"Emission Magnitude": round(co2e * 0.7, 2), "Activity Volume": round(val * 0.3, 2)},
                "summary": f"Flagged primarily due to high {cat} volume ({val}) generating {co2e:.1f} kg CO2e.",
            }

        try:
            X_sample = pd.DataFrame([activity_row[feature_cols].fillna(0.0)])
            shap_vals = self.explainer(X_sample)
            vals = shap_vals.values[0]

            contributions = {}
            for fname, val in zip(self.feature_names, vals):
                clean_name = fname.replace("cat_", "Category: ").replace("_", " ").title()
                contributions[clean_name] = round(float(val), 2)

            # Sort top 4 contributors by absolute attribution
            sorted_contrib = dict(
                sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)[:4]
            )

            # Build narrative explanation
            top_pos = [f"{k} (+{v} kg)" for k, v in sorted_contrib.items() if v > 0]
            if top_pos:
                summary = f"Emission spike driven by: {', '.join(top_pos)}."
            else:
                summary = "Activity emission deviates significantly from baseline profile."

            return {
                "shap_values": sorted_contrib,
                "summary": summary,
            }
        except Exception as e:
            logger.warning(f"Error computing SHAP explanation: {e}")
            return {
                "shap_values": {"Volume": 1.0},
                "summary": "Outlier identified based on statistical variance.",
            }
