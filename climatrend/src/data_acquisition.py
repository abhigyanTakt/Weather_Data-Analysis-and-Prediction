"""
ClimaTrend Data Acquisition Module.

This module provides functions to geocode city names and fetch historical weather
data from the Open-Meteo Historical Weather API.
"""

import os
import logging
from typing import Tuple, Dict, Any, Optional
import pandas as pd
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Constants
OPEN_METEO_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
OPEN_METEO_ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"


def geocode_city(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Geocodes a city name to get its latitude, longitude, elevation, and country.

    Args:
        city_name: The name of the city to search for.

    Returns:
        A dictionary containing 'lat', 'lon', 'elevation', 'country', and 'name'
        if found, else None.
    """
    logger.info(f"Geocoding city: {city_name}")
    params = {"name": city_name, "count": 1, "format": "json"}

    try:
        response = requests.get(OPEN_METEO_GEOCODE_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "results" in data and len(data["results"]) > 0:
            result = data["results"][0]
            info = {
                "name": result.get("name"),
                "lat": result.get("latitude"),
                "lon": result.get("longitude"),
                "elevation": result.get("elevation", 0.0),
                "country": result.get("country", "Unknown"),
            }
            logger.info(f"Found: {info['name']}, {info['country']} ({info['lat']}, {info['lon']})")
            return info
        else:
            logger.warning(f"No geocoding results found for city: {city_name}")
            return None
    except Exception as e:
        logger.error(f"Error during geocoding: {str(e)}")
        return None


def fetch_historical_weather(
    lat: float,
    lon: float,
    start_date: str,
    end_date: str,
    cache_dir: str = "climatrend/data/raw",
    city_name: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Fetches historical weather data from Open-Meteo Archive API.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.
        start_date: Start date in 'YYYY-MM-DD' format.
        end_date: End date in 'YYYY-MM-DD' format.
        cache_dir: Directory to save the cached raw data.
        city_name: Optional name of the city to use for the cache filename.

    Returns:
        A pandas DataFrame with hourly weather parameters, or None if failed.
    """
    # Create cache directory if it doesn't exist
    os.makedirs(cache_dir, exist_ok=True)

    # Resolve cache filename
    loc_str = f"{city_name.lower().replace(' ', '_')}" if city_name else f"{lat:.4f}_{lon:.4f}"
    cache_path = os.path.join(cache_dir, f"raw_weather_{loc_str}_{start_date}_to_{end_date}.csv")

    if os.path.exists(cache_path):
        logger.info(f"Loading cached historical weather data from {cache_path}")
        return pd.read_csv(cache_path, parse_dates=["time"])

    logger.info(f"Fetching historical weather data for ({lat}, {lon}) from {start_date} to {end_date}")

    # We request hourly parameters to analyze the meteorological conditions thoroughly.
    # Open-Meteo Archive contains historical data back to 1940.
    hourly_vars = [
        "temperature_2m",
        "relative_humidity_2m",
        "dew_point_2m",
        "apparent_temperature",
        "precipitation",
        "rain",
        "snowfall",
        "surface_pressure",
        "cloud_cover",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
        "shortwave_radiation",
    ]

    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "hourly": ",".join(hourly_vars),
        "timezone": "auto",
    }

    try:
        response = requests.get(OPEN_METEO_ARCHIVE_URL, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()

        if "hourly" in data:
            hourly_data = data["hourly"]
            df = pd.DataFrame(hourly_data)
            df["time"] = pd.to_datetime(df["time"])

            # Save metadata columns as info
            df["latitude"] = lat
            df["longitude"] = lon
            df["elevation"] = data.get("elevation", 0.0)

            # Save to cache
            df.to_csv(cache_path, index=False)
            logger.info(f"Successfully fetched and cached data to {cache_path}")
            return df
        else:
            logger.error("API response does not contain 'hourly' data.")
            return None
    except Exception as e:
        logger.error(f"Error fetching historical weather data: {str(e)}")
        return None


def fetch_realtime_forecast(lat: float, lon: float) -> Optional[Dict[str, Any]]:
    """
    Fetches real-time current weather conditions and 7-day forecast from Open-Meteo API.

    Args:
        lat: Latitude of the location.
        lon: Longitude of the location.

    Returns:
        A dictionary containing real-time weather and daily forecasts, or None if failed.
    """
    logger.info(f"Fetching real-time weather forecast for ({lat}, {lon})")
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,snowfall,weather_code,surface_pressure,wind_speed_10m,wind_direction_10m,is_day",
        "hourly": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation_probability,weather_code",
        "daily": "temperature_2m_max,temperature_2m_min,apparent_temperature_max,apparent_temperature_min,precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max",
        "timezone": "auto"
    }

    try:
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Error fetching real-time forecast: {str(e)}")
        return None
