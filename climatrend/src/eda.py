"""
ClimaTrend Exploratory Data Analysis (EDA) Module.

This module provides utility functions for statistical summaries, seasonal decomposition,
correlation analysis, and autocorrelation calculations for meteorological data.
"""

import logging
from typing import Dict, Any, Tuple
import numpy as np
import pandas as pd
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import acf, pacf

logger = logging.getLogger(__name__)


def generate_summary_statistics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generates descriptive statistics for weather variables in the DataFrame.

    Args:
        df: Daily aggregated weather DataFrame.

    Returns:
        DataFrame containing summary statistics.
    """
    logger.info("Generating summary statistics...")
    cols_to_summarize = [
        col
        for col in df.columns
        if col
        not in [
            "time",
            "latitude",
            "longitude",
            "elevation",
            "wind_direction_10m_dominant",
        ]
    ]

    summary = df[cols_to_summarize].describe().transpose()
    # Add skewness and kurtosis
    summary["skewness"] = df[cols_to_summarize].skew()
    summary["kurtosis"] = df[cols_to_summarize].kurtosis()

    return summary


def perform_seasonal_decomposition(
    df: pd.DataFrame, target_col: str = "temperature_2m_mean", period: int = 365
) -> Tuple[pd.Series, pd.Series, pd.Series, pd.Series]:
    """
    Decomposes the time series into trend, seasonal, and residual components.

    Args:
        df: Daily aggregated weather DataFrame with a datetime index or time column.
        target_col: Column to decompose.
        period: Period for seasonal decomposition (default 365 for daily data).

    Returns:
        A tuple of (observed, trend, seasonal, residual) as pandas Series.
    """
    logger.info(f"Performing seasonal decomposition on '{target_col}' with period {period}...")

    # Ensure time is index and sorted
    df_temp = df.copy()
    if "time" in df_temp.columns:
        df_temp = df_temp.set_index("time")
    df_temp = df_temp.sort_index()

    # Need to handle missing values by filling them (should be clean already)
    series = df_temp[target_col].ffill().bfill()

    # If the series length is less than 2 * period, statsmodels seasonal_decompose will fail.
    # In that case, we fall back to a smaller period or a simple moving average.
    if len(series) < 2 * period:
        logger.warning(
            f"Series length ({len(series)}) is too short for seasonal decomposition with period {period}."
            f" Falling back to period={min(len(series)//2 - 1, 30)}"
        )
        period = max(7, min(len(series) // 2 - 1, 30))

    try:
        result = seasonal_decompose(series, model="additive", period=period, extrapolate_trend="freq")
        return result.observed, result.trend, result.seasonal, result.resid
    except Exception as e:
        logger.error(f"Error in seasonal decomposition: {str(e)}")
        # Fallback manual decomposition: trend = rolling mean, seasonal = 0, residual = observed - trend
        trend = series.rolling(window=period, center=True, min_periods=1).mean()
        residual = series - trend
        seasonal = pd.Series(0.0, index=series.index)
        return series, trend, seasonal, residual


def compute_acf_pacf(
    df: pd.DataFrame, target_col: str = "temperature_2m_mean", nlags: int = 40
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Computes Autocorrelation Function (ACF) and Partial Autocorrelation Function (PACF).

    Args:
        df: Weather DataFrame.
        target_col: Target column name.
        nlags: Number of lags to compute.

    Returns:
        A tuple of (acf_values, pacf_values) as numpy arrays.
    """
    logger.info(f"Computing ACF and PACF for '{target_col}' up to {nlags} lags...")

    df_temp = df.copy()
    if "time" in df_temp.columns:
        df_temp = df_temp.set_index("time")
    df_temp = df_temp.sort_index()

    series = df_temp[target_col].ffill().bfill()

    # Adjust nlags if series is too short
    actual_lags = min(nlags, len(series) // 2 - 1)

    acf_vals = acf(series, nlags=actual_lags, fft=True)
    pacf_vals = pacf(series, nlags=actual_lags, method="yw")

    return acf_vals, pacf_vals


def calculate_correlations(df: pd.DataFrame) -> pd.DataFrame:
    """
    Calculates the Pearson correlation matrix for numerical weather variables.

    Args:
        df: Weather DataFrame.

    Returns:
        Correlation matrix as a DataFrame.
    """
    logger.info("Calculating variable correlation matrix...")
    cols_to_correlate = [
        col
        for col in df.columns
        if col
        not in [
            "time",
            "latitude",
            "longitude",
            "elevation",
            "wind_direction_10m_dominant",
        ]
    ]

    return df[cols_to_correlate].corr()
