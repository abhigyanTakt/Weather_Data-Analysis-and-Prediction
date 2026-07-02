"""
ClimaTrend Streamlit Dashboard.

This is the main web application file that integrates all ClimaTrend modules
into an interactive, professional-grade dashboard with high-fidelity UI/UX,
multilingual localizations, and real-time weather reports.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
import datetime
import matplotlib.pyplot as plt
import streamlit as st
import plotly.graph_objects as go
import requests
from PIL import Image

# Setup path to import src modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from climatrend.src.data_acquisition import geocode_city, fetch_historical_weather, fetch_realtime_forecast
from climatrend.src.data_cleaning import process_pipeline
from climatrend.src.eda import (
    generate_summary_statistics,
    perform_seasonal_decomposition,
    compute_acf_pacf,
    calculate_correlations,
)
from climatrend.src.chart_visualizations import (
    plot_time_series,
    plot_seasonal_decomposition,
    plot_acf_pacf,
    plot_correlation_heatmap,
    plot_calendar_heatmap,
    plot_monthly_distribution,
    plot_bar_averages,
    plot_scatter_correlation,
    plot_wind_rose,
)
from climatrend.src.map_visualizations import (
    plot_static_choropleth,
    plot_interactive_folium_heatmap,
    plot_contour_gradient,
)
from climatrend.src.ai_insights import get_ai_insight, API_KEY
from climatrend.src.forecasting_model import train_test_split_ts
from climatrend.src.translations import TRANSLATIONS

# Configure logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Start background server for wallpaper video
import socket
import threading
import http.server
import socketserver

def find_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def start_background_wallpaper_server():
    if getattr(sys, "_wallpaper_server_started", False):
        return sys._wallpaper_server_port

    port = find_free_port()
    directory = r"D:\Downloads\Wallpaper1\Live"
    
    if not os.path.exists(directory):
        logger.warning(f"Wallpaper directory {directory} does not exist.")
        sys._wallpaper_server_started = True
        sys._wallpaper_server_port = None
        return None

    class SilentHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=directory, **kwargs)
        
        def log_message(self, format, *args):
            # Suppress logs to keep terminal clean
            pass

    def serve():
        socketserver.TCPServer.allow_reuse_address = True
        try:
            with socketserver.TCPServer(("", port), SilentHTTPRequestHandler) as httpd:
                sys._wallpaper_server_instance = httpd
                httpd.serve_forever()
        except Exception as e:
            logger.error(f"Failed to run TCPServer on port {port}: {str(e)}")

    thread = threading.Thread(target=serve, daemon=True)
    thread.start()
    
    sys._wallpaper_server_started = True
    sys._wallpaper_server_port = port
    logger.info(f"Started background wallpaper server on port {port} serving {directory}")
    return port

wallpaper_port = start_background_wallpaper_server()

# Streamlit config
st.set_page_config(
    page_title="ClimaTrend | Weather Analysis & Forecasting",
    page_icon="🌡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Render Background Video wallpaper
if wallpaper_port:
    st.markdown(
        f"""
        <video autoplay loop muted playsinline onplay="this.playbackRate = 1.75;" style="
            position: fixed;
            left: 50%;
            top: 50%;
            transform: translate(-50%, -50%) scale(0.4);
            min-width: 100%;
            min-height: 100%;
            width: auto;
            height: auto;
            z-index: -100;
            object-fit: cover;
            opacity: 0.35;
        ">
            <source src="http://localhost:{wallpaper_port}/azure-horizon.3840x2160.mp4" type="video/mp4">
        </video>
        """,
        unsafe_allow_html=True,
    )

# Custom High-Fidelity UI/UX CSS with Transitions & Animations
st.markdown(
    """
    <style>
    /* Fade-in slide-up animation for main app */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(15px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .main .block-container {
        animation: fadeInUp 0.7s cubic-bezier(0.4, 0, 0.2, 1) both;
        padding-top: 1.5rem !important;
    }

    /* Dark theme adjustments with transparency for live video */
    body {
        background-color: #0c1524 !important;
    }

    .stApp {
        background: transparent !important;
        color: #f8fafc !important;
    }

    div[data-testid="stAppViewContainer"] {
        background: transparent !important;
    }

    div[data-testid="stMain"] {
        background: transparent !important;
    }

    div[data-testid="stHeader"] {
        background-color: rgba(12, 21, 36, 0.4) !important;
        backdrop-filter: blur(10px) !important;
    }

    /* Sidebar Styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, rgba(8, 13, 22, 0.8) 0%, rgba(12, 21, 36, 0.8) 100%) !important;
        backdrop-filter: blur(12px) !important;
        border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
    }

    /* Glassmorphism Cards with Neon Hover */
    .metric-card {
        background-color: rgba(24, 34, 50, 0.5) !important;
        padding: 16px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
    }
    .metric-card:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(0, 255, 255, 0.15) !important;
        border-color: #00ffff !important;
    }

    /* Style the 3D weather model card directly via its container */
    div[data-testid="stHtml"] {
        background-color: rgba(24, 34, 50, 0.5) !important;
        padding: 10px !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.3) !important;
        border: 1px solid rgba(255, 255, 255, 0.08) !important;
        backdrop-filter: blur(8px) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        height: 220px !important;
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        align-items: center !important;
    }
    div[data-testid="stHtml"]:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 30px rgba(0, 255, 255, 0.15) !important;
        border-color: #00ffff !important;
    }

    .metric-val {
        font-size: 24px !important;
        font-weight: bold !important;
        color: #00ffff !important;
        text-shadow: 0 0 8px rgba(0, 255, 255, 0.4) !important;
    }

    .metric-lbl {
        font-size: 11px !important;
        color: #94a3b8 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
    }

    /* Neon buttons override */
    .stButton > button {
        background: linear-gradient(135deg, rgba(12, 21, 36, 0.8) 0%, rgba(30, 41, 59, 0.8) 100%) !important;
        color: #00ffff !important;
        border: 1px solid #00ffff !important;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.2) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        font-weight: bold !important;
        border-radius: 8px !important;
        text-transform: uppercase !important;
        letter-spacing: 0.05em !important;
        width: 100%;
        text-shadow: 0 0 4px rgba(0, 255, 255, 0.4) !important;
    }
    .stButton > button:hover {
        background: #00ffff !important;
        color: #0c1524 !important;
        box-shadow: 0 0 15px #00ffff, 0 0 30px rgba(0, 255, 255, 0.6) !important;
        transform: translateY(-2px) !important;
        text-shadow: none !important;
    }

    /* Top bar container styling */
    .top-bar-container {
        background: rgba(12, 21, 36, 0.4);
        padding: 10px 15px;
        border-radius: 12px;
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.03);
    }

    /* Top city card styling */
    .top-city-card {
        background: rgba(24, 34, 50, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 20px;
        padding: 6px 14px;
        display: inline-flex;
        align-items: center;
        font-size: 13px;
        color: #f8fafc;
        box-shadow: 0 2px 10px rgba(0,0,0,0.2);
    }

    .alert-badge {
        background-color: #f59e0b;
        color: #0f172a;
        font-size: 10px;
        font-weight: bold;
        border-radius: 50%;
        width: 16px;
        height: 16px;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        margin-left: 8px;
        box-shadow: 0 0 8px #f59e0b;
    }

    /* Vertical Radio-based Floating Navigation Menu */
    div[data-testid="stRadio"] label[data-baseweb="radio"] {
        background-color: rgba(24, 34, 50, 0.5) !important;
        border: 1px solid rgba(255, 255, 255, 0.05) !important;
        color: #94a3b8 !important;
        border-radius: 10px !important;
        padding: 10px 16px !important;
        margin-bottom: 10px !important;
        transition: all 0.3s ease !important;
        width: 100% !important;
        cursor: pointer !important;
    }
    
    div[data-testid="stRadio"] label[data-baseweb="radio"]:hover {
        color: #00ffff !important;
        border-color: #00ffff !important;
        background-color: rgba(0, 255, 255, 0.05) !important;
        box-shadow: 0 0 10px rgba(0, 255, 255, 0.2) !important;
    }
    
    /* Active menu item with yellow glowing theme */
    div[data-testid="stRadio"] label[data-baseweb="radio"]:has(div[aria-checked="true"]) {
        background: linear-gradient(135deg, #ffea00 0%, #d9b600 100%) !important;
        color: #0c1524 !important;
        font-weight: bold !important;
        border-color: #ffea00 !important;
        box-shadow: 0 0 15px #ffea00, 0 0 30px rgba(255, 234, 0, 0.4) !important;
    }
    
    /* Hide the default radio circle */
    div[data-testid="stRadio"] label[data-baseweb="radio"] div[role="presentation"] {
        display: none !important;
    }

    /* Custom styled weather detail container */
    .weather-detail-container {
        background: rgba(30, 41, 59, 0.5);
        border-radius: 12px;
        border: 1px solid rgba(255, 255, 255, 0.05);
        padding: 15px;
        margin-bottom: 12px;
    }
    .weather-icon-inline {
        font-size: 40px;
        margin-right: 15px;
    }

    /* Hide standard Streamlit header details */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    </style>
    """,
    unsafe_allow_html=True,
)

# Global Predefined Cities for Map and Quick Loading
PREDEFINED_CITIES = {
    "London": {"lat": 51.5074, "lon": -0.1278, "country": "United Kingdom"},
    "New York": {"lat": 40.7128, "lon": -74.0060, "country": "United States"},
    "Tokyo": {"lat": 35.6762, "lon": 139.6503, "country": "Japan"},
    "Sydney": {"lat": -33.8688, "lon": 151.2093, "country": "Australia"},
    "Cairo": {"lat": 30.0444, "lon": 31.2357, "country": "Egypt"},
    "Moscow": {"lat": 55.7558, "lon": 37.6173, "country": "Russia"},
    "Rio de Janeiro": {"lat": -22.9068, "lon": -43.1729, "country": "Brazil"},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777, "country": "India"},
    "Cape Town": {"lat": -33.9249, "lon": 18.4241, "country": "South Africa"},
    "Singapore": {"lat": 1.3521, "lon": 103.8198, "country": "Singapore"},
    "Paris": {"lat": 48.8566, "lon": 2.3522, "country": "France"},
    "Buenos Aires": {"lat": -34.6037, "lon": -58.3816, "country": "Argentina"},
}

# Weather Code to Emoji Icon Map
def get_weather_icon(code: int, is_day: int = 1) -> str:
    if code == 0:
        return "☀️" if is_day == 1 else "🌙"  # Clear
    elif code in [1, 2, 3]:
        return "⛅" if is_day == 1 else "☁️"  # Partly Cloudy
    elif code in [45, 48]:
        return "🌫️"  # Fog
    elif code in [51, 53, 55]:
        return "🌦️" if is_day == 1 else "🌧️"  # Drizzle
    elif code in [61, 63, 65]:
        return "🌧️"  # Rain
    elif code in [71, 73, 75, 77]:
        return "❄️"  # Snow
    elif code in [80, 81, 82]:
        return "🌦️" if is_day == 1 else "🌧️"  # Showers
    elif code in [85, 86]:
        return "🌨️"  # Snow Showers
    elif code in [95, 96, 99]:
        return "⛈️"  # Thunderstorm
    return "🌡️"



@st.cache_data(show_spinner=False)
def load_global_map_data():
    """
    Fetches weather data for all predefined cities to display on the world map.
    Cached to avoid API hits on every interaction.
    """
    logger.info("Loading global city weather data for mapping...")
    start_date = (datetime.date.today() - datetime.timedelta(days=365)).strftime("%Y-%m-%d")
    end_date = datetime.date.today().strftime("%Y-%m-%d")

    records = []
    for city, coords in PREDEFINED_CITIES.items():
        try:
            df_raw = fetch_historical_weather(
                coords["lat"],
                coords["lon"],
                start_date,
                end_date,
                city_name=city,
            )
            if df_raw is not None and not df_raw.empty:
                _, df_daily = process_pipeline(df_raw)
                avg_temp = df_daily["temperature_2m_mean"].mean()
                avg_precip = df_daily["precipitation_sum"].mean()
                records.append(
                    {
                        "name": city,
                        "latitude": coords["lat"],
                        "longitude": coords["lon"],
                        "country": coords["country"],
                        "temperature_2m_mean": avg_temp,
                        "precipitation_sum": avg_precip,
                    }
                )
        except Exception as e:
            logger.error(f"Failed to fetch global map data for {city}: {str(e)}")

    return pd.DataFrame(records)


# ----------------- SIDEBAR HEADER & LOGO -----------------
logo_path = os.path.join(os.path.dirname(__file__), "logo.jpg")
if os.path.exists(logo_path):
    st.sidebar.image(logo_path, width='stretch')
else:
    st.sidebar.image(
        "https://images.unsplash.com/photo-1592217643599-22c54463d7e8?auto=format&fit=crop&w=400&q=80",
        width='stretch',
    )

# Language Selector
st.sidebar.markdown("### 🌐 Localization")
language = st.sidebar.selectbox(
    "Language / 言語 / Idioma / भाषा",
    ["English", "日本語", "中文 (Mandarin)", "Español", "Français", "हिन्दी"],
)

LOCAL_TRANSLATIONS = {
    "English": {
        "overview": "Overview",
        "feels_like_toggle": "Feels like",
        "now": "Now",
        "precipitation_label": "Precipitation",
        "sunrise_sunset_cycle": "Sunrise / Sunset cycle active",
        "night_sky_moon": "Night sky — Moon visible",
        "hourly_met_forecast": "Hourly Detailed Meteorological Forecast",
        "time_lbl": "Time",
        "temp_lbl": "Temperature",
        "humidity_pct": "Humidity (%)",
        "precip_prob_pct": "Precipitation Prob (%)",
        "map_settings": "Map Settings",
        "weather_overlay": "Weather Overlay",
        "map_zoom_level": "Map Zoom Level",
        "selected_city_lbl": "Selected City",
        "coordinates_lbl": "Coordinates",
        "elevation_lbl": "Elevation",
        "show_location_marker": "Show Location Marker",
        "overlay_temp": "Temperature 🌡️",
        "overlay_rain": "Rain / Radar 🌧️",
        "overlay_wind": "Wind 🌀",
        "overlay_clouds": "Clouds ☁️",
        "overlay_pressure": "Pressure 🎈",
        "interactive_map_title": "Interactive Map",
        "interactive_city_maps": "Interactive City Weather Maps",
        "global_maps_title": "Global Spatial Weather Distribution (Folium Heatmap / Choropleth)",
        "global_maps_desc": "Mapping global temperature distributions using Open-Meteo station observations across predefined cities.",
        "3d_state_space": "3D Meteorological State Space Analysis",
        "3d_state_space_desc": "Rotate and explore weather parameter relations interactively (Temp, Humidity, Wind, Precip).",
        "forecasting_engine": "Time-Series Forecasting Engine",
        "forecasting_horizon_desc": "Forecasting future {target} over a {horizon}-day horizon.",
        "select_models_warn": "Please select at least one model to run the forecast.",
        "exec_success": "Models executed successfully!",
        "eval_metrics_missing": "Evaluation metrics not available.",
        "select_models_prompt": "Please select and run the forecasting models using the button above.",
        "daytime": "☀️ Daytime",
        "nighttime": "🌙 Nighttime",
        "eda_trends": "Advanced Weather Trends & Predictive Forecasting",
    },
    "日本語": {
        "overview": "概要",
        "feels_like_toggle": "体感温度",
        "now": "現在",
        "precipitation_label": "降水量",
        "sunrise_sunset_cycle": "日の出・日の入りサイクルが有効",
        "night_sky_moon": "夜空 — 月が見えます",
        "hourly_met_forecast": "時間ごとの詳細な気象予測",
        "time_lbl": "時間",
        "temp_lbl": "気温",
        "humidity_pct": "湿度 (%)",
        "precip_prob_pct": "降水確率 (%)",
        "map_settings": "地図の設定",
        "weather_overlay": "気象レイヤー",
        "map_zoom_level": "地図のズームレベル",
        "selected_city_lbl": "選択された都市",
        "coordinates_lbl": "座標",
        "elevation_lbl": "標高",
        "show_location_marker": "位置マーカーを表示",
        "overlay_temp": "気温 🌡️",
        "overlay_rain": "雨 / レーダー 🌧️",
        "overlay_wind": "風速 🌀",
        "overlay_clouds": "雲量 ☁️",
        "overlay_pressure": "気圧 🎈",
        "interactive_map_title": "インタラクティブ地図",
        "interactive_city_maps": "インタラクティブ都市気象地図",
        "global_maps_title": "世界の気象分布 (ヒートマップ・コロプレス図)",
        "global_maps_desc": "プリセット都市の気象観測データを使用した世界気温分布のマッピング。",
        "3d_state_space": "3D気象状態空間分析",
        "3d_state_space_desc": "気象パラメータ（気温、湿度、風速、降水量）の相互関係を回転させてインタラクティブに探索します。",
        "forecasting_engine": "時系列予測シミュレーションエンジン",
        "forecasting_horizon_desc": "{horizon}日間の予測期間における将来の{target}の予測。",
        "select_models_warn": "予測を実行するには、少なくとも1つのモデルを選択してください。",
        "exec_success": "モデルの実行が成功しました！",
        "eval_metrics_missing": "評価指標は利用できません。",
        "select_models_prompt": "上のボタンを使用して予測モデルを選択し、実行してください。",
        "daytime": "☀️ 昼間",
        "nighttime": "🌙 夜間",
        "eda_trends": "高度な気象トレンドと予測分析",
    },
    "中文 (Mandarin)": {
        "overview": "概览",
        "feels_like_toggle": "体感温度",
        "now": "现在",
        "precipitation_label": "降水量",
        "sunrise_sunset_cycle": "日出/日落周期激活",
        "night_sky_moon": "夜空 — 月亮可见",
        "hourly_met_forecast": "逐小时详细气象预报",
        "time_lbl": "时间",
        "temp_lbl": "温度",
        "humidity_pct": "湿度 (%)",
        "precip_prob_pct": "降水概率 (%)",
        "map_settings": "地图设置",
        "weather_overlay": "天气叠加层",
        "map_zoom_level": "地图缩放级别",
        "selected_city_lbl": "所选城市",
        "coordinates_lbl": "地理坐标",
        "elevation_lbl": "海拔",
        "show_location_marker": "显示位置标记",
        "overlay_temp": "温度 🌡️",
        "overlay_rain": "降雨 / 雷达 🌧️",
        "overlay_wind": "风速 🌀",
        "overlay_clouds": "云量 ☁️",
        "overlay_pressure": "气压 🎈",
        "interactive_map_title": "交互式地图",
        "interactive_city_maps": "交互式城市天气地图",
        "global_maps_title": "全球空间天气分布 (热力图/填色图)",
        "global_maps_desc": "使用预设城市的观察站气象数据生成全球温度分布图。",
        "3d_state_space": "3D气象状态空间特征分析",
        "3d_state_space_desc": "交互旋转和探索气象参数（温度、湿度、风力、降水量）之间的关系。",
        "forecasting_engine": "时间序列预测引擎",
        "forecasting_horizon_desc": "在未来的 {horizon} 天内预测未来的 {target}。",
        "select_models_warn": "请选择至少一个模型以运行预测。",
        "exec_success": "模型运行成功！",
        "eval_metrics_missing": "评估指标不可用。",
        "select_models_prompt": "请使用上方的按钮选择并运行预测模型。",
        "daytime": "☀️ 白天",
        "nighttime": "🌙 夜晚",
        "eda_trends": "高级天气趋势与预测分析",
    },
    "Español": {
        "overview": "Resumen",
        "feels_like_toggle": "Sensación térmica",
        "now": "Ahora",
        "precipitation_label": "Precipitación",
        "sunrise_sunset_cycle": "Ciclo de amanecer/atardecer activo",
        "night_sky_moon": "Cielo nocturno — Luna visible",
        "hourly_met_forecast": "Pronóstico Meteorológico Detallado por Hora",
        "time_lbl": "Hora",
        "temp_lbl": "Temperatura",
        "humidity_pct": "Humedad (%)",
        "precip_prob_pct": "Probabilidad de Precipitación (%)",
        "map_settings": "Configuración del Mapa",
        "weather_overlay": "Capa de Clima",
        "map_zoom_level": "Nivel de Zoom del Mapa",
        "selected_city_lbl": "Ciudad Seleccionada",
        "coordinates_lbl": "Coordenadas",
        "elevation_lbl": "Elevación",
        "show_location_marker": "Mostrar Marcador de Ubicación",
        "overlay_temp": "Temperatura 🌡️",
        "overlay_rain": "Lluvia / Radar 🌧️",
        "overlay_wind": "Viento 🌀",
        "overlay_clouds": "Nubes ☁️",
        "overlay_pressure": "Presión 🎈",
        "interactive_map_title": "Mapa Interactivo",
        "interactive_city_maps": "Mapas Climáticos Interactivos de la Ciudad",
        "global_maps_title": "Distribución Climática Espacial Global (Mapa de Calor / Coroplético)",
        "global_maps_desc": "Mapeo de las distribuciones de temperatura globales utilizando observaciones de estaciones para las ciudades predeterminadas.",
        "3d_state_space": "Análisis Tridimensional del Espacio de Estados Meteorológicos",
        "3d_state_space_desc": "Gira y explora interactivamente las relaciones de los parámetros climáticos (Temp, Humedad, Viento, Precip).",
        "forecasting_engine": "Motor de Pronóstico de Series Temporales",
        "forecasting_horizon_desc": "Pronosticando {target} futuro sobre un horizonte de {horizon} días.",
        "select_models_warn": "Por favor, seleccione al menos un modelo para ejecutar el pronóstico.",
        "exec_success": "¡Modelos ejecutados con éxito!",
        "eval_metrics_missing": "Métricas de evaluación no disponibles.",
        "select_models_prompt": "Por favor, seleccione y ejecute los modelos de pronóstico usando el botón de arriba.",
        "daytime": "☀️ Día",
        "nighttime": "🌙 Noche",
        "eda_trends": "Tendencias Climáticas Avanzadas y Pronóstico Predictivo",
    },
    "Français": {
        "overview": "Aperçu",
        "feels_like_toggle": "Ressenti",
        "now": "Maintenant",
        "precipitation_label": "Précipitations",
        "sunrise_sunset_cycle": "Cycle lever/coucher du soleil actif",
        "night_sky_moon": "Ciel nocturne — Lune visible",
        "hourly_met_forecast": "Prévisions Météorologiques Horaires Détaillées",
        "time_lbl": "Temps",
        "temp_lbl": "Température",
        "humidity_pct": "Humidité (%)",
        "precip_prob_pct": "Prob. de Précipitations (%)",
        "map_settings": "Paramètres de la Carte",
        "weather_overlay": "Couche Météo",
        "map_zoom_level": "Niveau de Zoom de la Carte",
        "selected_city_lbl": "Ville Sélectionnée",
        "coordinates_lbl": "Coordonnées",
        "elevation_lbl": "Altitude",
        "show_location_marker": "Afficher le Marqueur d'Emplacement",
        "overlay_temp": "Température 🌡️",
        "overlay_rain": "Pluie / Radar 🌧️",
        "overlay_wind": "Vent 🌀",
        "overlay_clouds": "Nuages ☁️",
        "overlay_pressure": "Pression 🎈",
        "interactive_map_title": "Carte Interactive",
        "interactive_city_maps": "Cartes Météo Interactives de la Ville",
        "global_maps_title": "Distribution Météo Spatiale Globale (Carte de Chaleur / Choroplèthe)",
        "global_maps_desc": "Cartographie des distributions mondiales de température à l'aide des observations des stations dans les villes prédéfinies.",
        "3d_state_space": "Analyse Tridimensionnelle de l'Espace d'États Météorologiques",
        "3d_state_space_desc": "Faites pivoter et explorez de manière interactive les relations des paramètres météo (Temp, Humidité, Vent, Précip).",
        "forecasting_engine": "Moteur de Prévision de Séries Temporelles",
        "forecasting_horizon_desc": "Prévision du futur {target} sur un horizon de {horizon} jours.",
        "select_models_warn": "Veuillez sélectionner au moins un modèle pour lancer la prévision.",
        "exec_success": "Modèles exécutés avec succès !",
        "eval_metrics_missing": "Métriques d'évaluation non disponibles.",
        "select_models_prompt": "Veuillez choisir et lancer les modèles de prévision avec le bouton ci-dessus.",
        "daytime": "☀️ Jour",
        "nighttime": "🌙 Nuit",
        "eda_trends": "Tendances Météo Avancées & Prévision Prédictive",
    },
    "हिन्दी": {
        "overview": "अवलोकन",
        "feels_like_toggle": "महसूस होता है",
        "now": "अभी",
        "precipitation_label": "वर्षा",
        "sunrise_sunset_cycle": "सूर्योदय/सूर्यास्त चक्र सक्रिय",
        "night_sky_moon": "रात का आकाश — चंद्रमा दिखाई दे रहा है",
        "hourly_met_forecast": "प्रति घंटा विस्तृत मौसम पूर्वानुमान",
        "time_lbl": "समय",
        "temp_lbl": "तापमान",
        "humidity_pct": "नमी (%)",
        "precip_prob_pct": "वर्षा की संभावना (%)",
        "map_settings": "मानचित्र सेटिंग्स",
        "weather_overlay": "मौसम ओवरले",
        "map_zoom_level": "मानचित्र ज़ूम स्तर",
        "selected_city_lbl": "चयनित शहर",
        "coordinates_lbl": "निर्देशांक",
        "elevation_lbl": "ऊंचाई",
        "show_location_marker": "स्थान मार्कर दिखाएं",
        "overlay_temp": "तापमान 🌡️",
        "overlay_rain": "वर्षा / रडार 🌧️",
        "overlay_wind": "हवा 🌀",
        "overlay_clouds": "बादल ☁️",
        "overlay_pressure": "वायुमंडलीय दबाव 🎈",
        "interactive_map_title": "इंटरएक्टिव मानचित्र",
        "interactive_city_maps": "इंटरएक्टिव शहर मौसम मानचित्र",
        "global_maps_title": "वैश्विक स्थानिक मौसम वितरण (हीटमैप / कोरोप्लेथ)",
        "global_maps_desc": "पूर्व-निर्धारित शहरों में मौसम स्टेशनों के अवलोकन का उपयोग करके वैश्विक तापमान वितरण का मानचित्रण।",
        "3d_state_space": "3D मौसम विज्ञान संबंधी राज्य अंतरिक्ष विश्लेषण",
        "3d_state_space_desc": "मौसम के तत्वों (तापमान, नमी, हवा, वर्षा) के संबंधों को घुमाकर देखें।",
        "forecasting_engine": "समय-श्रृंखला पूर्वानुमान इंजन",
        "forecasting_horizon_desc": "{horizon} दिनों की पूर्वानुमान अवधि में {target} का पूर्वानुमान।",
        "select_models_warn": "पूर्वानुमान लगाने के लिए कृपया कम से कम एक मॉडल चुनें।",
        "exec_success": "मॉडल सफलतापूर्वक चलाए गए!",
        "eval_metrics_missing": "मूल्यांकन मीट्रिक उपलब्ध नहीं हैं।",
        "select_models_prompt": "कृपया ऊपर दिए गए बटन का उपयोग करके पूर्वानुमान मॉडल चुनें और चलाएं।",
        "daytime": "☀️ दिन",
        "nighttime": "🌙 रात",
        "eda_trends": "उन्नत मौसम प्रवृत्तियाँ और भविष्यसूचक पूर्वानुमान",
    }
}

t = TRANSLATIONS[language].copy()
for k, v in LOCAL_TRANSLATIONS[language].items():
    t[k] = v

# Main Title and Subtitle (Sleek App Bar Layout)
st.markdown(
    f"""
    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:20px; border-bottom:1px solid rgba(255,255,255,0.08); padding-bottom:10px;">
        <h2 style="color:white; margin:0; font-size:26px; font-weight:600;">{t['title']}</h2>
        <span style="color:#94a3b8; font-size:14px;">{t['subtitle']}</span>
    </div>
    """,
    unsafe_allow_html=True,
)

st.sidebar.markdown(f"### {t['loc_select']}")
loc_mode = st.sidebar.radio(t["input_mode"], [t["preset_cities"], t["custom_coords"]])

city_name = "London"
lat, lon = 51.5074, -0.1278

if loc_mode == t["preset_cities"]:
    city_name = st.sidebar.selectbox(t["select_city"], list(PREDEFINED_CITIES.keys()))
    lat = PREDEFINED_CITIES[city_name]["lat"]
    lon = PREDEFINED_CITIES[city_name]["lon"]
else:
    search_city = st.sidebar.text_input(t["search_city"])
    if search_city:
        geo_info = geocode_city(search_city)
        if geo_info:
            city_name = geo_info["name"]
            lat = geo_info["lat"]
            lon = geo_info["lon"]
            st.sidebar.success(f"Found: {city_name} ({lat:.4f}, {lon:.4f})")
        else:
            st.sidebar.error("City not found. Using coordinates manually.")

    lat = st.sidebar.number_input("Latitude", value=lat, format="%.4f")
    lon = st.sidebar.number_input("Longitude", value=lon, format="%.4f")
    if not search_city:
        city_name = f"Custom ({lat:.2f}, {lon:.2f})"

st.sidebar.markdown(f"### {t['time_select']}")
today = datetime.date.today()
start_date = st.sidebar.date_input(t["start_date"], today - datetime.timedelta(days=3 * 365))
end_date = st.sidebar.date_input(t["end_date"], today)

st.sidebar.markdown(f"### {t['fore_settings']}")
forecast_horizon = st.sidebar.slider(t["fore_horizon"], min_value=7, max_value=365, value=90)
forecast_target = st.sidebar.selectbox(
    t["target_param"],
    [
        "temperature_2m_mean",
        "feels_like_mean",
        "relative_humidity_2m_mean",
        "surface_pressure_mean",
        "wind_speed_10m_mean",
    ],
)

# Deepseek Key override option
st.sidebar.markdown(f"### {t['api_override']}")
deepseek_key = st.sidebar.text_input(t["api_override"], type="password", placeholder=t["placeholder_api"])
active_api_key = deepseek_key if deepseek_key else API_KEY

# Fetch historical data
with st.spinner(f"Fetching weather data..."):
    df_raw = fetch_historical_weather(
        lat,
        lon,
        start_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        city_name=city_name,
    )

# Fetch real-time current conditions & short-term forecast
realtime_forecast = fetch_realtime_forecast(lat, lon)

if df_raw is None or df_raw.empty:
    st.error("Could not retrieve weather data. Please check connection and coordinates.")
    st.stop()

# Run cleaning and aggregation pipeline
df_hourly, df_daily = process_pipeline(df_raw)

# ----------------- SESSION STATE FOR NAVIGATION & UNIT -----------------
if "active_tab" not in st.session_state:
    st.session_state["active_tab"] = "Current"
if "temp_unit" not in st.session_state:
    st.session_state["temp_unit"] = "°C"

def to_f(temp_c):
    if temp_c is None:
        return None
    return (temp_c * 9/5) + 32

temp_unit = st.session_state["temp_unit"]

# Top bar with Location cards and unit selection
st.markdown('<div class="top-bar-container">', unsafe_allow_html=True)
top_cols = st.columns([1.5, 1.5, 1.5, 1.5, 2, 1])

# Fetch top cities weather (cached)
@st.cache_data(ttl=600, show_spinner=False)
def fetch_top_cities_weather():
    cities = {
        "Washington": {"lat": 38.8951, "lon": -77.0364, "alerts": 2},
        "New York": {"lat": 40.7128, "lon": -74.0060, "alerts": 2},
        "Los Angeles": {"lat": 34.0522, "lon": -118.2437, "alerts": 0},
        "Chicago": {"lat": 41.8781, "lon": -87.6298, "alerts": 1}
    }
    results = {}
    for name, coords in cities.items():
        try:
            url = f"https://api.open-meteo.com/v1/forecast?latitude={coords['lat']}&longitude={coords['lon']}&current=temperature_2m,weather_code,is_day&timezone=auto"
            res = requests.get(url, timeout=5).json()
            if "current" in res:
                results[name] = {
                    "temp": res["current"]["temperature_2m"],
                    "weather_code": res["current"]["weather_code"],
                    "is_day": res["current"].get("is_day", 1),
                    "alerts": coords["alerts"]
                }
        except Exception:
            results[name] = {"temp": 24, "weather_code": 0, "is_day": 1, "alerts": coords["alerts"]}
    return results

top_city_data = fetch_top_cities_weather()

for idx, (cname, data) in enumerate(top_city_data.items()):
    c_wicon = get_weather_icon(data["weather_code"], is_day=data.get("is_day", 1))
    raw_temp = data["temp"]
    if temp_unit == "°F":
        raw_temp = to_f(raw_temp)
    alert_badge = f'<span class="alert-badge">{data["alerts"]}</span>' if data["alerts"] > 0 else ""
    with top_cols[idx]:
        st.markdown(
            f"""
            <div class="top-city-card">
                <span style="font-weight: 600;">{cname}</span>
                <span style="color: #00ffff; margin-left: 8px; font-weight: bold;">{c_wicon} {round(raw_temp)}°</span>
                {alert_badge}
            </div>
            """,
            unsafe_allow_html=True
        )

with top_cols[4]:
    st.write("")  # Spacing

with top_cols[5]:
    # Custom unit toggle
    unit_toggle = st.radio("Unit Toggle", ["°C", "°F"], horizontal=True, label_visibility="collapsed")
    if unit_toggle != st.session_state["temp_unit"]:
        st.session_state["temp_unit"] = unit_toggle
        st.rerun()

st.markdown('</div>', unsafe_allow_html=True)


# ----------------- MAIN COLUMN LAYOUT (SIDEBAR NAV + CONTENT) -----------------
col_menu, col_content = st.columns([0.18, 0.82], gap="small")

with col_menu:
    menu_options = ["Current", "Hourly", "Details", "Maps", "Monthly", "Trends"]
    display_names = {
        "Current": "☀️ Current",
        "Hourly": "🕒 Hourly",
        "Details": "📋 Details",
        "Maps": "🗺️ Maps",
        "Monthly": "📅 Monthly",
        "Trends": "📈 Trends"
    }
    
    default_idx = menu_options.index(st.session_state["active_tab"])
    
    selected_display = st.radio(
        "Navigation",
        [display_names[opt] for opt in menu_options],
        index=default_idx,
        label_visibility="collapsed"
    )
    
    selected_opt = [k for k, v in display_names.items() if v == selected_display][0]
    if selected_opt != st.session_state["active_tab"]:
        st.session_state["active_tab"] = selected_opt
        st.rerun()


# Render active content in the content column
with col_content:
    
    # ----------------- NAV STATE: CURRENT -----------------
    if st.session_state["active_tab"] == "Current":
        if realtime_forecast and "current" in realtime_forecast:
            curr = realtime_forecast["current"]
            wcode = curr.get("weather_code", 0)
            curr_is_day = curr.get("is_day", 1)
            wicon = get_weather_icon(wcode, is_day=curr_is_day)
            
            from climatrend.src.ai_insights import WMO_CODE_MAP
            wdesc_raw = WMO_CODE_MAP.get(wcode, "Clear")
            day_night_label = "☀️ Daytime" if curr_is_day == 1 else "🌙 Nighttime"
            
            st.markdown(f"### 📡 {t['current_weather']}")
            
            col_text, col_3d = st.columns([2.5, 1.5])
            
            curr_temp = curr.get('temperature_2m')
            apparent_temp = curr.get('apparent_temperature')
            if temp_unit == "°F":
                curr_temp = to_f(curr_temp)
                apparent_temp = to_f(apparent_temp)
                
            with col_text:
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(
                        f"""
                        <div class="metric-card" style="display:flex; align-items:center; height:100px;">
                            <div class="weather-icon-inline">{wicon}</div>
                            <div>
                                <div class="metric-lbl">{city_name}</div>
                                <div class="metric-val" style="font-size:24px;">{curr_temp:.1f}{temp_unit}</div>
                                <div style="color:#94a3b8; font-size:12px; margin-top:2px;">{wdesc_raw}</div>
                            </div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(
                        f'<div class="metric-card" style="height:100px;"><div class="metric-lbl">{t["feels_like"]}</div><div class="metric-val">{apparent_temp:.1f}{temp_unit}</div></div>',
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.markdown(
                        f'<div class="metric-card" style="height:100px;"><div class="metric-lbl">{t["humidity"]}</div><div class="metric-val">{curr.get("relative_humidity_2m")}%</div></div>',
                        unsafe_allow_html=True,
                    )
                
                c4, c5, c6 = st.columns(3)
                with c4:
                    st.markdown(
                        f'<div class="metric-card" style="height:100px;"><div class="metric-lbl">{t["wind_speed"]}</div><div class="metric-val">{curr.get("wind_speed_10m")} km/h</div></div>',
                        unsafe_allow_html=True,
                    )
                with c5:
                    st.markdown(
                        f'<div class="metric-card" style="height:100px;"><div class="metric-lbl">{t["pressure"]}</div><div class="metric-val">{curr.get("surface_pressure", 1013):.0f} hPa</div></div>',
                        unsafe_allow_html=True,
                    )
                with c6:
                    st.markdown(
                        f'<div class="metric-card" style="height:100px;"><div class="metric-lbl">{t["precipitation_label"]}</div><div class="metric-val">{curr.get("precipitation", 0.0):.1f} mm</div></div>',
                        unsafe_allow_html=True,
                    )
                    
            with col_3d:
                from climatrend.src.threejs_models import get_3d_weather_model_html
                _3d_label = t["daytime"] if curr_is_day == 1 else t["nighttime"]
                st.components.v1.html(get_3d_weather_model_html(wcode, is_day=curr_is_day, label=_3d_label), height=220)
                
        st.markdown("---")
        
        col_overview_title, col_overview_toggle = st.columns([8, 2])
        with col_overview_title:
            st.markdown(f"### {t['overview']}")
        with col_overview_toggle:
            use_apparent = st.toggle(t["feels_like_toggle"], value=False)
            
        if realtime_forecast and "hourly" in realtime_forecast:
            hourly = realtime_forecast["hourly"]
            cols = st.columns(12)
            for i in range(12):
                time_str = hourly["time"][i]
                dt = pd.to_datetime(time_str)
                lbl = t["now"] if i == 0 else dt.strftime("%I %p").lstrip('0')
                wcode = hourly["weather_code"][i]
                # Determine day/night for each hourly slot (6 AM - 6 PM = day)
                hour_is_day = 1 if 6 <= dt.hour < 18 else 0
                wicon = get_weather_icon(wcode, is_day=hour_is_day)
                temp = hourly["temperature_2m"][i] if not use_apparent else hourly["apparent_temperature"][i]
                if temp_unit == "°F":
                    temp = to_f(temp)
                with cols[i]:
                    night_bg = "background: rgba(8, 15, 30, 0.7);" if hour_is_day == 0 else "background: rgba(30, 41, 59, 0.4);"
                    night_border = "border: 1px solid rgba(56, 189, 248, 0.15);" if hour_is_day == 0 else "border: 1px solid rgba(255,255,255,0.05);"
                    st.markdown(
                        f"""
                        <div style="text-align:center; {night_bg} padding: 8px; border-radius: 8px; {night_border}">
                            <div style="font-size:11px; color:#94a3b8;">{lbl}</div>
                            <div style="font-size:22px; margin: 4px 0;">{wicon}</div>
                            <div style="font-weight:600; font-size:13px; color:#f8fafc;">{round(temp)}°</div>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                    
            from climatrend.src.chart_visualizations import plot_hourly_overview_chart
            hourly_converted = hourly.copy()
            if temp_unit == "°F":
                hourly_converted["temperature_2m"] = [to_f(t) for t in hourly["temperature_2m"]]
                hourly_converted["apparent_temperature"] = [to_f(t) for t in hourly["apparent_temperature"]]

            fig_overview = plot_hourly_overview_chart(hourly_converted, use_apparent)
            st.plotly_chart(fig_overview, use_container_width=True)
            
            _day_label = t["sunrise_sunset_cycle"] if curr_is_day == 1 else t["night_sky_moon"]
            st.markdown(
                f"""
                <div style="display:flex; gap:20px; align-items:center; justify-content:center; font-size:12px; color:#94a3b8; background: rgba(12, 21, 36, 0.5); padding: 10px; border-radius: 8px; border: 1px solid rgba(255, 255, 255, 0.05);">
                    <span>🟡 <b>{t['temp_lbl']}</b></span>
                    <span>{'☀️' if curr_is_day == 1 else '🌙'} <b>{_day_label}</b></span>
                </div>
                """,
                unsafe_allow_html=True
            )

    # ----------------- NAV STATE: HOURLY -----------------
    elif st.session_state["active_tab"] == "Hourly":
        if realtime_forecast and "daily" in realtime_forecast:
            st.markdown(f"#### 🗓️ {t['forecast_7day']}")
            daily = realtime_forecast["daily"]
            wcode_today = realtime_forecast["current"].get("weather_code", 0)
            wicon = get_weather_icon(wcode_today, is_day=realtime_forecast["current"].get("is_day", 1))
            
            cols = st.columns(7)
            for idx in range(7):
                date_str = daily["time"][idx]
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                day_lbl = dt.strftime("%a\n%d %b")
                
                tmax = daily["temperature_2m_max"][idx]
                tmin = daily["temperature_2m_min"][idx]
                if temp_unit == "°F":
                    tmax = to_f(tmax)
                    tmin = to_f(tmin)
                prec_prob = daily["precipitation_probability_max"][idx]
                uv = daily["uv_index_max"][idx]
                
                with cols[idx]:
                    st.markdown(
                        f"""
                        <div class="metric-card" style="text-align:center; padding: 12px 6px;">
                            <div style="font-weight:600; font-size:13px; color:#e2e8f0; white-space:pre-line;">{day_lbl}</div>
                            <div style="font-size:24px; margin: 8px 0;">{wicon}</div>
                            <div style="font-size:14px; font-weight:700; color:#f8fafc;">{tmax:.0f}°/{tmin:.0f}°</div>
                            <div style="font-size:11px; color:#38bdf8; margin-top:5px;">💧 {prec_prob}%</div>
                            <div style="font-size:11px; color:#f43f5e; margin-top:2px;">☀️ UV {uv:.0f}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    
        st.markdown("---")
        st.markdown(f"### {t['hourly_met_forecast']}")
        
        if realtime_forecast and "hourly" in realtime_forecast:
            h_data = realtime_forecast["hourly"]
            h_df = pd.DataFrame(h_data)
            
            if temp_unit == "°F":
                h_df["temperature_2m"] = h_df["temperature_2m"].apply(to_f)
                h_df["apparent_temperature"] = h_df["apparent_temperature"].apply(to_f)
                
            h_df["time"] = pd.to_datetime(h_df["time"])
            h_df["Time (Formatted)"] = h_df["time"].dt.strftime("%Y-%m-%d %I:%M %p")
            
            display_cols = ["Time (Formatted)", "temperature_2m", "apparent_temperature", "relative_humidity_2m", "precipitation_probability"]
            h_display = h_df[display_cols].copy()
            h_display.columns = [t["time_lbl"], f"{t['temp_lbl']} ({temp_unit})", f"{t['feels_like_toggle']} ({temp_unit})", t["humidity_pct"], t["precip_prob_pct"]]
            
            st.dataframe(h_display.head(24), use_container_width=True)

    # ----------------- NAV STATE: DETAILS -----------------
    elif st.session_state["active_tab"] == "Details":
        st.markdown(f"### 📊 Historical Averages & Data ({city_name})")
        
        col1, col2, col3, col4, col5 = st.columns(5)
        avg_temp = df_daily["temperature_2m_mean"].mean()
        max_temp = df_daily["temperature_2m_max"].max()
        min_temp = df_daily["temperature_2m_min"].min()
        tot_precip = df_daily["precipitation_sum"].sum()
        avg_wind = df_daily["wind_speed_10m_mean"].mean()
        
        if temp_unit == "°F":
            avg_temp = to_f(avg_temp)
            max_temp = to_f(max_temp)
            min_temp = to_f(min_temp)

        with col1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-lbl">{t["kpi_avg_temp"]}</div><div class="metric-val">{avg_temp:.1f}{temp_unit}</div></div>',
                unsafe_allow_html=True,
            )
        with col2:
            st.markdown(
                f'<div class="metric-card"><div class="metric-lbl">{t["kpi_high_temp"]}</div><div class="metric-val">{max_temp:.1f}{temp_unit}</div></div>',
                unsafe_allow_html=True,
            )
        with col3:
            st.markdown(
                f'<div class="metric-card"><div class="metric-lbl">{t["kpi_low_temp"]}</div><div class="metric-val">{min_temp:.1f}{temp_unit}</div></div>',
                unsafe_allow_html=True,
            )
        with col4:
            st.markdown(
                f'<div class="metric-card"><div class="metric-lbl">{t["kpi_precip"]}</div><div class="metric-val">{tot_precip:.1f} mm</div></div>',
                unsafe_allow_html=True,
            )
        with col5:
            st.markdown(
                f'<div class="metric-card"><div class="metric-lbl">{t["kpi_wind"]}</div><div class="metric-val">{avg_wind:.1f} km/h</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(f"#### {t['history_data']}")
        
        df_daily_display = df_daily.copy()
        if temp_unit == "°F":
            temp_cols_daily = [c for c in df_daily.columns if "temperature" in c or "feels" in c]
            for c in temp_cols_daily:
                df_daily_display[c] = df_daily_display[c].apply(to_f)
                
        st.dataframe(df_daily_display.tail(100), use_container_width=True)

        csv = df_daily.to_csv(index=False).encode("utf-8")
        st.download_button(
            t["download_csv"],
            data=csv,
            file_name=f"climatrend_{city_name.lower()}_daily.csv",
            mime="text/csv",
        )

    # ----------------- NAV STATE: MAPS -----------------
    elif st.session_state["active_tab"] == "Maps":
        st.markdown(f"### 📍 {t['interactive_city_maps']}: **{city_name}**")
        
        # Map configuration and metadata panel
        map_col1, map_col2 = st.columns([1, 3])
        
        with map_col1:
            st.markdown(f"#### ⚙️ {t['map_settings']}")
            
            # Overlay Selection
            _overlay_options = [t["overlay_temp"], t["overlay_rain"], t["overlay_wind"], t["overlay_clouds"], t["overlay_pressure"]]
            overlay_opt = st.selectbox(
                t["weather_overlay"],
                _overlay_options,
                index=0
            )
            
            overlay_map = {
                t["overlay_temp"]: "temp",
                t["overlay_rain"]: "rain",
                t["overlay_wind"]: "wind",
                t["overlay_clouds"]: "clouds",
                t["overlay_pressure"]: "pressure"
            }
            windy_overlay = overlay_map[overlay_opt]
            
            # Zoom slider
            zoom_level = st.slider(t["map_zoom_level"], min_value=3, max_value=12, value=7)
            
            # Metric units
            metric_temp = "°C" if temp_unit == "°C" else "°F"
            metric_wind = "kmh" if temp_unit == "°C" else "mph"
            
            # Location details card
            st.markdown(
                f"""
                <div class="metric-card" style="margin-top: 15px;">
                    <div class="metric-lbl">{t['selected_city_lbl']}</div>
                    <div style="font-size: 16px; font-weight: bold; color: #00ffff; margin-bottom: 8px;">{city_name}</div>
                    <div class="metric-lbl">{t['coordinates_lbl']}</div>
                    <div style="font-size: 13px; color: #f8fafc; margin-bottom: 8px;">Lat: {lat:.4f}<br>Lon: {lon:.4f}</div>
                    <div class="metric-lbl">{t['elevation_lbl']}</div>
                    <div style="font-size: 13px; color: #f8fafc;">{realtime_forecast.get("elevation", 0.0) if realtime_forecast else 0.0} m</div>
                </div>
                """,
                unsafe_allow_html=True
            )
            
            # Interactive markers toggle
            show_marker = st.checkbox(t["show_location_marker"], value=True)
            marker_param = "true" if show_marker else ""

        with map_col2:
            # Windy Embed URL
            windy_url = (
                f"https://embed.windy.com/embed2.html?"
                f"lat={lat}&lon={lon}"
                f"&zoom={zoom_level}"
                f"&level=surface"
                f"&overlay={windy_overlay}"
                f"&menu="
                f"&message="
                f"&marker={marker_param}"
                f"&calendar=now"
                f"&pressure=true"
                f"&type=map"
                f"&location=coordinates"
                f"&detail=true"
                f"&detailLat={lat}"
                f"&detailLon={lon}"
                f"&metricWind={metric_wind}"
                f"&metricTemp={metric_temp}"
            )
            
            st.markdown(f"#### {t['interactive_map_title']}: {overlay_opt}")
            # Embedded Windy iframe
            st.components.v1.iframe(windy_url, height=520, scrolling=False)

        st.markdown("---")
        with st.expander(f"🌍 {t['global_maps_title']}"):
            st.info(t["global_maps_desc"])
            
            with st.spinner("Fetching global city meteorological data..."):
                global_map_df = load_global_map_data()

            if global_map_df.empty:
                st.warning("Could not compile global mapping dataset. Maps will not be displayed.")
            else:
                map_opt = st.selectbox(t["map_type"], [t["map_int_heat"], t["map_static_choro"], t["map_contour"]])

                global_map_display = global_map_df.copy()
                if temp_unit == "°F":
                    global_map_display["temperature_2m_mean"] = global_map_display["temperature_2m_mean"].apply(to_f)

                if map_opt == t["map_int_heat"]:
                    st.markdown(f"#### {t['map_int_heat']}")
                    folium_map = plot_interactive_folium_heatmap(global_map_display, "temperature_2m_mean")
                    try:
                        from streamlit_folium import folium_static
                        folium_static(folium_map, width=1000, height=500)
                    except ImportError:
                        st.error("Optional package 'streamlit_folium' is not installed. Install it to view the interactive map.")

                elif map_opt == t["map_static_choro"]:
                    st.markdown(f"#### {t['map_static_choro']}")
                    fig_choro = plot_static_choropleth(global_map_display, "temperature_2m_mean")
                    st.pyplot(fig_choro)
                    plt.close(fig_choro)

                elif map_opt == t["map_contour"]:
                    st.markdown(f"#### {t['map_contour']}")
                    fig_cont = plot_contour_gradient(global_map_display, "temperature_2m_mean")
                    st.pyplot(fig_cont)
                    plt.close(fig_cont)

    # ----------------- NAV STATE: MONTHLY -----------------
    elif st.session_state["active_tab"] == "Monthly":
        st.markdown("### Monthly Weather Distribution & Climatology")

        eda_col1, eda_col2 = st.columns(2)
        df_daily_converted = df_daily.copy()
        if temp_unit == "°F":
            df_daily_converted["temperature_2m_mean"] = df_daily_converted["temperature_2m_mean"].apply(to_f)

        with eda_col1:
            st.markdown(f"#### {t['eda_dist']}")
            fig_dist = plot_monthly_distribution(df_daily_converted, "temperature_2m_mean")
            st.pyplot(fig_dist)
            plt.close(fig_dist)

            st.markdown(f"#### {t['eda_cal_heat']}")
            fig_cal = plot_calendar_heatmap(df_daily_converted, "temperature_2m_mean")
            st.pyplot(fig_cal)
            plt.close(fig_cal)

        with eda_col2:
            st.markdown(f"#### {t['eda_precip']}")
            fig_prec = plot_bar_averages(df_daily, "precipitation_sum", freq="monthly")
            st.pyplot(fig_prec)
            plt.close(fig_prec)

            st.markdown(f"#### {t['eda_wind']}")
            fig_wind = plot_wind_rose(df_daily)
            st.pyplot(fig_wind)
            plt.close(fig_wind)

    # ----------------- NAV STATE: TRENDS -----------------
    elif st.session_state["active_tab"] == "Trends":
        st.markdown(f"### {t['eda_trends']}")
        
        st.markdown(f"#### {t['3d_state_space']}")
        st.info(t["3d_state_space_desc"])
        from climatrend.src.chart_visualizations import plot_3d_weather_trends
        fig_3d = plot_3d_weather_trends(df_daily)
        st.plotly_chart(fig_3d, use_container_width=True)
        st.markdown("---")

        st.markdown(f"#### {t['forecasting_engine']}")
        st.write(t["forecasting_horizon_desc"].format(target=forecast_target.replace('_', ' ').title(), horizon=forecast_horizon))

        val_days = 30
        train_df, test_df = train_test_split_ts(df_daily, test_size_days=val_days)

        model_opts = st.multiselect(t["fore_models"], ["Prophet", "SARIMA", "Random Forest Regressor", "Linear Regression"], default=["Prophet", "Random Forest Regressor"])

        if not model_opts:
            st.warning(t["select_models_warn"])
        else:
            forecast_results = {}
            model_metrics = {}

            if st.button(t["fore_btn"]):
                progress = st.progress(0.0)
                total_models = len(model_opts)

                from climatrend.src.forecasting_model import (
                    fit_forecast_prophet,
                    fit_forecast_sarima,
                    fit_forecast_ml,
                )

                for idx, model_name in enumerate(model_opts):
                    st.spinner(f"Training {model_name}...")

                    if model_name == "Prophet":
                        try:
                            import prophet
                            f_df, met = fit_forecast_prophet(train_df, test_df, forecast_horizon, forecast_target)
                            if not f_df.empty:
                                forecast_results[model_name] = f_df
                                model_metrics[model_name] = met
                        except ImportError:
                            st.error("Prophet package is missing in environment. Cannot execute Prophet.")
                    elif model_name == "SARIMA":
                        f_df, met = fit_forecast_sarima(train_df, test_df, forecast_horizon, forecast_target)
                        if not f_df.empty:
                            forecast_results[model_name] = f_df
                            model_metrics[model_name] = met
                    elif model_name == "Random Forest Regressor":
                        f_df, met = fit_forecast_ml(train_df, test_df, forecast_horizon, forecast_target, "random_forest")
                        if not f_df.empty:
                            forecast_results[model_name] = f_df
                            model_metrics[model_name] = met
                    elif model_name == "Linear Regression":
                        f_df, met = fit_forecast_ml(train_df, test_df, forecast_horizon, forecast_target, "linear_regression")
                        if not f_df.empty:
                            forecast_results[model_name] = f_df
                            model_metrics[model_name] = met

                    progress.progress((idx + 1) / total_models)

                st.session_state["forecast_results"] = forecast_results
                st.session_state["model_metrics"] = model_metrics
                st.success(t["exec_success"])

            forecast_results = st.session_state.get("forecast_results", {})
            model_metrics = st.session_state.get("model_metrics", {})

            if forecast_results:
                st.markdown(f"#### {t['fore_plot_title']}")

                fig_forecast = go.Figure()

                hist_plot = df_daily.tail(365)
                y_hist = hist_plot[forecast_target].values
                if temp_unit == "°F" and "temperature" in forecast_target:
                    y_hist = [to_f(val) for val in y_hist]
                    
                fig_forecast.add_trace(
                    go.Scatter(
                        x=hist_plot["time"],
                        y=y_hist,
                        name="Historical",
                        line=dict(color="rgb(71, 85, 105)", width=2),
                    )
                )

                model_colors = {
                    "Prophet": "rgb(224, 122, 95)",
                    "SARIMA": "rgb(129, 178, 154)",
                    "Random Forest Regressor": "rgb(61, 64, 91)",
                    "Linear Regression": "rgb(242, 204, 143)",
                }

                for model_name, f_df in forecast_results.items():
                    y_fore = f_df["forecast"].values
                    y_up = f_df["upper_ci"].values
                    y_low = f_df["lower_ci"].values
                    
                    if temp_unit == "°F" and "temperature" in forecast_target:
                        y_fore = [to_f(val) for val in y_fore]
                        y_up = [to_f(val) for val in y_up]
                        y_low = [to_f(val) for val in y_low]
                        
                    fig_forecast.add_trace(
                        go.Scatter(
                            x=f_df["time"],
                            y=y_fore,
                            name=f"Forecast ({model_name})",
                            line=dict(color=model_colors.get(model_name, "rgb(0,0,0)"), width=2),
                        )
                    )
                    if len(model_opts) == 1 or model_name == model_opts[0]:
                        fig_forecast.add_trace(
                            go.Scatter(
                                x=f_df["time"],
                                y=y_up,
                                line=dict(width=0),
                                showlegend=False,
                                mode="lines",
                            )
                        )
                        fig_forecast.add_trace(
                            go.Scatter(
                                x=f_df["time"],
                                y=y_low,
                                fill="tonexty",
                                fillcolor=model_colors.get(model_name, 'rgb(0,0,0)').replace("rgb", "rgba").replace(")", ", 0.15)"),
                                line=dict(width=0),
                                name=f"95% Confidence Band ({model_name})",
                                mode="lines",
                            )
                        )

                fig_forecast.update_layout(
                    xaxis_title="Date",
                    yaxis_title=forecast_target.replace("_", " ").title() + f" ({temp_unit})" if "temperature" in forecast_target else forecast_target.replace("_", " ").title(),
                    hovermode="x unified",
                    template="plotly_white",
                    height=500,
                )

                st.plotly_chart(fig_forecast, use_container_width=True)

                st.markdown(f"#### {t['fore_comp']}")
                metrics_df = pd.DataFrame(model_metrics).transpose()
                if not metrics_df.empty:
                    st.dataframe(metrics_df.style.highlight_min(axis=0, color="#1e3a8a"), use_container_width=True)
                else:
                    st.info(t["eval_metrics_missing"])
            else:
                st.info(t["select_models_prompt"])

        st.markdown("---")
        
        dec_col1, dec_col2 = st.columns([2, 1])
        df_daily_converted = df_daily.copy()
        if temp_unit == "°F":
            df_daily_converted["temperature_2m_mean"] = df_daily_converted["temperature_2m_mean"].apply(to_f)

        with dec_col1:
            st.markdown(f"#### {t['eda_decomp']}")
            obs, trend_s, seas, resid = perform_seasonal_decomposition(df_daily_converted, "temperature_2m_mean")
            fig_decomp = plot_seasonal_decomposition(obs, trend_s, seas, resid)
            st.pyplot(fig_decomp)
            plt.close(fig_decomp)

        with dec_col2:
            st.markdown(f"#### {t['eda_acf']}")
            acf_v, pacf_v = compute_acf_pacf(df_daily_converted, "temperature_2m_mean")
            fig_acf = plot_acf_pacf(acf_v, pacf_v)
            st.pyplot(fig_acf)
            plt.close(fig_acf)

        st.markdown("---")

        st.markdown(f"### {t['ai_title']}")
        st.write(t["ai_descr"])

        if st.button(t["ai_btn"]):
            if not forecast_results:
                st.warning(t["ai_warn"])
            else:
                with st.spinner(t["ai_spinner"]):
                    primary_model = list(forecast_results.keys())[0]
                    primary_forecast = forecast_results[primary_model]

                    sum_stats = generate_summary_statistics(df_daily)

                    report_stream = get_ai_insight(
                        location_name=city_name,
                        summary_stats=sum_stats,
                        forecast_results=primary_forecast,
                        model_metrics=model_metrics,
                        realtime_data=realtime_forecast,
                        language=language,
                        api_key=active_api_key,
                        stream=True,
                    )

                    st.write_stream(report_stream)

        # ----------------- COLLAPSIBLE MATH NOTES -----------------
        st.markdown("---")
        with st.expander("🧠 Mathematical Details & Methods"):
            st.markdown(
                """
                #### 🧠 Mathematical Forecasting Methods
                
                *   **Prophet (Additive Seasonality)**:
                    Models time-series using a piecewise linear growth trend combined with yearly and weekly periodic Fourier components. Formulated as:
                    $$y(t) = g(t) + s(t) + h(t) + \\epsilon_t$$
                    where $g(t)$ is trend, $s(t)$ represents seasonality, $h(t)$ models holidays, and $\\epsilon_t$ is standard error.
                    
                *   **SARIMAX (Classical Statistical Model)**:
                    Seasonal Autoregressive Integrated Moving Average with Exogenous regressors. Stepwise auto-selection fits components:
                    $$(p, d, q) \\times (P, D, Q)_m$$
                    where AR captures lag effects, Integrated handles differencing for stationarity, and MA tracks residuals.
                    
                *   **Recursive Lag Machine Learning**:
                    Transforms time-series forecasting into tabular regression. Lag variables ($1, 2, 7, 30, 365$ days) and rolling statistics are calculated recursively step-by-step to predict future values.
                
                #### 🛰️ Data Integrity & Features
                
                *   **Open-Meteo API**:
                    Retrieves gridded historical weather data, current observations, and short-term forecasting grids. Includes support for temperature, humidity, wind, rainfall, cloud cover, pressure, and UV index.
                    
                *   **Vector Wind Averaging**:
                    Computes dominant wind direction angles using trigonometric averages of the sine and cosine wind vectors to avoid wrap-around calculation errors:
                    $$\\theta_{\\text{avg}} = \\text{atan2}(\\overline{\\sin(\\theta)}, \\overline{\\cos(\\theta)})$$
                """
            )


