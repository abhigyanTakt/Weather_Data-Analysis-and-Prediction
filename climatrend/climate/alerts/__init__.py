"""
Shared Alert Engine Package.
Unified alert core shared by Feature 6 (Disaster Early-Warning)
and Feature 7 (Historical Regional Alerts).
"""

from climatrend.climate.alerts.models import AlertSeverity, AlertEvent
from climatrend.climate.alerts.delivery import AlertDeliveryManager
from climatrend.climate.alerts.engine import SharedAlertEngine

__all__ = ["AlertSeverity", "AlertEvent", "AlertDeliveryManager", "SharedAlertEngine"]
