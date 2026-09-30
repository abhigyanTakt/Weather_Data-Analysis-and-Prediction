"""
Helper utility for creating clean, high-performance Folium basemaps.
Replaces deprecated/watermarked CartoDB tiles with reliable, free,
non-watermarked tiles (Esri Dark Canvas, OpenStreetMap, and Esri Satellite).
Supports CARTO_API_KEY when provided in .env.
"""

from typing import Any, List, Optional, Tuple
import folium
from climatrend.climate.config import CARTO_API_KEY


def get_folium_base_map(
    location: Any,
    zoom_start: int = 12,
    dark_mode: bool = True,
    include_layer_control: bool = True,
) -> folium.Map:
    """
    Creates a Folium Map with clean, un-watermarked basemaps.
    - If dark_mode=True: Uses Esri Dark Canvas (matches ClimaTrend UI) with OpenStreetMap and Satellite options.
    - If dark_mode=False: Uses OpenStreetMap with Dark Canvas and Satellite options.
    - If CARTO_API_KEY is configured: Can optionally use Carto without watermark.
    """
    carto_key = CARTO_API_KEY.strip()

    if dark_mode:
        if carto_key:
            base_tiles = f"https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png?api_key={carto_key}"
            base_attr = "© CARTO, © OpenStreetMap contributors"
            base_name = "Carto Dark"
        else:
            base_tiles = "https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
            base_attr = "Esri, HERE, Garmin, © OpenStreetMap contributors"
            base_name = "Dark Canvas"
    else:
        base_tiles = "OpenStreetMap"
        base_attr = "© OpenStreetMap contributors"
        base_name = "OpenStreetMap"

    m = folium.Map(
        location=location,
        zoom_start=zoom_start,
        tiles=base_tiles,
        attr=base_attr if base_tiles != "OpenStreetMap" else None,
        name=base_name,
    )

    if include_layer_control:
        if dark_mode:
            folium.TileLayer(
                tiles="OpenStreetMap",
                name="OpenStreetMap",
            ).add_to(m)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri World Imagery",
                name="Satellite Imagery",
            ).add_to(m)
        else:
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}",
                attr="Esri Dark Gray",
                name="Dark Canvas",
            ).add_to(m)
            folium.TileLayer(
                tiles="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
                attr="Esri World Imagery",
                name="Satellite Imagery",
            ).add_to(m)

        folium.LayerControl(position="topright").add_to(m)

    return m
