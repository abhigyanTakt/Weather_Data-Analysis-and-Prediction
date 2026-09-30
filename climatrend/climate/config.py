"""
Central configuration module for ClimaTrend Climate Extensions.
Manages file paths, database location, external API keys, timeouts,
caching policies, and notification endpoints.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# Load root .env file if available
PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


def get_setting(name: str, default: str = ""):
	"""Read a Streamlit secret first, then fall back to the process environment."""
	try:
		value = st.secrets.get(name)
	except Exception:
		value = None
	return value if value not in (None, "") else os.getenv(name, default)

# ----------------- STORAGE & PATHS -----------------
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PACKAGE_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
CLIMATE_CACHE_DIR = DATA_DIR / "climate_cache"
DB_PATH = DATA_DIR / "climate.db"

# Ensure storage directories exist
RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)
CLIMATE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ----------------- NETWORK & RESILIENCE DEFAULTS -----------------
DEFAULT_CONNECT_TIMEOUT = 5.0    # Seconds to establish TCP handshake
DEFAULT_READ_TIMEOUT = 15.0      # Seconds to receive full payload
DEFAULT_MAX_RETRIES = 3          # Exponential backoff attempts
DEFAULT_BACKOFF_FACTOR = 1.5     # Retry delay multiplier
DEFAULT_CACHE_TTL_HOURLY = 3600  # 1 hour for real-time data
DEFAULT_CACHE_TTL_DAILY = 86400  # 24 hours for daily data
DEFAULT_CACHE_TTL_STATIC = 86400 * 30  # 30 days for climatology baselines

# ----------------- EXTERNAL APIS & KEYS -----------------
OPEN_METEO_BASE_URL = "https://api.open-meteo.com/v1"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
OPEN_METEO_FLOOD_URL = "https://flood-api.open-meteo.com/v1/flood"
OPEN_METEO_ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"

OPENAQ_API_KEY = get_setting("OPENAQ_API_KEY")
OPENAQ_BASE_URL = "https://api.openaq.org/v3"

NASA_FIRMS_MAP_KEY = get_setting("NASA_FIRMS_MAP_KEY")
NASA_FIRMS_BASE_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"

USGS_EARTHQUAKE_URL = "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson"
GDACS_FEED_URL = "https://www.gdacs.org/xml/rss.xml"
RELIEFWEB_API_URL = "https://api.reliefweb.int/v1/reports"

CLIMATIQ_API_KEY = get_setting("CLIMATIQ_API_KEY")
CLIMATIQ_BASE_URL = "https://api.climatiq.io/data/v1/estimate"

# ----------------- ALERT DELIVERY CONFIGURATION -----------------
TELEGRAM_BOT_TOKEN = get_setting("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = get_setting("TELEGRAM_CHAT_ID")

SMTP_HOST = get_setting("SMTP_HOST")
SMTP_PORT = int(get_setting("SMTP_PORT", "587"))
SMTP_USER = get_setting("SMTP_USER")
SMTP_PASSWORD = get_setting("SMTP_PASSWORD")
SMTP_RECIPIENT = get_setting("SMTP_RECIPIENT")

NTFY_TOPIC = get_setting("NTFY_TOPIC", "climatrend_emergency_alerts")
NTFY_SERVER = get_setting("NTFY_SERVER", "https://ntfy.sh")

ALERT_CHECK_INTERVAL_HOURS = int(get_setting("ALERT_CHECK_INTERVAL_HOURS", "3"))

CARTO_API_KEY = get_setting("CARTO_API_KEY")

# Alert deduplication cooldown in hours (suppress identical alert unless severity escalates)
ALERT_DEDUP_COOLDOWN_HOURS = 12
