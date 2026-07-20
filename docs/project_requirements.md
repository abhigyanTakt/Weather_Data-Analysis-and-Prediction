# 🌦️ ClimaTrend — Project Requirements Document (PRD)

This document outlines the core requirements, target user personas, and functional features of **ClimaTrend**, a full-stack weather intelligence platform that combines real-time weather monitoring, spatial maps, machine learning forecasting, and AI-driven insights.

---

## 🚀 1. What to Build

**ClimaTrend** is a premium, open-source weather analysis and forecasting application built using Python and Streamlit. The application serves as a comprehensive dashboard that bridges the gap between raw meteorological data, classical/modern statistical forecasting, and generative AI explanations.

### Key Objectives & System Components
1. **Interactive Web Dashboard**: A single, unified dashboard built in **Streamlit** that offers a responsive, glassmorphic layout.
2. **Data Acquisition & Engineering Pipeline**: 
   - Geocodes location inputs automatically using the **Open-Meteo Geocoding API**.
   - Fetches historical and real-time hourly/daily data using the **Open-Meteo Archive API**.
   - Computes advanced secondary metrics such as trigonometric wind vectors (averaging sine/cosine components to prevent $360^\circ \to 0^\circ$ wrap-around errors) and feels-like indexes (Apparent Heat Index & Wind Chill).
3. **Exploratory Data Analysis (EDA)**: Offers graphical analyses of monthly weather distributions, parameter correlations, calendar-based trends, and seasonal components.
4. **Machine Learning Forecasting Engine**: Evaluates and compares four distinct mathematical models (Prophet, SARIMA, Random Forest Regressor, and Linear Regression) to predict key weather parameters (temperature, humidity, pressure, etc.) with 95% confidence bands and error metric side-by-side tables.
5. **AI Climate Insights**: Leverages the **DeepSeek-V4 Pro** model via NVIDIA's API endpoint to generate localized, natural-language narrative reports summarizing weather history, predictions, and model performance.
6. **Immersive User Experience**: Incorporates interactive 3D visualizations (Three.js and Plotly 3D scatter plots), switchable language localization across 6 major languages, and local video wallpaper backgrounds.

---

## 👥 2. Targeted Users

ClimaTrend is designed to serve a diverse group of users, each with distinct needs and technical backgrounds:

### 1. Citizen Scientists & Weather Enthusiasts
* **Need**: Access to detailed meteorological data, historical comparisons, and advanced charts (e.g., wind rose plots, seasonal trends) beyond standard weather apps.
* **Benefit**: Intuitive visualizations and feature-engineered metrics like Wind Chill and Heat Index.

### 2. Data Scientists & Machine Learning Practitioners
* **Need**: A showcase of how classical statistical models (SARIMA), additive forecasting models (Prophet), and lag-recursive machine learning algorithms (Random Forest) perform on real-world time-series data.
* **Benefit**: Clear evaluation metrics (RMSE, MAE, MAPE), model comparison tables, and parameter settings.

### 3. General Public & Everyday Users
* **Need**: A quick, visually appealing summary of today's weather, upcoming forecasts, and local conditions in their native language.
* **Benefit**: Easy-to-read cards, interactive map overlays, and natural-language AI weather summaries.

### 4. AI & Full-Stack Developers
* **Need**: Reference implementation for integrating LLM APIs (DeepSeek-V4) and 3D rendering (Three.js) into Streamlit applications.
* **Benefit**: Modular code structure, standard API integrations, and robust internationalization.

---

## ✨ 3. Features

The ClimaTrend platform is organized around the following key functional modules:

### 📡 A. Real-Time Weather & Forecast
* **Current Conditions Header**: Live temperature, apparent temp, humidity, wind speed, pressure, precipitation, and UV index.
* **Hourly Strip**: A scrollable 48-hour outlook indicating time, temperature, weather conditions, and day/night state.
* **Weekly Outlook**: A 7-day weather card layout highlighting maximum/minimum temperatures and daily precipitation probability.
* **3D Animated Weather State**: A Three.js-rendered visual card animating atmospheric conditions (e.g., sun, clouds, moon phase) dynamically matching the selected city's state.

### 🗺️ B. Interactive Mapping & Gradients
* **Windy.com Live Embed**: A high-fidelity, interactive map panel centered on the selected city.
  - Supports live toggling of overlays: **Temperature**, **Rain/Radar**, **Wind**, **Clouds**, and **Pressure**.
  - Interactive controls for zoom scale (levels 3 to 12) and location marker visibility.
* **Static Geospatial Gradients**: Heatmaps, choropleths, and contour gradient lines mapping historical regional weather distributions.

### 📊 C. Historical EDA Dashboard
* **Seasonal Distribution**: Monthly violin and box plots showing data variance over the preceding year.
* **Correlation Heatmap**: Coefficients calculated and plotted across all weather parameters (e.g., how wind speed affects apparent temperature).
* **Wind Rose Polar Charts**: Histogram showing wind speed frequencies grouped by cardinal directions.
* **Calendar Heatmap Grid**: Grid layout mapping daily averages of any selected weather metric over a 365-day period.

### 🔮 D. Multi-Model Forecasting Engine
Runs multiple forecasting pipelines in parallel to predict future weather trends:
* **Prophet**: Models long-term trends alongside weekly/yearly periodic Fourier components.
* **SARIMA**: Fits classical statistical coefficients using stepwise auto-selection of AR (p), differencing (d), and MA (q) parameters.
* **Recursive Lag ML**: Formulates prediction as a regression task using lags (1, 2, 7, 30, and 365 days) and rolling averages, fitted with **Random Forest** or **Linear Regression**.
* **Metrics Table**: Evaluates performance dynamically using **RMSE**, **MAE**, and **MAPE** on test slices.
* **Seasonality Breakdown**: Displays trend, seasonal, and residual components along with ACF & PACF graphs.

### 🤖 E. AI Climate Reports (DeepSeek-V4)
* **Natural-Language Summary**: One-click generation of a expert-level weather analysis.
* **Multilingual Output**: Auto-translated to the active user language.
* **Insight Depth**: Comments on historical extremes, forecast anomalies, and recommends which model (Prophet vs. SARIMA) is currently more reliable.

### 🌐 F. Interface & UI Aesthetics
* **Glassmorphism Theme**: Translucent dark mode cards utilizing `backdrop-filter` blur and thin borders.
* **Smooth Transitions**: Hover and micro-animations on cards and controls.
* **Internationalization**: Full localization supporting English (`en`), 日本語 (`ja`), 中文 (`zh`), Español (`es`), Français (`fr`), and हिन्दी (`hi`).
* **Live Video Wallpaper**: Seamlessly loops local meteorological background assets.
