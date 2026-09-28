"""
ClimaTrend Weather Designing Effects & Animated Cursor Module.
Dynamically injects visual ambient atmospheric effects (rain, snow, lightning,
sunbeams, drifting clouds, starfields) based on current location weather,
and sets an animated weather smiley emoji cursor with particle trails.
"""

import urllib.parse
from typing import Dict, Any, Tuple
import streamlit as st


def get_weather_theme(weather_code: int, is_day: int = 1, temp: float = 20.0) -> Dict[str, Any]:
    """
    Classifies the current weather into a visual design theme and corresponding
    animated smiley emoji SVG.
    """
    # 1. Thunderstorm (codes 95, 96, 99)
    if weather_code in [95, 96, 99]:
        return {
            "type": "thunderstorm",
            "name": "Electric Thunderstorm",
            "badge": "⛈️ Thunderstorm Active",
            "color": "#818cf8",
            "accent": "#fbbf24",
            "emoji": "⛈️",
            "svg": _get_thunderstorm_svg(),
            "cursor_size": 36,
        }

    # 2. Snow / Sleet (codes 71, 73, 75, 77, 85, 86 or freezing temp with precip)
    if weather_code in [71, 73, 75, 77, 85, 86] or (temp <= 0 and weather_code in [51, 61, 80]):
        return {
            "type": "snow",
            "name": "Winter Snowfall",
            "badge": "❄️ Gentle Snow Falling",
            "color": "#7dd3fc",
            "accent": "#e0f2fe",
            "emoji": "❄️",
            "svg": _get_snow_svg(),
            "cursor_size": 36,
        }

    # 3. Rain / Showers / Drizzle (codes 51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82)
    if weather_code in [51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82]:
        return {
            "type": "rain",
            "name": "Refreshing Rain",
            "badge": "🌧️ Ambient Rain Shower",
            "color": "#38bdf8",
            "accent": "#0284c7",
            "emoji": "🌧️",
            "svg": _get_rain_svg(),
            "cursor_size": 36,
        }

    # 4. Fog / Mist (codes 45, 48)
    if weather_code in [45, 48]:
        return {
            "type": "fog",
            "name": "Atmospheric Mist & Fog",
            "badge": "🌫️ Volumetric Mist",
            "color": "#94a3b8",
            "accent": "#cbd5e1",
            "emoji": "🌫️",
            "svg": _get_cloud_svg(),
            "cursor_size": 36,
        }

    # 5. Overcast / Heavy Clouds (code 3)
    if weather_code == 3:
        return {
            "type": "cloudy",
            "name": "Overcast Sky",
            "badge": "☁️ Puffy Cloud Layer",
            "color": "#94a3b8",
            "accent": "#e2e8f0",
            "emoji": "☁️",
            "svg": _get_cloud_svg(),
            "cursor_size": 36,
        }

    # 6. Clear / Sunny Day (codes 0, 1, 2 during daytime)
    if is_day == 1:
        if weather_code in [1, 2]:
            return {
                "type": "partly_cloudy",
                "name": "Sun & Scattered Clouds",
                "badge": "⛅ Golden Sunlight & Clouds",
                "color": "#f59e0b",
                "accent": "#38bdf8",
                "emoji": "⛅",
                "svg": _get_partly_cloudy_svg(),
                "cursor_size": 36,
            }
        return {
            "type": "sunny",
            "name": "Clear & Sunny",
            "badge": "☀️ Radiant Golden Sun",
            "color": "#fbbf24",
            "accent": "#f59e0b",
            "emoji": "☀️",
            "svg": _get_sun_svg(),
            "cursor_size": 36,
        }

    # 7. Clear Night (codes 0, 1, 2 at night)
    return {
        "type": "night",
        "name": "Starlit Night",
        "badge": "🌙 Twinkling Night Sky",
        "color": "#a855f7",
        "accent": "#fde047",
        "emoji": "🌙",
        "svg": _get_night_svg(),
        "cursor_size": 36,
    }


def _get_sun_svg() -> str:
    """Cute smiling radiant sun with rosy cheeks and joyful eyes."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <defs>
    <radialGradient id="sunGlow" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#fef08a"/>
      <stop offset="100%" stop-color="#fbbf24"/>
    </radialGradient>
  </defs>
  <!-- Rotating Sun Rays -->
  <g stroke="#f59e0b" stroke-width="2.5" stroke-linecap="round">
    <line x1="19" y1="2" x2="19" y2="6"/>
    <line x1="19" y1="32" x2="19" y2="36"/>
    <line x1="2" y1="19" x2="6" y2="19"/>
    <line x1="32" y1="19" x2="36" y2="19"/>
    <line x1="7" y1="7" x2="10" y2="10"/>
    <line x1="28" y1="28" x2="31" y2="31"/>
    <line x1="7" y1="31" x2="10" y2="28"/>
    <line x1="28" y1="10" x2="31" y2="7"/>
  </g>
  <!-- Smiling Sun Center -->
  <circle cx="19" cy="19" r="11" fill="url(#sunGlow)" stroke="#f59e0b" stroke-width="1.8"/>
  <!-- Rosy Cheeks -->
  <circle cx="14" cy="21" r="2" fill="#fb7185" opacity="0.75"/>
  <circle cx="24" cy="21" r="2" fill="#fb7185" opacity="0.75"/>
  <!-- Happy Eyes (curved joyful arcs) -->
  <path d="M 13 17 Q 15 14 17 17" stroke="#1e293b" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <path d="M 21 17 Q 23 14 25 17" stroke="#1e293b" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <!-- Catchlight Sparkle -->
  <circle cx="14" cy="14" r="0.8" fill="#ffffff"/>
  <circle cx="22" cy="14" r="0.8" fill="#ffffff"/>
  <!-- Big Happy Smile -->
  <path d="M 15 21 Q 19 26 23 21" stroke="#1e293b" stroke-width="1.8" stroke-linecap="round" fill="#e11d48"/>
</svg>"""


def _get_rain_svg() -> str:
    """Cute smiling cloud with droplets and happy face."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <!-- Raindrops falling -->
  <g fill="#38bdf8">
    <ellipse cx="12" cy="32" rx="1.5" ry="3"/>
    <ellipse cx="19" cy="34" rx="1.5" ry="3"/>
    <ellipse cx="26" cy="32" rx="1.5" ry="3"/>
  </g>
  <!-- Fluffy Cloud Body -->
  <path d="M 11 26 C 6 26 4 21 8 18 C 6 12 12 9 17 11 C 20 7 27 8 28 12 C 33 13 34 18 31 22 C 34 26 29 27 26 26 Z" fill="#e0f2fe" stroke="#38bdf8" stroke-width="1.8"/>
  <!-- Rosy Cheeks -->
  <circle cx="14" cy="21" r="1.8" fill="#f472b6" opacity="0.8"/>
  <circle cx="24" cy="21" r="1.8" fill="#f472b6" opacity="0.8"/>
  <!-- Happy Eyes -->
  <ellipse cx="15" cy="18" rx="1.3" ry="1.7" fill="#0f172a"/>
  <ellipse cx="23" cy="18" rx="1.3" ry="1.7" fill="#0f172a"/>
  <circle cx="15.5" cy="17.2" r="0.6" fill="#ffffff"/>
  <circle cx="23.5" cy="17.2" r="0.6" fill="#ffffff"/>
  <!-- Joyful Smile -->
  <path d="M 16 22 Q 19 25 22 22" stroke="#0f172a" stroke-width="1.6" stroke-linecap="round" fill="none"/>
</svg>"""


def _get_snow_svg() -> str:
    """Cute smiling ice snowflake."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <!-- Snowflake Crystal Spokes -->
  <g stroke="#7dd3fc" stroke-width="2.2" stroke-linecap="round">
    <line x1="19" y1="3" x2="19" y2="35"/>
    <line x1="3" y1="19" x2="35" y2="19"/>
    <line x1="7.7" y1="7.7" x2="30.3" y2="30.3"/>
    <line x1="7.7" y1="30.3" x2="30.3" y2="7.7"/>
    <!-- Crystal branches -->
    <line x1="16" y1="6" x2="19" y2="9"/>
    <line x1="22" y1="6" x2="19" y2="9"/>
    <line x1="16" y1="32" x2="19" y2="29"/>
    <line x1="22" y1="32" x2="19" y2="29"/>
  </g>
  <!-- Center Face Badge -->
  <circle cx="19" cy="19" r="9.5" fill="#f0f9ff" stroke="#38bdf8" stroke-width="1.8"/>
  <!-- Rosy Frost Cheeks -->
  <circle cx="14" cy="20" r="1.8" fill="#fda4af" opacity="0.8"/>
  <circle cx="24" cy="20" r="1.8" fill="#fda4af" opacity="0.8"/>
  <!-- Happy Eyes -->
  <ellipse cx="15" cy="17" rx="1.2" ry="1.6" fill="#0369a1"/>
  <ellipse cx="23" cy="17" rx="1.2" ry="1.6" fill="#0369a1"/>
  <circle cx="15.5" cy="16.3" r="0.5" fill="#ffffff"/>
  <circle cx="23.5" cy="16.3" r="0.5" fill="#ffffff"/>
  <!-- Frosty Smile -->
  <path d="M 16 21 Q 19 24 22 21" stroke="#0369a1" stroke-width="1.6" stroke-linecap="round" fill="none"/>
</svg>"""


def _get_thunderstorm_svg() -> str:
    """Cute storm cloud with electric lightning bolt and playful grin."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <!-- Glowing Lightning Bolt -->
  <polygon points="19,23 14,31 19,31 16,37 24,28 19,28 23,23" fill="#fbbf24" stroke="#f59e0b" stroke-width="1"/>
  <!-- Dark Storm Cloud -->
  <path d="M 11 24 C 6 24 4 19 8 16 C 6 10 12 7 17 9 C 20 5 27 6 28 10 C 33 11 34 16 31 20 C 34 24 29 25 26 24 Z" fill="#475569" stroke="#334155" stroke-width="1.8"/>
  <!-- Electric Glowing Cheeks -->
  <circle cx="14" cy="19" r="1.8" fill="#fbbf24" opacity="0.75"/>
  <circle cx="24" cy="19" r="1.8" fill="#fbbf24" opacity="0.75"/>
  <!-- Playful Excited Eyes -->
  <path d="M 13 16 Q 15 13 17 16" stroke="#f8fafc" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <path d="M 21 16 Q 23 13 25 16" stroke="#f8fafc" stroke-width="1.8" stroke-linecap="round" fill="none"/>
  <!-- Big Grin -->
  <path d="M 15 20 Q 19 23 23 20" stroke="#f8fafc" stroke-width="1.8" stroke-linecap="round" fill="#fbbf24"/>
</svg>"""


def _get_partly_cloudy_svg() -> str:
    """Cute smiling sun peeking out from behind a fluffy smiling cloud."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <!-- Sun behind cloud -->
  <circle cx="15" cy="14" r="8" fill="#fbbf24" stroke="#f59e0b" stroke-width="1.5"/>
  <!-- Sun Rays -->
  <g stroke="#f59e0b" stroke-width="2" stroke-linecap="round">
    <line x1="15" y1="2" x2="15" y2="4"/>
    <line x1="5" y1="14" x2="7" y2="14"/>
    <line x1="7.5" y1="6.5" x2="9" y2="8"/>
    <line x1="22.5" y1="6.5" x2="21" y2="8"/>
  </g>
  <!-- Foreground Cloud -->
  <path d="M 14 30 C 9 30 7 25 11 22 C 9 17 15 14 19 16 C 22 12 28 13 29 17 C 34 18 35 23 32 27 C 35 30 31 31 28 30 Z" fill="#f8fafc" stroke="#94a3b8" stroke-width="1.6"/>
  <!-- Rosy Cheeks on Cloud -->
  <circle cx="17" cy="25" r="1.6" fill="#f472b6" opacity="0.8"/>
  <circle cx="26" cy="25" r="1.6" fill="#f472b6" opacity="0.8"/>
  <!-- Cloud Smiling Face -->
  <ellipse cx="18" cy="22" rx="1.2" ry="1.6" fill="#0f172a"/>
  <ellipse cx="25" cy="22" rx="1.2" ry="1.6" fill="#0f172a"/>
  <circle cx="18.5" cy="21.3" r="0.5" fill="#ffffff"/>
  <circle cx="25.5" cy="21.3" r="0.5" fill="#ffffff"/>
  <path d="M 19 25 Q 21.5 28 24 25" stroke="#0f172a" stroke-width="1.5" stroke-linecap="round" fill="none"/>
</svg>"""


def _get_cloud_svg() -> str:
    """Cute puffy smiling cloud with rosy cheeks."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <path d="M 12 28 C 7 28 5 23 9 20 C 7 14 13 11 18 13 C 21 9 28 10 29 14 C 34 15 35 20 32 24 C 35 28 30 29 27 28 Z" fill="#f1f5f9" stroke="#94a3b8" stroke-width="1.8"/>
  <!-- Rosy Cheeks -->
  <circle cx="15" cy="23" r="1.8" fill="#fda4af" opacity="0.8"/>
  <circle cx="25" cy="23" r="1.8" fill="#fda4af" opacity="0.8"/>
  <!-- Big Shiny Eyes -->
  <ellipse cx="16" cy="19" rx="1.3" ry="1.8" fill="#1e293b"/>
  <ellipse cx="24" cy="19" rx="1.3" ry="1.8" fill="#1e293b"/>
  <circle cx="16.5" cy="18.2" r="0.6" fill="#ffffff"/>
  <circle cx="24.5" cy="18.2" r="0.6" fill="#ffffff"/>
  <!-- Gentle Content Smile -->
  <path d="M 17 23 Q 20 26 23 23" stroke="#1e293b" stroke-width="1.6" stroke-linecap="round" fill="none"/>
</svg>"""


def _get_night_svg() -> str:
    """Cute peaceful smiling crescent moon with stars."""
    return """<svg xmlns="http://www.w3.org/2000/svg" width="38" height="38" viewBox="0 0 38 38">
  <!-- Twinkling Stars -->
  <polygon points="30,5 31,8 34,9 31,10 30,13 29,10 26,9 29,8" fill="#fde047"/>
  <polygon points="8,26 9,28 11,29 9,30 8,32 7,30 5,29 7,28" fill="#fde047"/>
  <!-- Crescent Moon -->
  <path d="M 24 7 C 15 8 12 17 16 26 C 19 29 24 30 27 28 C 18 33 10 24 14 14 C 16 9 20 7 24 7 Z" fill="#fde047" stroke="#eab308" stroke-width="1.5"/>
  <!-- Rosy Cheek -->
  <circle cx="17.5" cy="21.5" r="1.8" fill="#f43f5e" opacity="0.7"/>
  <!-- Peaceful Sleeping/Smiling Eye -->
  <path d="M 15 16 Q 17 18 19 16" stroke="#713f12" stroke-width="1.6" stroke-linecap="round" fill="none"/>
  <!-- Gentle Night Smile -->
  <path d="M 17 22 Q 19 24 21 22" stroke="#713f12" stroke-width="1.5" stroke-linecap="round" fill="none"/>
</svg>"""


def apply_weather_effects(
    weather_code: int = 0,
    is_day: int = 1,
    temp: float = 20.0,
    city_name: str = "Location",
) -> None:
    """
    Renders ambient CSS weather animations and configures an animated weather
    smiley emoji cursor with a smooth interactive follower.
    """
    theme = get_weather_theme(weather_code, is_day, temp)
    wtype = theme["type"]
    svg_raw = theme["svg"]
    encoded_svg = urllib.parse.quote(svg_raw)
    cursor_data_uri = f"data:image/svg+xml,{encoded_svg}"

    # Generate atmospheric background effect CSS based on weather condition
    ambient_css = ""
    extra_dom = ""

    if wtype == "rain":
        ambient_css = """
        /* Rain Streaks Animation */
        @keyframes rainFall {
            0% { transform: translateY(-100vh) translateX(0); }
            100% { transform: translateY(100vh) translateX(-20px); }
        }
        .weather-rain-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: -40;
            overflow: hidden;
            background: linear-gradient(180deg, rgba(14, 165, 233, 0.04) 0%, rgba(2, 132, 199, 0.08) 100%);
        }
        .rain-drop {
            position: absolute;
            bottom: 100%;
            width: 1.5px;
            height: 55px;
            background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(56, 189, 248, 0.65));
            animation: rainFall 0.85s linear infinite;
        }
        """
        # Distribute rain drops
        rain_drops = "".join(
            [
                f'<div class="rain-drop" style="left:{i * 3.8}%; animation-delay:{round((i % 7) * 0.13, 2)}s; animation-duration:{round(0.7 + (i % 5) * 0.08, 2)}s; opacity:{round(0.4 + (i % 4) * 0.15, 2)};"></div>'
                for i in range(26)
            ]
        )
        extra_dom = f'<div class="weather-rain-container">{rain_drops}</div>'

    elif wtype == "thunderstorm":
        ambient_css = """
        /* Thunderstorm Lightning Flash & Rain */
        @keyframes lightningFlash {
            0%, 93%, 97%, 100% { opacity: 0; }
            94% { opacity: 0.28; background-color: #818cf8; }
            95% { opacity: 0.08; background-color: #c7d2fe; }
            96% { opacity: 0.35; background-color: #ffffff; }
        }
        @keyframes stormRain {
            0% { transform: translateY(-100vh) translateX(0); }
            100% { transform: translateY(100vh) translateX(-45px); }
        }
        .weather-storm-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: -40;
            overflow: hidden;
            animation: lightningFlash 7s infinite ease-out;
        }
        .storm-drop {
            position: absolute;
            bottom: 100%;
            width: 2px;
            height: 70px;
            background: linear-gradient(to bottom, rgba(255,255,255,0), rgba(165, 180, 252, 0.75));
            animation: stormRain 0.65s linear infinite;
        }
        """
        storm_drops = "".join(
            [
                f'<div class="storm-drop" style="left:{i * 3.5}%; animation-delay:{round((i % 8) * 0.09, 2)}s; animation-duration:{round(0.55 + (i % 4) * 0.06, 2)}s;"></div>'
                for i in range(28)
            ]
        )
        extra_dom = f'<div class="weather-storm-container">{storm_drops}</div>'

    elif wtype == "snow":
        ambient_css = """
        /* Snow Drifting Animation */
        @keyframes snowSway {
            0% { transform: translateY(-10vh) translateX(0) rotate(0deg); opacity: 0; }
            15% { opacity: 0.85; }
            50% { transform: translateY(50vh) translateX(25px) rotate(180deg); }
            85% { opacity: 0.85; }
            100% { transform: translateY(105vh) translateX(-15px) rotate(360deg); opacity: 0; }
        }
        .weather-snow-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: -40;
            overflow: hidden;
            background: radial-gradient(circle at 50% 0%, rgba(186, 230, 253, 0.08) 0%, transparent 70%);
        }
        .snow-flake {
            position: absolute;
            color: #ffffff;
            font-size: 18px;
            user-select: none;
            filter: drop-shadow(0 0 6px rgba(186, 230, 253, 0.8));
            animation: snowSway linear infinite;
        }
        """
        flakes = ["❄", "❅", "❆", "•"]
        snow_dom = "".join(
            [
                f'<div class="snow-flake" style="left:{i * 4.2}%; animation-delay:{round((i % 10) * 0.45, 1)}s; animation-duration:{round(5.5 + (i % 6) * 1.1, 1)}s; font-size:{12 + (i % 5) * 4}px; opacity:{round(0.5 + (i % 4) * 0.15, 2)};">{flakes[i % len(flakes)]}</div>'
                for i in range(24)
            ]
        )
        extra_dom = f'<div class="weather-snow-container">{snow_dom}</div>'

    elif wtype in ["sunny", "partly_cloudy"]:
        ambient_css = """
        /* Warm Sunlight Sunbeam Flare */
        @keyframes sunRayGlow {
            0%, 100% { opacity: 0.28; transform: scale(1) rotate(0deg); }
            50% { opacity: 0.45; transform: scale(1.08) rotate(4deg); }
        }
        .weather-sun-glow {
            position: fixed;
            top: -160px;
            right: -160px;
            width: 580px;
            height: 580px;
            border-radius: 50%;
            background: radial-gradient(circle, rgba(251, 191, 36, 0.28) 0%, rgba(245, 158, 11, 0.12) 45%, transparent 72%);
            pointer-events: none;
            z-index: -40;
            animation: sunRayGlow 8s ease-in-out infinite;
            filter: blur(20px);
        }
        """
        extra_dom = '<div class="weather-sun-glow"></div>'

    elif wtype == "night":
        ambient_css = """
        /* Twinkling Starfield */
        @keyframes starTwinkle {
            0%, 100% { opacity: 0.25; transform: scale(0.85); }
            50% { opacity: 0.95; transform: scale(1.3); }
        }
        .weather-night-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 100vw;
            height: 100vh;
            pointer-events: none;
            z-index: -40;
            overflow: hidden;
            background: radial-gradient(circle at 80% 15%, rgba(168, 85, 247, 0.08) 0%, transparent 60%);
        }
        .night-star {
            position: absolute;
            color: #fde047;
            animation: starTwinkle ease-in-out infinite;
            user-select: none;
        }
        """
        stars_dom = "".join(
            [
                f'<div class="night-star" style="left:{5 + (i * 4.3) % 90}%; top:{4 + (i * 7.1) % 65}%; animation-delay:{round((i % 7) * 0.4, 2)}s; animation-duration:{round(2.0 + (i % 5) * 0.6, 2)}s; font-size:{9 + (i % 3) * 3}px;">✦</div>'
                for i in range(22)
            ]
        )
        extra_dom = f'<div class="weather-night-container">{stars_dom}</div>'

    elif wtype in ["cloudy", "fog"]:
        ambient_css = """
        /* Drifting Atmospheric Mist */
        @keyframes mistDrift {
            0% { transform: translateX(-15%); opacity: 0.35; }
            50% { transform: translateX(10%); opacity: 0.55; }
            100% { transform: translateX(-15%); opacity: 0.35; }
        }
        .weather-mist-container {
            position: fixed;
            top: 0;
            left: 0;
            width: 130vw;
            height: 100vh;
            pointer-events: none;
            z-index: -40;
            background: linear-gradient(180deg, rgba(148, 163, 184, 0.12) 0%, rgba(203, 213, 225, 0.04) 50%, transparent 100%);
            animation: mistDrift 22s ease-in-out infinite;
            filter: blur(28px);
        }
        """
        extra_dom = '<div class="weather-mist-container"></div>'

    # Master CSS: Cursor override + Interactive animated follower + Floating animation
    full_css = f"""
    <style>
    /* 1. Global Animated Weather Smiley Cursor */
    html, body, [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] * {{
        cursor: url("{cursor_data_uri}") 18 18, auto !important;
    }}

    button, a, select, input, [role="button"], .stButton > button, [data-baseweb="tab"] {{
        cursor: url("{cursor_data_uri}") 18 18, pointer !important;
    }}

    /* 2. Floating Animated Companion Badge */
    @keyframes smileyBobbing {{
        0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
        25% {{ transform: translateY(-4px) rotate(-6deg); }}
        75% {{ transform: translateY(3px) rotate(6deg); }}
    }}

    @keyframes pulseRing {{
        0% {{ transform: scale(0.9); opacity: 0.7; }}
        50% {{ transform: scale(1.35); opacity: 0; }}
        100% {{ transform: scale(0.9); opacity: 0; }}
    }}

    #climatrend-cursor-follower {{
        position: fixed;
        top: 0;
        left: 0;
        width: 32px;
        height: 32px;
        pointer-events: none;
        z-index: 999999;
        transform: translate3d(-100px, -100px, 0);
        transition: transform 0.08s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.3s ease;
        will-change: transform;
    }}

    #climatrend-cursor-follower .inner-smiley {{
        width: 100%;
        height: 100%;
        animation: smileyBobbing 3s ease-in-out infinite;
        filter: drop-shadow(0 2px 8px {theme["color"]}66);
    }}

    #climatrend-cursor-follower.cursor-clicking .inner-smiley {{
        transform: scale(1.4) rotate(15deg);
        transition: transform 0.15s ease;
    }}

    #climatrend-cursor-follower.cursor-hovering .inner-smiley {{
        transform: scale(1.25);
        filter: drop-shadow(0 0 12px {theme["color"]});
    }}

    /* Atmospheric effects */
    {ambient_css}
    </style>
    """

    # Inject DOM & CSS into page
    st.markdown(full_css, unsafe_allow_html=True)
    if extra_dom:
        st.markdown(extra_dom, unsafe_allow_html=True)

    # Inject high-performance lightweight script via iframe to attach follower to window.parent
    js_script = f"""
    <script>
    (function() {{
        try {{
            const doc = window.parent.document;
            let follower = doc.getElementById('climatrend-cursor-follower');
            
            if (!follower) {{
                follower = doc.createElement('div');
                follower.id = 'climatrend-cursor-follower';
                doc.body.appendChild(follower);
            }}

            follower.innerHTML = `
                <div class="inner-smiley">
                    {svg_raw}
                </div>
            `;

            let mouseX = -100, mouseY = -100;
            let posX = -100, posY = -100;

            const onMouseMove = (e) => {{
                mouseX = e.clientX + 14;
                mouseY = e.clientY + 14;
            }};

            const onMouseDown = () => {{
                if (follower) follower.classList.add('cursor-clicking');
            }};

            const onMouseUp = () => {{
                if (follower) follower.classList.remove('cursor-clicking');
            }};

            const onMouseOver = (e) => {{
                if (e.target && (e.target.tagName === 'BUTTON' || e.target.tagName === 'A' || e.target.closest('button') || e.target.closest('a'))) {{
                    follower.classList.add('cursor-hovering');
                }} else {{
                    follower.classList.remove('cursor-hovering');
                }}
            }};

            doc.addEventListener('mousemove', onMouseMove, {{ passive: true }});
            doc.addEventListener('mousedown', onMouseDown, {{ passive: true }});
            doc.addEventListener('mouseup', onMouseUp, {{ passive: true }});
            doc.addEventListener('mouseover', onMouseOver, {{ passive: true }});

            let active = true;
            function loop() {{
                if (!active) return;
                posX += (mouseX - posX) * 0.25;
                posY += (mouseY - posY) * 0.25;
                follower.style.transform = `translate3d(${{posX}}px, ${{posY}}px, 0)`;
                requestAnimationFrame(loop);
            }}
            requestAnimationFrame(loop);

        }} catch (err) {{
            // Parent document access secured
        }}
    }})();
    </script>
    """
    st.components.v1.html(js_script, height=0)
