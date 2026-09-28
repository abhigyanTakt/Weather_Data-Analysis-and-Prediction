"""
Shared Alert Engine.
Central engine powering both Feature 6 (Disaster Early-Warning)
and Feature 7 (Historical Regional Alerts) with deduplication,
severity escalation, subscription filtering, and unified logging.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from climatrend.climate.alerts.delivery import AlertDeliveryManager
from climatrend.climate.alerts.models import AlertEvent, AlertSeverity
from climatrend.climate.config import ALERT_DEDUP_COOLDOWN_HOURS
from climatrend.climate.db.database import get_db

logger = logging.getLogger(__name__)


class SharedAlertEngine:
    """
    Unified alert processor used by all climate modules.
    Enforces deduplication, escalation, subscription routing, and persistent logging.
    """

    def __init__(self, delivery_manager: Optional[AlertDeliveryManager] = None):
        self.delivery = delivery_manager or AlertDeliveryManager()

    def process_event(self, event: AlertEvent) -> Dict[str, Any]:
        """
        Processes an incoming alert event:
        1. Checks database for duplicates/active alerts with same event_id.
        2. Escalates if new severity > previous severity; suppresses if duplicate.
        3. Identifies subscriber channels.
        4. Dispatches notifications.
        5. Records or updates the entry in alert_log.
        """
        cooldown_threshold = (
            datetime.utcnow() - timedelta(hours=ALERT_DEDUP_COOLDOWN_HOURS)
        ).strftime("%Y-%m-%d %H:%M:%S")

        with get_db() as conn:
            cursor = conn.cursor()

            # 1. Deduplication & Escalation Check
            cursor.execute(
                """
                SELECT id, severity, status, detected_at
                FROM alert_log
                WHERE event_id = ? AND detected_at >= ?
                ORDER BY detected_at DESC LIMIT 1;
                """,
                (event.event_id, cooldown_threshold),
            )
            existing = cursor.fetchone()

            is_escalation = False
            if existing:
                prev_severity = AlertSeverity.from_str(existing["severity"])
                if event.severity > prev_severity:
                    is_escalation = True
                    event.title = f"🔺 [ESCALATED to {event.severity.value}] {event.title}"
                    event.message = f"Severity escalated from {prev_severity.value} to {event.severity.value}. {event.message}"
                    logger.info(f"Escalating alert {event.event_id}: {prev_severity.value} -> {event.severity.value}")
                else:
                    logger.info(
                        f"Suppressing duplicate alert {event.event_id} (Severity: {event.severity.value}, unchanged)."
                    )
                    return {
                        "status": "suppressed",
                        "event_id": event.event_id,
                        "reason": "Duplicate within cooldown window",
                    }

            # 2. Match Subscriptions to Determine Delivery Channels
            cursor.execute(
                """
                SELECT user_id, hazard_types, min_severity, channels, destination
                FROM alert_subscriptions
                WHERE is_active = 1
                AND (region_id IS NULL OR region_id = ?);
                """,
                (event.region_id,),
            )
            subscriptions = cursor.fetchall()

            aggregated_channels = {"in_app"}
            for sub in subscriptions:
                min_sev = AlertSeverity.from_str(sub["min_severity"])
                if event.severity >= min_sev:
                    try:
                        hazards = json.loads(sub["hazard_types"])
                        if "all" in hazards or event.hazard_type in hazards:
                            sub_channels = json.loads(sub["channels"])
                            for ch in sub_channels:
                                aggregated_channels.add(ch)
                    except Exception as e:
                        logger.warning(f"Error parsing subscription {sub['user_id']}: {e}")

            # 3. Dispatch via Delivery Layer
            sent_channels = self.delivery.dispatch(
                event=event,
                channels=list(aggregated_channels),
            )

            # 4. Record to Shared alert_log Table
            if is_escalation and existing:
                cursor.execute(
                    """
                    UPDATE alert_log
                    SET severity = ?, title = ?, message = ?, sent_channels = ?, status = 'escalated'
                    WHERE id = ?;
                    """,
                    (
                        event.severity.value,
                        event.title,
                        event.message,
                        json.dumps(sent_channels),
                        existing["id"],
                    ),
                )
                action_status = "escalated"
            else:
                cursor.execute(
                    """
                    INSERT INTO alert_log (
                        event_id, region_id, hazard_type, severity, title, message,
                        historical_context, latitude, longitude, source,
                        forecast_value, normal_value, sent_channels, status, expires_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        event.event_id,
                        event.region_id,
                        event.hazard_type,
                        event.severity.value,
                        event.title,
                        event.message,
                        event.historical_context,
                        event.latitude,
                        event.longitude,
                        event.source,
                        event.forecast_value,
                        event.normal_value,
                        json.dumps(sent_channels),
                        "active",
                        event.expires_at.strftime("%Y-%m-%d %H:%M:%S") if event.expires_at else None,
                    ),
                )
                action_status = "dispatched"

        return {
            "status": action_status,
            "event_id": event.event_id,
            "severity": event.severity.value,
            "sent_channels": sent_channels,
        }

    def get_recent_alerts(
        self, region_id: Optional[int] = None, limit: int = 50, active_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Retrieves recent alerts from the shared alert_log table."""
        with get_db() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM alert_log"
            params: List[Any] = []
            conditions = []

            if region_id is not None:
                conditions.append("region_id = ?")
                params.append(region_id)
            if active_only:
                conditions.append("status IN ('active', 'escalated')")

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY detected_at DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, tuple(params))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def subscribe_user(
        self,
        user_id: str,
        region_id: Optional[int],
        hazard_types: List[str],
        min_severity: str = "Advisory",
        channels: Optional[List[str]] = None,
        destination: Optional[str] = None,
    ) -> int:
        """Adds or updates an alert subscription."""
        target_channels = channels or ["in_app"]
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO alert_subscriptions (
                    user_id, region_id, hazard_types, min_severity, channels, destination
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    user_id,
                    region_id,
                    json.dumps(hazard_types),
                    min_severity,
                    json.dumps(target_channels),
                    destination,
                ),
            )
            return cursor.lastrowid
