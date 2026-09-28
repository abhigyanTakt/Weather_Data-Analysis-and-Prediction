"""
Background Scheduler for periodic disaster ingestion and alert checks.
Runs as a background daemon inside Streamlit or as a standalone CLI worker.
"""

import logging
import sys
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from climatrend.climate.config import ALERT_CHECK_INTERVAL_HOURS
from climatrend.climate.db.database import init_db

logger = logging.getLogger(__name__)

_SCHEDULER_INSTANCE: Optional[BackgroundScheduler] = None


def run_scheduled_disaster_check() -> None:
    """Scheduled job: Ingests USGS and FIRMS alerts and processes through Shared Alert Engine."""
    try:
        logger.info("Running scheduled disaster check job...")
        from climatrend.climate.disasters.service import DisasterService
        service = DisasterService()
        alerts = service.check_all_monitored_regions()
        logger.info(f"Disaster check completed. Processed {len(alerts)} alerts.")
    except Exception as e:
        logger.error(f"Error during scheduled disaster check: {e}")


def run_scheduled_climatology_check() -> None:
    """Scheduled job: Evaluates current forecasts against regional baselines."""
    try:
        logger.info("Running scheduled regional climatology alert check...")
        from climatrend.climate.regional_alerts.history_rules import HistoryRulesEngine
        engine = HistoryRulesEngine()
        alerts = engine.check_all_regions()
        logger.info(f"Climatology check completed. Processed {len(alerts)} alerts.")
    except Exception as e:
        logger.error(f"Error during scheduled climatology check: {e}")


def start_scheduler() -> BackgroundScheduler:
    """Starts the background scheduler singleton if not already running."""
    global _SCHEDULER_INSTANCE

    if getattr(sys, "_climate_scheduler_started", False) and _SCHEDULER_INSTANCE is not None:
        return _SCHEDULER_INSTANCE

    init_db()

    scheduler = BackgroundScheduler(daemon=True)

    # Schedule disaster checks every N hours
    scheduler.add_job(
        run_scheduled_disaster_check,
        trigger=IntervalTrigger(hours=ALERT_CHECK_INTERVAL_HOURS),
        id="disaster_check_job",
        name="Scheduled Disaster Alerts Ingestion",
        replace_existing=True,
    )

    # Schedule regional climatology checks every N hours
    scheduler.add_job(
        run_scheduled_climatology_check,
        trigger=IntervalTrigger(hours=ALERT_CHECK_INTERVAL_HOURS),
        id="climatology_check_job",
        name="Scheduled Climatology Alerts Evaluation",
        replace_existing=True,
    )

    scheduler.start()
    _SCHEDULER_INSTANCE = scheduler
    sys._climate_scheduler_started = True
    logger.info(f"Climate Background Scheduler started (Interval: {ALERT_CHECK_INTERVAL_HOURS}h).")
    return scheduler


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    logger.info("Starting ClimaTrend Scheduler in standalone CLI mode...")
    sched = start_scheduler()
    import time
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down scheduler...")
        sched.shutdown()
