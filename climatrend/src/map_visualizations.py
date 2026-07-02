"""
ClimaTrend Map Visualizations Module.

This module provides helper functions to generate beautiful weather maps, including
static country-level choropleth maps, interactive Folium heatmaps, and spatial
contour plots representing temperature gradients.
"""

import os
import logging
import requests
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import folium
from folium.plugins import HeatMap
from typing import Optional, List, Tuple

logger = logging.getLogger(__name__)


def save_map(fig: plt.Figure, filename: str, output_dir: str = "climatrend/outputs/maps") -> str:
    """
    Saves a Matplotlib map figure to the output directory.
    """
    os.makedirs(output_dir, exist_ok=True)
    path = os.path.join(output_dir, filename)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    logger.info(f"Saved map to {path}")
    return path


def plot_static_choropleth(
    city_data_df: pd.DataFrame,
    val_col: str = "temperature_2m_mean",
    title: str = "Global Temperature Choropleth Map",
) -> plt.Figure:
    """
    Plots a static choropleth map using Geopandas.
    Binds country codes or coordinates to world boundaries.

    Args:
        city_data_df: DataFrame containing at least 'country', 'latitude', 'longitude', and the value column.
        val_col: Column to color.
        title: Title of the map.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(12, 6))

    try:
        import geopandas as gpd

        # Fetch world borders GeoJSON from a reliable public URL to avoid path issues
        world_geojson_url = "https://raw.githubusercontent.com/python-visualization/folium/master/examples/data/world-countries.json"
        logger.info(f"Loading world boundaries from {world_geojson_url}")

        world = gpd.read_file(world_geojson_url)

        # Let's map our cities to countries
        # Average the values per country
        country_avg = city_data_df.groupby("country")[val_col].mean().reset_index()

        # Merge with geopandas dataframe. Note: world has 'name' which is country name.
        # Geopandas 'name' might have slight differences from geocoding countries.
        # Clean country names for matching
        country_avg["country_clean"] = country_avg["country"].str.lower().str.strip()
        world["name_clean"] = world["name"].str.lower().str.strip()

        # Handle common naming mismatches
        name_mapping = {
            "united states of america": "united states",
            "united kingdom": "united kingdom",
            "russian federation": "russia",
        }
        world["name_clean"] = world["name_clean"].replace(name_mapping)

        merged = world.merge(country_avg, left_on="name_clean", right_on="country_clean", how="left")

        # Plot world background in light grey for missing data
        world.plot(ax=ax, color="#e0e0e0", edgecolor="white", linewidth=0.5)

        # Plot data
        merged.dropna(subset=[val_col]).plot(
            column=val_col,
            ax=ax,
            cmap="OrRd",
            legend=True,
            legend_kwds={"label": val_col.replace("_", " ").title(), "shrink": 0.5},
            edgecolor="white",
            linewidth=0.5,
        )

        ax.set_title(title)
        ax.axis("off")

    except Exception as e:
        logger.warning(f"Geopandas choropleth failed: {str(e)}. Falling back to simple scatter map.")
        # Fallback to simple coordinates scatter plot over raw outline if geopandas fails
        ax.set_facecolor("#e0f2fe")
        scatter = ax.scatter(
            city_data_df["longitude"],
            city_data_df["latitude"],
            c=city_data_df[val_col],
            cmap="OrRd",
            s=city_data_df[val_col].abs() * 5 + 20,
            edgecolors="black",
            linewidth=0.5,
            alpha=0.8,
        )
        # Draw basic grids
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.set_xlim(-180, 180)
        ax.set_ylim(-90, 90)
        fig.colorbar(scatter, label=val_col.replace("_", " ").title(), shrink=0.5, ax=ax)
        ax.set_title(f"{title} (Points Fallback)")

    fig.tight_layout()
    return fig


def plot_interactive_folium_heatmap(
    city_data_df: pd.DataFrame,
    val_col: str = "temperature_2m_mean",
) -> folium.Map:
    """
    Generates an interactive Folium Map with the HeatMap plugin.

    Args:
        city_data_df: DataFrame with 'latitude', 'longitude', and the value column.
        val_col: Column to use for heat intensity.

    Returns:
        Folium Map object.
    """
    logger.info("Generating Folium interactive heatmap...")

    # Clean data (no NaNs)
    df_clean = city_data_df.dropna(subset=["latitude", "longitude", val_col])

    # Center map near average coords
    avg_lat = df_clean["latitude"].mean() if not df_clean.empty else 20.0
    avg_lon = df_clean["longitude"].mean() if not df_clean.empty else 0.0

    m = folium.Map(location=[avg_lat, avg_lon], zoom_start=2, tiles="CartoDB positron")

    # Prepare data points for HeatMap plugin: [[lat, lon, weight], ...]
    # Normalize weights between 0 and 1 for better rendering
    max_val = df_clean[val_col].max()
    min_val = df_clean[val_col].min()
    range_val = max_val - min_val if max_val != min_val else 1.0

    heat_data = []
    for _, row in df_clean.iterrows():
        # Normalize weight
        weight = (row[val_col] - min_val) / range_val
        heat_data.append([row["latitude"], row["longitude"], weight])

    # Add heatmap layer
    HeatMap(heat_data, radius=25, blur=15, max_zoom=1).add_to(m)

    # Add markers for reference with labels
    for _, row in df_clean.iterrows():
        folium.CircleMarker(
            location=[row["latitude"], row["longitude"]],
            radius=4,
            popup=f"<b>{row.get('name', 'Station')}</b><br>{val_col.replace('_', ' ').title()}: {row[val_col]:.2f}",
            color="crimson",
            fill=True,
            fill_color="crimson",
            fill_opacity=0.6,
        ).add_to(m)

    return m


def plot_contour_gradient(
    city_data_df: pd.DataFrame,
    val_col: str = "temperature_2m_mean",
    title: str = "Temperature Contour Map",
) -> plt.Figure:
    """
    Plots a contour map representing weather variable gradients.
    Tries Cartopy first for proper map projections. If Cartopy is not available,
    it falls back to Matplotlib's tricontourf interpolation over scatter.

    Args:
        city_data_df: DataFrame with 'latitude', 'longitude', and the value column.
        val_col: Column to map.
        title: Title of the contour map.

    Returns:
        Matplotlib Figure.
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    # Drop NaNs
    df_clean = city_data_df.dropna(subset=["latitude", "longitude", val_col])

    if len(df_clean) < 4:
        # Interpolation needs at least 4 points
        ax.text(0.5, 0.5, "Not enough data points for contour map", transform=ax.transAxes, ha="center", va="center")
        return fig

    # Separate coords and values
    x = df_clean["longitude"].values
    y = df_clean["latitude"].values
    z = df_clean[val_col].values

    try:
        # Try importing cartopy
        import cartopy.crs as ccrs
        import cartopy.feature as cfeature

        # Re-create figure with Cartopy projection
        plt.close(fig)
        fig = plt.figure(figsize=(10, 6))
        ax = fig.add_subplot(1, 1, 1, projection=ccrs.PlateCarree())

        # Add coastlines and borders
        ax.add_feature(cfeature.LAND, facecolor="#f5f5f5")
        ax.add_feature(cfeature.OCEAN, facecolor="#e0f2fe")
        ax.add_feature(cfeature.COASTLINE, edgecolor="gray", linewidth=0.5)
        ax.add_feature(cfeature.BORDERS, edgecolor="lightgray", linewidth=0.5)

        # Plot contours
        # We use tricontourf as our cities represent irregular points on a grid
        cf = ax.tricontourf(x, y, z, transform=ccrs.PlateCarree(), cmap="coolwarm", alpha=0.7, levels=14)
        fig.colorbar(cf, label=val_col.replace("_", " ").title(), shrink=0.5, ax=ax)

        # Plot points on top
        ax.scatter(x, y, transform=ccrs.PlateCarree(), color="black", s=8, alpha=0.6)

        ax.set_title(title)

    except Exception as e:
        logger.warning(f"Cartopy contour map failed: {str(e)}. Falling back to Matplotlib tricontourf.")
        # Fallback to standard matplotlib tricontourf (no map projections)
        cf = ax.tricontourf(x, y, z, cmap="coolwarm", alpha=0.7, levels=14)
        fig.colorbar(cf, label=val_col.replace("_", " ").title(), shrink=0.5, ax=ax)

        # Plot city locations as dots
        ax.scatter(x, y, color="black", s=15, edgecolor="white", label="Weather Station")
        # Annotate city names
        for _, row in df_clean.iterrows():
            ax.annotate(
                row.get("name", ""),
                (row["longitude"], row["latitude"]),
                textcoords="offset points",
                xytext=(0, 5),
                ha="center",
                fontsize=7,
                alpha=0.8,
            )

        ax.set_title(f"{title} (Interpolated Gradient)")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.grid(True, linestyle=":", alpha=0.5)
        ax.legend(loc="lower left")

    fig.tight_layout()
    return fig
