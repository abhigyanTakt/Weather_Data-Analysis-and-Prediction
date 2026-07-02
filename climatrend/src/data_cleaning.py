"""
ClimaTrend Data Cleaning and Processing Module.

This module provides functions to process raw hourly weather data, impute missing values,
detect outliers, calculate meteorological metrics (heat index, wind chill),
and resample data to daily, weekly, or monthly aggregations.
"""

import logging
import numpy as np
import pandas as pd
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def calculate_heat_index(temp_c: float, rh: float) -> float:
    """
    Calculates the Heat Index (feels like temperature for warm conditions) in Celsius.
    Uses the Rothfusz regression equation.

    Args:
        temp_c: Temperature in Celsius.
        rh: Relative humidity in percentage (0-100).

    Returns:
        The Heat Index in Celsius.
    """
    # Heat Index is only applicable for temperatures >= 26.7C (80F) and RH >= 40%
    if temp_c < 26.7 or rh < 40:
        return temp_c

    # Convert to Fahrenheit
    t = (temp_c * 9 / 5) + 32

    # Rothfusz regression formula
    hi_f = (
        -42.379
        + 2.04901523 * t
        + 10.14333127 * rh
        - 0.22475541 * t * rh
        - 0.00683783 * t * t
        - 0.05481717 * rh * rh
        + 0.00122874 * t * t * rh
        + 0.00085282 * t * rh * rh
        - 0.00000199 * t * t * rh * rh
    )

    # Convert back to Celsius
    return (hi_f - 32) * 5 / 9


def calculate_wind_chill(temp_c: float, wind_speed_kmh: float) -> float:
    """
    Calculates the Wind Chill index (feels like temperature for cold/windy conditions) in Celsius.
    Applicable for temperatures <= 10C and wind speeds > 4.8 km/h.

    Args:
        temp_c: Temperature in Celsius.
        wind_speed_kmh: Wind speed in km/h.

    Returns:
        The Wind Chill in Celsius.
    """
    # Wind chill is only defined for temperatures <= 10C and wind speed > 4.8 km/h (approx 3 mph)
    if temp_c > 10.0 or wind_speed_kmh <= 4.8:
        return temp_c

    # Wind chill formula (standard US/Canadian/UK meteorological formula in Metric)
    wc = (
        13.12
        + 0.6215 * temp_c
        - 11.37 * (wind_speed_kmh**0.16)
        + 0.3965 * temp_c * (wind_speed_kmh**0.16)
    )
    return wc


def impute_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """
    Imputes missing values in the weather DataFrame using linear interpolation.

    Args:
        df: Input DataFrame.

    Returns:
        DataFrame with missing values filled.
    """
    df_clean = df.copy()

    # Log missing count
    null_counts = df_clean.isnull().sum()
    if null_counts.sum() > 0:
        logger.info(f"Missing values found before imputation:\n{null_counts[null_counts > 0]}")

        # Interpolate numeric columns, limit to filling forward/backward for edges
        numeric_cols = df_clean.select_dtypes(include=[np.number]).columns
        df_clean[numeric_cols] = df_clean[numeric_cols].interpolate(method="linear", limit_direction="both")

        # Fill remaining if any (e.g. non-numeric or edge cases)
        df_clean = df_clean.ffill().bfill()
        logger.info("Imputation completed via linear interpolation.")
    else:
        logger.info("No missing values detected.")

    return df_clean


def handle_outliers(df: pd.DataFrame, col: str, threshold: float = 3.0) -> pd.DataFrame:
    """
    Detects and handles outliers in a column using the Z-score method.
    Outliers are capped at the threshold value rather than deleted, to preserve time continuity.

    Args:
        df: Input DataFrame.
        col: Target column name.
        threshold: Z-score threshold (default 3.0).

    Returns:
        DataFrame with capped outliers.
    """
    df_clean = df.copy()
    if col not in df_clean.columns:
        return df_clean

    mean = df_clean[col].mean()
    std = df_clean[col].std()

    if std == 0:
        return df_clean

    # Calculate z-scores
    z_scores = (df_clean[col] - mean) / std

    # Identify outliers
    outliers = df_clean[np.abs(z_scores) > threshold]
    if len(outliers) > 0:
        logger.info(f"Detected {len(outliers)} outliers in column '{col}' using threshold Z={threshold}")
        # Cap values
        upper_limit = mean + threshold * std
        lower_limit = mean - threshold * std
        df_clean[col] = np.clip(df_clean[col], lower_limit, upper_limit)
        logger.info(f"Capped outliers in '{col}' to range [{lower_limit:.2f}, {upper_limit:.2f}]")

    return df_clean


def clean_hourly_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans raw hourly data, handles missing values, detects and handles outliers
    in temperature/humidity, and computes secondary metrics.

    Args:
        df: Raw hourly weather DataFrame.

    Returns:
        Cleaned hourly DataFrame.
    """
    logger.info("Starting hourly data cleaning process...")

    # Step 1: Ensure time column is parsed and index is set
    df_clean = df.copy()
    if "time" in df_clean.columns:
        df_clean["time"] = pd.to_datetime(df_clean["time"])
    else:
        raise ValueError("DataFrame must contain a 'time' column.")

    # Sort by time to ensure order
    df_clean = df_clean.sort_values("time").reset_index(drop=True)

    # Step 2: Impute missing values
    df_clean = impute_missing_values(df_clean)

    # Step 3: Handle outliers in critical columns
    for col in ["temperature_2m", "relative_humidity_2m", "surface_pressure", "wind_speed_10m"]:
        if col in df_clean.columns:
            df_clean = handle_outliers(df_clean, col)

    # Step 4: Calculate custom feels-like temperature metrics (Heat Index / Wind Chill)
    # apparent_temperature is provided by Open-Meteo, but we compute feels_like
    # to demonstrate custom meteorological formula application.
    if "temperature_2m" in df_clean.columns and "relative_humidity_2m" in df_clean.columns:
        feels_like_list = []
        for _, row in df_clean.iterrows():
            temp = row["temperature_2m"]
            rh = row["relative_humidity_2m"]
            wind = row.get("wind_speed_10m", 0.0)

            # Check which index to apply
            if temp >= 26.7:
                feels_like = calculate_heat_index(temp, rh)
            elif temp <= 10.0 and wind > 0:
                feels_like = calculate_wind_chill(temp, wind)
            else:
                feels_like = temp
            feels_like_list.append(feels_like)

        df_clean["feels_like"] = feels_like_list
    else:
        # Fallback to apparent_temperature if available, else copy temperature
        df_clean["feels_like"] = df_clean.get("apparent_temperature", df_clean.get("temperature_2m", 0.0))

    logger.info("Hourly data cleaning completed successfully.")
    return df_clean


def aggregate_to_daily(df_hourly: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregates hourly cleaned data to daily frequency.

    Args:
        df_hourly: Cleaned hourly weather DataFrame.

    Returns:
        Daily aggregated DataFrame.
    """
    logger.info("Aggregating hourly data to daily frequency...")

    # We group by the date component of the 'time' column
    df = df_hourly.copy()
    df["date"] = df["time"].dt.date

    # Define standard aggregation functions for weather parameters
    # Using trig averages for wind direction
    rad = np.deg2rad(df["wind_direction_10m"])
    df["wind_sin"] = np.sin(rad)
    df["wind_cos"] = np.cos(rad)

    agg_dict = {
        "temperature_2m": ["mean", "min", "max"],
        "feels_like": ["mean", "min", "max"],
        "relative_humidity_2m": "mean",
        "dew_point_2m": "mean",
        "precipitation": "sum",
        "rain": "sum",
        "snowfall": "sum",
        "surface_pressure": "mean",
        "cloud_cover": "mean",
        "wind_speed_10m": ["mean", "max"],
        "wind_gusts_10m": "max",
        "shortwave_radiation": "sum",
        "wind_sin": "mean",
        "wind_cos": "mean",
        "latitude": "first",
        "longitude": "first",
        "elevation": "first",
    }

    # Keep only columns that exist
    actual_agg = {col: agg_dict[col] for col in agg_dict if col in df.columns}

    # Aggregate
    df_daily = df.groupby("date").agg(actual_agg)

    # Flatten multi-index columns
    flat_cols = []
    for col in df_daily.columns:
        if isinstance(col, tuple):
            if col[1] == "first":
                flat_cols.append(col[0])
            else:
                flat_cols.append(f"{col[0]}_{col[1]}")
        else:
            flat_cols.append(col)
    df_daily.columns = flat_cols

    # Reconstruct wind direction from average sine and cosine components
    if "wind_sin_mean" in df_daily.columns and "wind_cos_mean" in df_daily.columns:
        avg_rad = np.arctan2(df_daily["wind_sin_mean"], df_daily["wind_cos_mean"])
        df_daily["wind_direction_10m_dominant"] = np.rad2deg(avg_rad) % 360
        df_daily = df_daily.drop(columns=["wind_sin_mean", "wind_cos_mean"])

    # Reset index and convert date to datetime
    df_daily = df_daily.reset_index()
    df_daily["date"] = pd.to_datetime(df_daily["date"])
    df_daily = df_daily.rename(columns={"date": "time"})

    logger.info(f"Aggregation complete. Output shape: {df_daily.shape}")
    return df_daily


def process_pipeline(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Runs the complete cleaning and aggregation pipeline.

    Args:
        df_raw: Raw weather DataFrame.

    Returns:
        A tuple of (cleaned_hourly_df, daily_aggregated_df).
    """
    df_hourly = clean_hourly_data(df_raw)
    df_daily = aggregate_to_daily(df_hourly)
    return df_hourly, df_daily
