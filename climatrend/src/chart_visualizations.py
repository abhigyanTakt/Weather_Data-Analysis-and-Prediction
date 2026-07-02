"""
ClimaTrend Chart Visualizations Module.

This module provides helper functions to generate beautiful, portfolio-quality
data visualizations including time series plots, seasonal decomposition, ACF/PACF,
correlation heatmaps, calendar heatmaps, box/violin distributions, and wind rose plots.
"""

import os
import logging
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.graph_objects as go
import plotly.express as px
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

# Configure seaborn aesthetics
sns.set_theme(style="whitegrid")
plt.rcParams.update({
    "font.size": 10,
    "axes.labelsize": 11,
    "axes.titlesize": 13,
    "xtick.labelsize": 9,
    "ytick.labelsize": 9,
    "figure.titlesize": 15,
})


def save_plot(fig: plt.Figure, filename: str, output_dir: str = "climatrend/outputs/charts") -> str:
    """
    Saves a Matplotlib figure to the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved plot to {path}")
    return path


def plot_time_series(df: pd.DataFrame, col: str, title: str = "Time Series Plot") -> plt.Figure:
    """
    Plots a simple time series line plot for a given column.
    """
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(df["time"], df[col], label=col, color="#2b5c8f", alpha=0.85, linewidth=1.5)
    ax.set_title(title)
    ax.set_xlabel("Time")
    ax.set_ylabel(col.replace("_", " ").title())
    ax.legend()
    fig.tight_layout()
    return fig


def plot_seasonal_decomposition(
    observed: pd.Series, trend: pd.Series, seasonal: pd.Series, resid: pd.Series
) -> plt.Figure:
    """
    Plots the seasonal decomposition (observed, trend, seasonality, residuals) of a time series.
    """
    fig, axes = plt.subplots(4, 1, figsize=(10, 8), sharex=True)

    axes[0].plot(observed.index, observed.values, color="#2b5c8f")
    axes[0].set_ylabel("Observed")
    axes[0].set_title("Seasonal Decomposition")

    axes[1].plot(trend.index, trend.values, color="#e07a5f")
    axes[1].set_ylabel("Trend")

    axes[2].plot(seasonal.index, seasonal.values, color="#81b29a")
    axes[2].set_ylabel("Seasonal")

    axes[3].scatter(resid.index, resid.values, color="#3d405b", s=2, alpha=0.5)
    axes[3].axhline(0, color="red", linestyle="--", linewidth=1)
    axes[3].set_ylabel("Residuals")

    for ax in axes:
        ax.grid(True, linestyle=":", alpha=0.6)

    fig.tight_layout()
    return fig


def plot_acf_pacf(acf_vals: np.ndarray, pacf_vals: np.ndarray) -> plt.Figure:
    """
    Plots Autocorrelation (ACF) and Partial Autocorrelation (PACF) values side-by-side.
    """
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    # ACF
    ax1.bar(range(len(acf_vals)), acf_vals, width=0.5, color="#2b5c8f")
    ax1.axhline(0, color="black", linestyle="-", linewidth=0.5)
    # Significance bounds (approximate 95% confidence interval)
    bound = 1.96 / np.sqrt(len(acf_vals) * 2)  # conservative estimate
    ax1.axhline(bound, color="red", linestyle="--", alpha=0.5)
    ax1.axhline(-bound, color="red", linestyle="--", alpha=0.5)
    ax1.set_title("Autocorrelation (ACF)")
    ax1.set_xlabel("Lags")
    ax1.set_ylabel("ACF")

    # PACF
    ax2.bar(range(len(pacf_vals)), pacf_vals, width=0.5, color="#e07a5f")
    ax2.axhline(0, color="black", linestyle="-", linewidth=0.5)
    ax2.axhline(bound, color="red", linestyle="--", alpha=0.5)
    ax2.axhline(-bound, color="red", linestyle="--", alpha=0.5)
    ax2.set_title("Partial Autocorrelation (PACF)")
    ax2.set_xlabel("Lags")
    ax2.set_ylabel("PACF")

    fig.tight_layout()
    return fig


def plot_correlation_heatmap(corr_df: pd.DataFrame) -> plt.Figure:
    """
    Generates a correlation heatmap for weather variables.
    """
    fig, ax = plt.subplots(figsize=(8, 6))

    # Replace column underscores with clean labels for display
    clean_cols = [c.replace("_", " ").title() for c in corr_df.columns]
    corr_display = corr_df.copy()
    corr_display.columns = clean_cols
    corr_display.index = clean_cols

    mask = np.triu(np.ones_like(corr_display, dtype=bool))
    sns.heatmap(
        corr_display,
        mask=mask,
        cmap="coolwarm",
        vmax=1.0,
        vmin=-1.0,
        center=0,
        square=True,
        linewidths=0.5,
        annot=True,
        fmt=".2f",
        cbar_kws={"shrink": 0.8},
        ax=ax,
    )
    ax.set_title("Correlation Heatmap of Weather Variables")
    fig.tight_layout()
    return fig


def plot_calendar_heatmap(df: pd.DataFrame, col: str = "temperature_2m_mean") -> plt.Figure:
    """
    Generates a monthly grid heatmap of weather variables (days on x-axis, month on y-axis)
    using pandas pivoting. This is robust and has no external package dependencies.
    """
    fig, ax = plt.subplots(figsize=(10, 5))

    df_heat = df.copy()
    df_heat["year"] = df_heat["time"].dt.year
    df_heat["month"] = df_heat["time"].dt.strftime("%b")
    df_heat["day"] = df_heat["time"].dt.day

    # Group by month and day, getting average over all years in dataset
    pivoted = df_heat.pivot_table(index="month", columns="day", values=col, aggfunc="mean")

    # Order months correctly
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    pivoted = pivoted.reindex(month_order)

    sns.heatmap(
        pivoted,
        cmap="YlOrRd",
        linewidths=0.2,
        cbar_kws={"label": col.replace("_", " ").title(), "shrink": 0.8},
        ax=ax,
    )

    ax.set_title(f"Calendar Heatmap: Average {col.replace('_', ' ').title()} by Day & Month")
    ax.set_xlabel("Day of Month")
    ax.set_ylabel("Month")
    fig.tight_layout()
    return fig


def plot_monthly_distribution(df: pd.DataFrame, col: str = "temperature_2m_mean") -> plt.Figure:
    """
    Plots the monthly temperature distribution using box/violin plots.
    """
    fig, ax = plt.subplots(figsize=(10, 4))

    df_dist = df.copy()
    df_dist["month"] = df_dist["time"].dt.strftime("%b")
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

    # Combined violin and boxplot (violin for shape, box for quartiles)
    sns.violinplot(
        x="month",
        y=col,
        data=df_dist,
        order=month_order,
        palette="crest",
        inner="quartile",
        ax=ax,
        hue="month",
        legend=False,
    )

    ax.set_title(f"Monthly Temperature Distribution ({col.replace('_', ' ').title()})")
    ax.set_xlabel("Month")
    ax.set_ylabel("Temperature (°C)")
    fig.tight_layout()
    return fig


def plot_bar_averages(df: pd.DataFrame, col: str = "precipitation_sum", freq: str = "yearly") -> plt.Figure:
    """
    Generates a bar chart of monthly or yearly averages.
    """
    fig, ax = plt.subplots(figsize=(10, 4))
    df_agg = df.copy()

    if freq == "yearly":
        df_agg["Year"] = df_agg["time"].dt.year
        data = df_agg.groupby("Year")[col].sum().reset_index()
        sns.barplot(x="Year", y=col, data=data, color="#81b29a", ax=ax)
        ax.set_title(f"Yearly Aggregated Sum: {col.replace('_', ' ').title()}")
        ax.set_ylabel("Total Sum")
    else:
        df_agg["Month"] = df_agg["time"].dt.strftime("%b")
        month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        data = df_agg.groupby("Month")[col].mean().reset_index()
        sns.barplot(x="Month", y=col, data=data, order=month_order, color="#f2cc8f", ax=ax)
        ax.set_title(f"Monthly Mean: {col.replace('_', ' ').title()}")
        ax.set_ylabel("Average")

    fig.tight_layout()
    return fig


def plot_scatter_correlation(df: pd.DataFrame, col1: str, col2: str) -> plt.Figure:
    """
    Plots a scatter plot of variable correlations (e.g. humidity vs temperature) with a regression line.
    """
    fig, ax = plt.subplots(figsize=(7, 5))
    sns.regplot(
        x=col1,
        y=col2,
        data=df,
        scatter_kws={"alpha": 0.4, "s": 10, "color": "#2b5c8f"},
        line_kws={"color": "red", "linewidth": 1.5},
        ax=ax,
    )

    ax.set_title(f"Correlation: {col1.replace('_', ' ').title()} vs {col2.replace('_', ' ').title()}")
    ax.set_xlabel(col1.replace("_", " ").title())
    ax.set_ylabel(col2.replace("_", " ").title())
    fig.tight_layout()
    return fig


def plot_wind_rose(df: pd.DataFrame) -> plt.Figure:
    """
    Generates a wind rose plot showing wind speed and direction.
    Uses standard Matplotlib polar projection.
    """
    fig = plt.figure(figsize=(6, 6))
    ax = fig.add_subplot(111, polar=True)

    # Filter wind columns
    speed_col = "wind_speed_10m_mean" if "wind_speed_10m_mean" in df.columns else "wind_speed_10m"
    dir_col = "wind_direction_10m_dominant" if "wind_direction_10m_dominant" in df.columns else "wind_direction_10m"

    if speed_col not in df.columns or dir_col not in df.columns:
        # Generate empty placeholder with note
        ax.text(0.5, 0.5, "Wind data not available", transform=ax.transAxes, ha="center", va="center")
        return fig

    # Drop nan values
    df_wind = df[[speed_col, dir_col]].dropna()

    # Bin directions into 8 sectors (N, NE, E, SE, S, SW, W, NW)
    num_sectors = 8
    theta = np.linspace(0.0, 2 * np.pi, num_sectors, endpoint=False)
    # Wind directions are in degrees (0-360), 0 is North.
    # Convert degrees to radians and adjust north to be 0
    rad_dir = np.deg2rad(df_wind[dir_col])

    # Bin directions
    bins = np.linspace(0, 2 * np.pi, num_sectors + 1)
    # Assign each direction to a bin index
    binned_dirs = np.digitize(rad_dir % (2 * np.pi), bins) - 1
    # Handle edge bin
    binned_dirs[binned_dirs == num_sectors] = 0

    # Categorize wind speeds into 4 groups
    speeds = df_wind[speed_col]
    speed_bins = [0, 5, 10, 20, np.inf]
    speed_colors = ["#ccece6", "#99d8c9", "#41ae76", "#08585e"]
    speed_labels = ["<5 km/h", "5-10 km/h", "10-20 km/h", ">20 km/h"]

    # Calculate frequencies for each sector and speed bin
    width = 2 * np.pi / num_sectors
    bottoms = np.zeros(num_sectors)

    for i in range(len(speed_bins) - 1):
        speed_mask = (speeds >= speed_bins[i]) & (speeds < speed_bins[i + 1])
        counts = []
        for sector in range(num_sectors):
            sector_mask = binned_dirs == sector
            counts.append(np.sum(speed_mask & sector_mask))

        counts = np.array(counts)
        # Convert count to percentage
        pct = (counts / len(df_wind)) * 100 if len(df_wind) > 0 else counts

        ax.bar(
            theta,
            pct,
            width=width * 0.85,
            bottom=bottoms,
            color=speed_colors[i],
            label=speed_labels[i],
            edgecolor="gray",
            linewidth=0.5,
        )
        bottoms += pct

    # Set cardinal labels
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)  # Clockwise
    ax.set_thetagrids(np.rad2deg(theta), labels=["N", "NE", "E", "SE", "S", "SW", "W", "NW"])
    ax.set_title("Wind Rose (Speed & Dominant Direction)", pad=15)
    ax.legend(loc="lower left", bbox_to_anchor=(1.1, 0.1))

    fig.tight_layout()
    return fig


def plot_forecast_plotly(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    target_col: str = "temperature_2m_mean",
    model_name: str = "Model",
) -> go.Figure:
    """
    Plots historical values alongside forecasted values with confidence interval bands using Plotly.
    Provides an interactive web-based output.
    """
    fig = go.Figure()

    # Historical data (last 365 days for readability)
    hist_plot = historical_df.tail(365)

    # 1. Historical line
    fig.add_trace(
        go.Scatter(
            x=hist_plot["time"],
            y=hist_plot[target_col],
            name="Historical (Last Year)",
            line=dict(color="rgb(43, 92, 143)", width=1.5),
            mode="lines",
        )
    )

    # 2. Forecast line
    fig.add_trace(
        go.Scatter(
            x=forecast_df["time"],
            y=forecast_df["forecast"],
            name=f"Forecast ({model_name})",
            line=dict(color="rgb(224, 122, 95)", width=2),
            mode="lines",
        )
    )

    # 3. Upper CI
    fig.add_trace(
        go.Scatter(
            x=forecast_df["time"],
            y=forecast_df["upper_ci"],
            name="Upper 95% Confidence",
            line=dict(color="rgba(224, 122, 95, 0)", width=0),
            showlegend=False,
            mode="lines",
        )
    )

    # 4. Lower CI (shaded fill area)
    fig.add_trace(
        go.Scatter(
            x=forecast_df["time"],
            y=forecast_df["lower_ci"],
            name="95% Confidence Band",
            fill="tonexty",
            fillcolor="rgba(224, 122, 95, 0.2)",
            line=dict(color="rgba(224, 122, 95, 0)", width=0),
            mode="lines",
        )
    )

    fig.update_layout(
        title=f"Time Series Forecast: {target_col.replace('_', ' ').title()}",
        xaxis_title="Date",
        yaxis_title="Value",
        hovermode="x unified",
        template="plotly_white",
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01),
        margin=dict(l=40, r=40, t=60, b=40),
    )

    return fig


def plot_forecast_matplotlib(
    historical_df: pd.DataFrame,
    forecast_df: pd.DataFrame,
    target_col: str = "temperature_2m_mean",
    model_name: str = "Model",
) -> plt.Figure:
    """
    Plots historical values alongside forecasted values with confidence interval bands using Matplotlib.
    """
    fig, ax = plt.subplots(figsize=(10, 4.5))

    # Last 365 days of history for clarity
    hist_plot = historical_df.tail(365)

    ax.plot(hist_plot["time"], hist_plot[target_col], label="Historical (Last Year)", color="#2b5c8f", alpha=0.85)
    ax.plot(forecast_df["time"], forecast_df["forecast"], label=f"Forecast ({model_name})", color="#e07a5f", linewidth=2)

    ax.fill_between(
        forecast_df["time"],
        forecast_df["lower_ci"],
        forecast_df["upper_ci"],
        color="#e07a5f",
        alpha=0.2,
        label="95% Confidence Band",
    )

    ax.set_title(f"{target_col.replace('_', ' ').title()} Forecast - {model_name}")
    ax.set_xlabel("Date")
    ax.set_ylabel("Value")
    ax.legend(loc="upper left")
    ax.grid(True, linestyle=":", alpha=0.6)

    fig.tight_layout()
    return fig


def plot_hourly_overview_chart(hourly_dict: dict, use_apparent: bool = False) -> go.Figure:
    """
    Generates a high-fidelity Plotly chart combining:
    1. A smooth temperature curve (spline) with gradient/glowing area fill.
    2. Sunrise and sunset markers on the curve.
    3. Bottom-aligned precipitation probability bar chart.
    Styled matching the dark navy Windows Weather App screenshot.
    """
    import plotly.graph_objects as go
    import pandas as pd

    # Parse hourly data
    df = pd.DataFrame(hourly_dict)
    # Get next 12 hours starting from now
    df = df.head(12).copy()

    # Format the hour labels (e.g. "Now", "9 PM", "11 PM", etc.)
    times = []
    for idx, t_str in enumerate(df["time"]):
        dt = pd.to_datetime(t_str)
        if idx == 0:
            times.append("Now")
        else:
            times.append(dt.strftime("%I %p").lstrip('0'))
    
    df["display_time"] = times
    
    # Select target temperature column
    temp_col = "apparent_temperature" if use_apparent else "temperature_2m"
    y_temp = df[temp_col].values
    y_prec = df["precipitation_probability"].values
    
    fig = go.Figure()
    
    # Temperature line with glowing spline
    fig.add_trace(
        go.Scatter(
            x=df["display_time"],
            y=y_temp,
            name="Temperature",
            mode="lines+markers+text",
            line=dict(shape="spline", color="#ffb703", width=3),
            marker=dict(size=8, color="#ffb703", symbol="circle"),
            text=[f"{round(val)}°" for val in y_temp],
            textposition="top center",
            textfont=dict(color="#f8fafc", size=12, family="Outfit, Inter, sans-serif"),
            yaxis="y1"
        )
    )
    
    # Semi-transparent area fill underneath the temperature curve
    fig.add_trace(
        go.Scatter(
            x=df["display_time"],
            y=y_temp,
            mode="lines",
            line=dict(width=0),
            fill="tozeroy",
            fillcolor="rgba(255, 183, 3, 0.12)",
            showlegend=False,
            hoverinfo="skip",
            yaxis="y1"
        )
    )
    
    # Precipitation probability bars (light blue)
    fig.add_trace(
        go.Bar(
            x=df["display_time"],
            y=y_prec,
            name="Precipitation %",
            marker=dict(
                color="rgba(56, 189, 248, 0.4)",
                line=dict(color="rgba(56, 189, 248, 0.8)", width=1.5)
            ),
            text=[f"{val}%" if val > 0 else "" for val in y_prec],
            textposition="auto",
            textfont=dict(color="#f8fafc", size=10),
            yaxis="y2"
        )
    )
    
    # Setup layout with dual Y-axes
    min_temp = min(y_temp)
    max_temp = max(y_temp)
    
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
        showlegend=False,
        hovermode="x unified",
        xaxis=dict(
            showgrid=False,
            zeroline=False,
            tickfont=dict(color="#94a3b8", size=11),
            type="category"
        ),
        yaxis=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[min_temp - 3, max_temp + 5]
        ),
        yaxis2=dict(
            showgrid=False,
            zeroline=False,
            showticklabels=False,
            range=[0, 300],
            overlaying="y",
            side="right"
        ),
        height=280
    )
    
    return fig


def plot_3d_weather_trends(df: pd.DataFrame) -> go.Figure:
    """
    Generates an interactive 3D scatter plot of weather variables:
    X: Mean Temperature
    Y: Relative Humidity
    Z: Wind Speed
    Color: Precipitation Sum
    """
    import plotly.graph_objects as go
    
    # Clean column names for display
    x_data = df["temperature_2m_mean"]
    y_data = df["relative_humidity_2m_mean"] if "relative_humidity_2m_mean" in df.columns else df["temperature_2m_max"]
    z_data = df["wind_speed_10m_mean"] if "wind_speed_10m_mean" in df.columns else df["wind_speed_10m_max"]
    c_data = df["precipitation_sum"] if "precipitation_sum" in df.columns else df["precipitation"]
    
    fig = go.Figure(data=[go.Scatter3d(
        x=x_data,
        y=y_data,
        z=z_data,
        mode='markers',
        marker=dict(
            size=6,
            color=c_data,
            colorscale='Viridis',
            opacity=0.8,
            colorbar=dict(title="Precip (mm)", thickness=15, len=0.6, tickfont=dict(color="#f8fafc")),
            showscale=True
        ),
        hovertemplate=(
            "Temp: %{x:.1f}°C<br>" +
            "Humidity: %{y:.1f}%<br>" +
            "Wind Speed: %{z:.1f} km/h<br>" +
            "Precip: %{marker.color:.1f} mm<extra></extra>"
        )
    )])
    
    fig.update_layout(
        title=dict(
            text="Interactive 3D Weather State Space",
            font=dict(color="#f8fafc", size=16)
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        scene=dict(
            xaxis=dict(
                title=dict(
                    text="Temperature (°C)",
                    font=dict(color="#38bdf8")
                ),
                backgroundcolor="rgba(12, 21, 36, 0.5)",
                gridcolor="#334155",
                showbackground=True,
                tickfont=dict(color="#94a3b8")
            ),
            yaxis=dict(
                title=dict(
                    text="Relative Humidity (%)",
                    font=dict(color="#38bdf8")
                ),
                backgroundcolor="rgba(12, 21, 36, 0.5)",
                gridcolor="#334155",
                showbackground=True,
                tickfont=dict(color="#94a3b8")
            ),
            zaxis=dict(
                title=dict(
                    text="Wind Speed (km/h)",
                    font=dict(color="#38bdf8")
                ),
                backgroundcolor="rgba(12, 21, 36, 0.5)",
                gridcolor="#334155",
                showbackground=True,
                tickfont=dict(color="#94a3b8")
            )
        ),
        margin=dict(l=0, r=0, b=0, t=40),
        height=500
    )
    return fig

