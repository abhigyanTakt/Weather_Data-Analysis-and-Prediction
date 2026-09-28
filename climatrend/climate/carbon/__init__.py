"""
Carbon-Footprint Tracking & Emission Analytics Package.
"""

from climatrend.climate.carbon.service import CarbonService
from climatrend.climate.carbon.anomaly_detector import CarbonAnomalyDetector
from climatrend.climate.carbon.explainer import CarbonSHAPExplainer

__all__ = ["CarbonService", "CarbonAnomalyDetector", "CarbonSHAPExplainer"]
