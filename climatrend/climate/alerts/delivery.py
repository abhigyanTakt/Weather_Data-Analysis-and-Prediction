"""
Unified Alert Delivery Layer.
Dispatches notifications across In-App, Telegram, Email (SMTP), ntfy push, and Apprise.
Never raises fatal exceptions; records delivery success/failure cleanly.
"""

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, List, Optional

import requests

from climatrend.climate.alerts.models import AlertEvent, AlertSeverity
from climatrend.climate.config import (
    NTFY_SERVER,
    NTFY_TOPIC,
    SMTP_HOST,
    SMTP_PASSWORD,
    SMTP_PORT,
    SMTP_RECIPIENT,
    SMTP_USER,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
)

logger = logging.getLogger(__name__)


class AlertDeliveryManager:
    """Manages multi-channel dispatch of alerts with resilience."""

    def __init__(self):
        self.session = requests.Session()

    def format_alert_text(self, event: AlertEvent) -> str:
        """Formats an alert into a readable markdown string with historical context."""
        hist = f"\n📊 **Historical Context**: {event.historical_context}" if event.historical_context else ""
        text = (
            f"🚨 **CLIMATREND ALERT: {event.severity.value.upper()}**\n"
            f"**Hazard**: {event.hazard_type.replace('_', ' ').title()}\n"
            f"**Location**: {event.region_name or 'Monitored Area'}\n"
            f"**Summary**: {event.title}\n"
            f"**Details**: {event.message}{hist}\n"
            f"⏱️ **Time Window**: {event.time_window}\n"
            f"🛡️ **Action Required**: {event.recommended_action}\n"
            f"📡 **Source**: {event.source}"
        )
        return text

    def send_telegram(self, event: AlertEvent, chat_id: Optional[str] = None) -> bool:
        """Sends alert message to a Telegram chat."""
        token = TELEGRAM_BOT_TOKEN
        target_chat = chat_id or TELEGRAM_CHAT_ID

        if not token or not target_chat:
            logger.debug("Telegram credentials not configured; skipping Telegram dispatch.")
            return False

        url = f"https://api.telegram.org/bot{token}/sendMessage"
        payload = {
            "chat_id": target_chat,
            "text": self.format_alert_text(event),
            "parse_mode": "Markdown",
        }
        try:
            resp = self.session.post(url, json=payload, timeout=8.0)
            if resp.status_code == 200:
                logger.info(f"Successfully dispatched alert {event.event_id} via Telegram.")
                return True
            else:
                logger.warning(f"Telegram dispatch failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.warning(f"Telegram dispatch exception: {e}")
            return False

    def send_ntfy(self, event: AlertEvent, topic: Optional[str] = None) -> bool:
        """Sends push notification via free, open-source ntfy.sh."""
        target_topic = topic or NTFY_TOPIC
        if not target_topic:
            return False

        # Map severity to ntfy priority
        priority_map = {
            AlertSeverity.ADVISORY: "low",
            AlertSeverity.WATCH: "default",
            AlertSeverity.WARNING: "high",
            AlertSeverity.SEVERE: "urgent",
        }
        headers = {
            "Title": f"[{event.severity.value}] {event.title}",
            "Priority": priority_map.get(event.severity, "default"),
            "Tags": "warning,climate",
        }
        url = f"{NTFY_SERVER.rstrip('/')}/{target_topic}"
        try:
            resp = self.session.post(
                url,
                data=self.format_alert_text(event).encode("utf-8"),
                headers=headers,
                timeout=8.0,
            )
            if resp.status_code == 200:
                logger.info(f"Successfully dispatched alert {event.event_id} via ntfy ({target_topic}).")
                return True
            else:
                logger.warning(f"ntfy dispatch failed ({resp.status_code}): {resp.text}")
                return False
        except Exception as e:
            logger.warning(f"ntfy dispatch exception: {e}")
            return False

    def send_email(self, event: AlertEvent, recipient: Optional[str] = None) -> bool:
        """Sends alert notification via SMTP."""
        target_recipient = recipient or SMTP_RECIPIENT
        if not SMTP_HOST or not SMTP_USER or not target_recipient:
            logger.debug("SMTP credentials not configured; skipping Email dispatch.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ClimaTrend Alert [{event.severity.value}]: {event.title}"
        msg["From"] = SMTP_USER
        msg["To"] = target_recipient

        body_text = self.format_alert_text(event)
        msg.attach(MIMEText(body_text, "plain"))

        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10.0) as server:
                server.starttls()
                if SMTP_PASSWORD:
                    server.login(SMTP_USER, SMTP_PASSWORD)
                server.sendmail(SMTP_USER, [target_recipient], msg.as_string())
            logger.info(f"Successfully dispatched alert {event.event_id} to email {target_recipient}.")
            return True
        except Exception as e:
            logger.warning(f"Email dispatch exception: {e}")
            return False

    def dispatch(
        self,
        event: AlertEvent,
        channels: Optional[List[str]] = None,
        destination_override: Optional[str] = None,
    ) -> List[str]:
        """
        Dispatches the alert across all requested channels.
        Returns a list of successfully delivered channel names.
        """
        target_channels = channels or ["in_app"]
        successful_channels = ["in_app"]  # In-app logging is always recorded

        for ch in target_channels:
            ch_clean = ch.lower().strip()
            if ch_clean == "telegram":
                if self.send_telegram(event, chat_id=destination_override):
                    successful_channels.append("telegram")
            elif ch_clean == "ntfy":
                if self.send_ntfy(event, topic=destination_override):
                    successful_channels.append("ntfy")
            elif ch_clean == "email":
                if self.send_email(event, recipient=destination_override):
                    successful_channels.append("email")

        return list(set(successful_channels))
