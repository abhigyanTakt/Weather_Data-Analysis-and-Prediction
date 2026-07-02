"""
ClimaTrend Verification Script.
Tests the core data acquisition, cleaning, and model fitting steps.
"""

import os
import sys
import logging

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("verify")

def run_tests():
    logger.info("Starting ClimaTrend pipeline validation...")

    # 1. Imports
    try:
        from climatrend.src.data_acquisition import geocode_city, fetch_historical_weather
        from climatrend.src.data_cleaning import process_pipeline
        from climatrend.src.eda import generate_summary_statistics, perform_seasonal_decomposition
        from climatrend.src.forecasting_model import train_test_split_ts, fit_forecast_ml
        logger.info("Successfully imported all ClimaTrend modules.")
    except Exception as e:
        logger.error(f"Import failed: {str(e)}")
        sys.exit(1)

    # 2. Geocoding test
    logger.info("Testing geocoding function...")
    geo = geocode_city("London")
    if not geo or geo["lat"] is None or geo["lon"] is None:
        logger.error("Geocoding failed.")
        sys.exit(1)
    logger.info(f"Geocoding succeeded: {geo}")

    # 3. Weather Fetch test (5 days)
    logger.info("Testing weather data acquisition...")
    df_raw = fetch_historical_weather(
        geo["lat"], geo["lon"], "2025-06-01", "2025-06-05", city_name="London_Test"
    )
    if df_raw is None or df_raw.empty:
        logger.error("Failed to fetch historical weather data.")
        sys.exit(1)
    logger.info(f"Successfully fetched raw data. Shape: {df_raw.shape}")

    # 4. Cleaning & Aggregation test
    logger.info("Testing cleaning and aggregation pipeline...")
    df_hourly, df_daily = process_pipeline(df_raw)
    if df_hourly.empty or df_daily.empty:
        logger.error("Data processing pipeline returned empty DataFrames.")
        sys.exit(1)
    logger.info(f"Processed daily data. Daily shape: {df_daily.shape}")

    # 5. Summary Stats & Modeling test
    logger.info("Testing modeling feature generation and fitting...")
    train, test = train_test_split_ts(df_daily, test_size_days=1)
    # Fit simple ML model (Random Forest or Linear Regression)
    # Horizon is 2 days
    forecast_df, metrics = fit_forecast_ml(
        train, test, forecast_days=2, target_col="temperature_2m_mean", model_type="linear_regression"
    )
    if forecast_df.empty:
        logger.error("Forecasting model failed to return predictions.")
        sys.exit(1)
    logger.info(f"Model fit and forecasted successfully. Forecast shape: {forecast_df.shape}")
    logger.info(f"Validation Metrics: {metrics}")

    logger.info("✅ All core pipeline components verified successfully!")

if __name__ == "__main__":
    run_tests()
