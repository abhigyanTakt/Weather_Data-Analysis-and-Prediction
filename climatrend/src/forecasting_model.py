"""
ClimaTrend Forecasting Model Module.

This module implements time-series forecasting models including Prophet,
SARIMA/ARIMA, and machine learning regressors (Linear Regression and Random Forest)
using lag and rolling features with recursive forecasting.
"""

import logging
from typing import Tuple, Dict, Any, List, Optional
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.statespace.sarimax import SARIMAX

logger = logging.getLogger(__name__)


def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """
    Calculates Mean Absolute Percentage Error.

    Args:
        y_true: True values.
        y_pred: Predicted values.

    Returns:
        MAPE as a percentage (0-100).
    """
    mask = y_true != 0
    if not np.any(mask):
        return 0.0
    return np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100


def evaluate_forecast(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Evaluates forecasting performance using MAE, RMSE, and MAPE.

    Args:
        y_true: True values.
        y_pred: Predicted values.

    Returns:
        Dictionary containing MAE, RMSE, and MAPE.
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    mape = calculate_mape(y_true, y_pred)

    return {"MAE": float(mae), "RMSE": float(rmse), "MAPE": float(mape)}


def train_test_split_ts(df: pd.DataFrame, test_size_days: int = 30) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits a time-series DataFrame into train and test sets sequentially.

    Args:
        df: Input DataFrame.
        test_size_days: Number of days to include in the test set.

    Returns:
        A tuple of (train_df, test_df).
    """
    df_sorted = df.sort_values("time").reset_index(drop=True)
    split_idx = len(df_sorted) - test_size_days

    # Ensure train set is not empty
    if split_idx <= 0:
        split_idx = int(len(df_sorted) * 0.8)

    train_df = df_sorted.iloc[:split_idx].copy()
    test_df = df_sorted.iloc[split_idx:].copy()

    logger.info(f"Split data into train (shape: {train_df.shape}) and test (shape: {test_df.shape})")
    return train_df, test_df


def fit_forecast_prophet(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    forecast_days: int,
    target_col: str = "temperature_2m_mean",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Fits Facebook Prophet model and forecasts future values.

    Args:
        train_df: Training DataFrame.
        test_df: Testing DataFrame (for validation metrics).
        forecast_days: Number of days to forecast.
        target_col: The target weather variable.

    Returns:
        A tuple containing the forecast DataFrame (with time, yhat, yhat_lower, yhat_upper)
        and validation metrics.
    """
    # Import Prophet inside function to handle missing installations gracefully
    try:
        from prophet import Prophet
    except ImportError:
        logger.error("Prophet package is not installed. Returning empty forecast.")
        return pd.DataFrame(), {}

    logger.info(f"Fitting Prophet model on '{target_col}'...")

    # Prophet requires columns 'ds' and 'y'
    prophet_train = train_df[["time", target_col]].rename(columns={"time": "ds", target_col: "y"})

    # Initialize model with standard yearly and weekly seasonality
    model = Prophet(
        yearly_seasonality=True,
        weekly_seasonality=True,
        daily_seasonality=False,
        interval_width=0.95,  # 95% confidence intervals
    )

    model.fit(prophet_train)

    # Create future dataframe
    steps = max(len(test_df), forecast_days)
    future = model.make_future_dataframe(periods=steps, freq="D")
    forecast_all = model.predict(future)

    # Extract target forecast range corresponding to test_df + future
    # Let's align with the length of test_df + the extra forecast horizon
    # Or just return the entire forecast
    forecast_out = forecast_all[["ds", "yhat", "yhat_lower", "yhat_upper"]].rename(
        columns={"ds": "time", "yhat": "forecast", "yhat_lower": "lower_ci", "yhat_upper": "upper_ci"}
    )

    # Evaluate on test set
    test_dates = test_df["time"].values
    forecast_test = forecast_out[forecast_out["time"].isin(test_dates)]

    metrics = {}
    if not forecast_test.empty and len(forecast_test) == len(test_df):
        metrics = evaluate_forecast(test_df[target_col].values, forecast_test["forecast"].values)
        logger.info(f"Prophet Test Metrics: {metrics}")
    else:
        logger.warning("Could not align Prophet forecast with test set for evaluation.")

    return forecast_out, metrics


def fit_forecast_sarima(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    forecast_days: int,
    target_col: str = "temperature_2m_mean",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Fits SARIMAX/ARIMA model and forecasts future values.
    Uses pmdarima for auto-selection if available, else a fast default configuration.

    Args:
        train_df: Training DataFrame.
        test_df: Testing DataFrame.
        forecast_days: Number of days to forecast.
        target_col: The target weather variable.

    Returns:
        A tuple containing the forecast DataFrame and validation metrics.
    """
    logger.info(f"Fitting SARIMA model on '{target_col}'...")

    train_series = train_df.set_index("time")[target_col].asfreq("D").ffill().bfill()
    test_len = len(test_df)

    # Attempt auto_arima or fallback to default
    order = (1, 1, 1)
    seasonal_order = (1, 0, 1, 7)  # weekly seasonality (7 days)

    try:
        from pmdarima import auto_arima

        logger.info("Running auto_arima to select optimal order parameters...")
        # Restrict parameters for speed; search takes too long otherwise on long daily series
        # We downsample search or restrict max_p, max_q
        stepwise_model = auto_arima(
            train_series,
            start_p=1,
            start_q=1,
            max_p=3,
            max_q=3,
            m=7,  # weekly seasonality
            seasonal=True,
            d=1,
            D=1,
            trace=False,
            error_action="ignore",
            suppress_warnings=True,
            stepwise=True,
            max_iter=20,
        )
        order = stepwise_model.order
        seasonal_order = stepwise_model.seasonal_order
        logger.info(f"Selected ARIMA order: {order}, seasonal order: {seasonal_order}")
    except Exception as e:
        logger.warning(f"Failed to run auto_arima: {str(e)}. Using default order {order} and seasonal_order {seasonal_order}")

    try:
        # Fit SARIMAX
        model = SARIMAX(
            train_series,
            order=order,
            seasonal_order=seasonal_order,
            enforce_stationarity=False,
            enforce_invertibility=False,
        )
        results = model.fit(disp=False)

        # Forecast
        steps = max(test_len, forecast_days)
        forecast_res = results.get_forecast(steps=steps)

        # Build dates for forecast index
        last_date = train_df["time"].max()
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=steps, freq="D")

        forecast_mean = forecast_res.predicted_mean
        conf_int = forecast_res.conf_int(alpha=0.05)  # 95% CI

        forecast_df = pd.DataFrame(
            {
                "time": forecast_dates,
                "forecast": forecast_mean.values,
                "lower_ci": conf_int.iloc[:, 0].values,
                "upper_ci": conf_int.iloc[:, 1].values,
            }
        )

        # Evaluate on test set
        y_true = test_df[target_col].values
        # Match test size
        y_pred = forecast_df.iloc[:test_len]["forecast"].values
        metrics = evaluate_forecast(y_true, y_pred)
        logger.info(f"SARIMA Test Metrics: {metrics}")

        return forecast_df, metrics
    except Exception as e:
        logger.error(f"Error fitting SARIMA: {str(e)}")
        # Simple mean fallback
        last_date = train_df["time"].max()
        steps = test_len + (forecast_days - test_len)
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=steps, freq="D")
        mean_val = train_series.mean()
        forecast_df = pd.DataFrame(
            {
                "time": forecast_dates,
                "forecast": [mean_val] * steps,
                "lower_ci": [mean_val - 2 * train_series.std()] * steps,
                "upper_ci": [mean_val + 2 * train_series.std()] * steps,
            }
        )
        return forecast_df, {}


def _create_ml_features(df: pd.DataFrame, target_col: str) -> pd.DataFrame:
    """
    Creates lags, rolling statistics, and calendar features for ML models.
    """
    df_feat = df.copy()
    if "time" in df_feat.columns:
        df_feat["date_col"] = df_feat["time"]
    else:
        df_feat["date_col"] = df_feat.index

    # Calendar features
    df_feat["month"] = df_feat["date_col"].dt.month
    df_feat["dayofyear"] = df_feat["date_col"].dt.dayofyear
    df_feat["sin_dayofyear"] = np.sin(2 * np.pi * df_feat["dayofyear"] / 365.25)
    df_feat["cos_dayofyear"] = np.cos(2 * np.pi * df_feat["dayofyear"] / 365.25)

    # Lag features
    for lag in [1, 2, 7, 30, 365]:
        df_feat[f"lag_{lag}"] = df_feat[target_col].shift(lag)

    # Rolling features
    df_feat["rolling_mean_7"] = df_feat[target_col].shift(1).rolling(window=7).mean()
    df_feat["rolling_mean_30"] = df_feat[target_col].shift(1).rolling(window=30).mean()

    # Drop intermediate columns
    df_feat = df_feat.drop(columns=["date_col"])

    return df_feat


def fit_forecast_ml(
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    forecast_days: int,
    target_col: str = "temperature_2m_mean",
    model_type: str = "random_forest",
) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """
    Fits a Machine Learning Regressor (Linear Regression or Random Forest)
    and forecasts future values recursively to support multi-step forecasting.

    Args:
        train_df: Training DataFrame.
        test_df: Testing DataFrame.
        forecast_days: Total forecast horizon (includes test_df length).
        target_col: Target weather variable.
        model_type: Either 'random_forest' or 'linear_regression'.

    Returns:
        A tuple of (forecast_df, validation_metrics).
    """
    logger.info(f"Fitting ML Regressor ({model_type}) on '{target_col}'...")

    # Combine data to create features with correct time alignment
    full_df = pd.concat([train_df, test_df]).sort_values("time").reset_index(drop=True)
    full_feat = _create_ml_features(full_df, target_col)

    # Split back into train
    train_feat = full_feat.iloc[: len(train_df)].copy()

    # Identify feature columns
    feature_cols = [
        col
        for col in train_feat.columns
        if col.startswith("lag_")
        or col.startswith("rolling_")
        or col in ["month", "sin_dayofyear", "cos_dayofyear"]
    ]

    # Fill NaNs in features (important for short datasets or early rows)
    train_feat[feature_cols] = train_feat[feature_cols].bfill().ffill().fillna(0.0)

    # Drop rows only if the target is NaN
    train_feat = train_feat.dropna(subset=[target_col])

    X_train = train_feat[feature_cols]
    y_train = train_feat[target_col]

    # Select model
    if model_type == "random_forest":
        model = RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=-1)
    else:
        model = LinearRegression()

    model.fit(X_train, y_train)

    # Perform recursive multi-step forecasting
    # We will forecast one step at a time, appending predictions to update lags/rolling statistics.
    history_df = full_df.iloc[: len(train_df)].copy()
    last_date = history_df["time"].max()

    steps = max(len(test_df), forecast_days)
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=steps, freq="D")

    predictions = []

    for i in range(steps):
        # Create a single-row DataFrame for the next date to generate features
        next_date = forecast_dates[i]
        next_row = pd.DataFrame({"time": [next_date], target_col: [np.nan]})

        # Append to history temporarily
        temp_history = pd.concat([history_df, next_row]).sort_values("time").reset_index(drop=True)
        temp_feat = _create_ml_features(temp_history, target_col)

        # Handle NaNs in features (important for short datasets or early rows)
        temp_feat[feature_cols] = temp_feat[feature_cols].bfill().ffill().fillna(0.0)

        # Get the feature values for the last row (our target forecast step)
        X_next = temp_feat.iloc[-1:][feature_cols]

        # Predict
        pred_val = model.predict(X_next)[0]
        predictions.append(pred_val)

        # Update the target column in history so it can be used for future lags
        history_df = pd.concat(
            [history_df, pd.DataFrame({"time": [next_date], target_col: [pred_val]})]
        ).reset_index(drop=True)

    # Calculate standard intervals using residuals standard deviation
    residuals = y_train - model.predict(X_train)
    resid_std = np.std(residuals)

    forecast_df = pd.DataFrame(
        {
            "time": forecast_dates,
            "forecast": predictions,
            "lower_ci": np.array(predictions) - 1.96 * resid_std,
            "upper_ci": np.array(predictions) + 1.96 * resid_std,
        }
    )

    # Evaluate
    test_len = len(test_df)
    y_true = test_df[target_col].values
    y_pred = forecast_df.iloc[:test_len]["forecast"].values
    metrics = evaluate_forecast(y_true, y_pred)
    logger.info(f"ML ({model_type}) Test Metrics: {metrics}")

    return forecast_df, metrics
