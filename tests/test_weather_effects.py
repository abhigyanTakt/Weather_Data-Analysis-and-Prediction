"""
Unit tests for Weather Designing Effects & Animated Cursor Module.
Verifies weather classification, SVG generators, and theme structure.
"""

import pytest
from climatrend.src.weather_effects import get_weather_theme


def test_weather_theme_rain():
    """Verify rain weather code generates rain theme and valid SVG."""
    theme = get_weather_theme(weather_code=61, is_day=1, temp=15.0)
    assert theme["type"] == "rain"
    assert "Rain" in theme["name"]
    assert "<svg" in theme["svg"]
    assert "fill=\"#38bdf8\"" in theme["svg"]


def test_weather_theme_snow():
    """Verify snow weather code generates snow theme with snowflake SVG."""
    theme = get_weather_theme(weather_code=71, is_day=1, temp=-2.0)
    assert theme["type"] == "snow"
    assert "Snow" in theme["name"]
    assert "<svg" in theme["svg"]


def test_weather_theme_thunderstorm():
    """Verify thunderstorm weather code generates lightning effects."""
    theme = get_weather_theme(weather_code=95, is_day=1, temp=22.0)
    assert theme["type"] == "thunderstorm"
    assert "Thunderstorm" in theme["name"]
    assert "polygon" in theme["svg"]  # Lightning bolt


def test_weather_theme_sunny_vs_night():
    """Verify day/night distinction for clear weather."""
    day_theme = get_weather_theme(weather_code=0, is_day=1, temp=25.0)
    assert day_theme["type"] == "sunny"
    assert "Sunny" in day_theme["name"]

    night_theme = get_weather_theme(weather_code=0, is_day=0, temp=15.0)
    assert night_theme["type"] == "night"
    assert "Night" in night_theme["name"]


def test_weather_theme_cloudy():
    """Verify overcast/cloudy weather codes."""
    cloud_theme = get_weather_theme(weather_code=3, is_day=1, temp=18.0)
    assert cloud_theme["type"] == "cloudy"
    assert "<svg" in cloud_theme["svg"]
