"""
Data models and severity classifications for the Unified Alert System.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AlertSeverity(Enum):
    """
    Standard 4-tier alert severity levels.
    Supports total ordering: Advisory < Watch < Warning < Severe.
    """
    ADVISORY = "Advisory"
    WATCH = "Watch"
    WARNING = "Warning"
    SEVERE = "Severe"

    @property
    def rank(self) -> int:
        ranks = {
            AlertSeverity.ADVISORY: 1,
            AlertSeverity.WATCH: 2,
            AlertSeverity.WARNING: 3,
            AlertSeverity.SEVERE: 4,
        }
        return ranks[self]

    def __lt__(self, other: "AlertSeverity") -> bool:
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.rank < other.rank

    def __le__(self, other: "AlertSeverity") -> bool:
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.rank <= other.rank

    def __gt__(self, other: "AlertSeverity") -> bool:
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.rank > other.rank

    def __ge__(self, other: "AlertSeverity") -> bool:
        if not isinstance(other, AlertSeverity):
            return NotImplemented
        return self.rank >= other.rank

    @classmethod
    def from_str(cls, val: str) -> "AlertSeverity":
        val_clean = val.capitalize().strip()
        for member in cls:
            if member.value == val_clean:
                return member
        return cls.ADVISORY


@dataclass
class AlertEvent:
    """
    Canonical representation of an alert event.
    Shared identically across Feature 6 (Disasters) and Feature 7 (Regional Alerts).
    """
    event_id: str
    hazard_type: str
    severity: AlertSeverity
    title: str
    message: str
    source: str  # 'historical_climatology', 'usgs', 'nasa_firms', 'gdacs', 'open_meteo'
    region_id: Optional[int] = None
    region_name: Optional[str] = None
    historical_context: Optional[str] = None  # e.g., "Hotter than 98% of days in May since 1995"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    forecast_value: Optional[float] = None
    normal_value: Optional[float] = None
    time_window: str = "Next 24-72 hours"
    recommended_action: str = "Monitor local guidance and take precautions."
    detected_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "region_id": self.region_id,
            "region_name": self.region_name,
            "hazard_type": self.hazard_type,
            "severity": self.severity.value,
            "title": self.title,
            "message": self.message,
            "historical_context": self.historical_context,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "forecast_value": self.forecast_value,
            "normal_value": self.normal_value,
            "source": self.source,
            "time_window": self.time_window,
            "recommended_action": self.recommended_action,
            "detected_at": self.detected_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
