# 🌦️ ClimaTrend — Weather Analysis & Forecasting Dashboard

<div align="center">

![ClimaTrend Banner](climatrend/logo.jpg)

**A full-stack weather intelligence platform built with Python & Streamlit**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.x-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)](https://streamlit.io)

</div>

---

## 🧠 What is ClimaTrend?

**ClimaTrend** is a premium, open-source weather analytics dashboard that combines **real-time meteorological data**, **ML-powered time-series forecasting**, **interactive maps**, and **AI-generated insights** — all in one beautiful, multilingual interface.

Whether you're tracking your city's climate trends, exploring global weather patterns, or running predictive models, ClimaTrend delivers a professional-grade experience right in your browser.

---

## ✨ Features

### 📡 Real-Time Weather
- Live current conditions — temperature, humidity, wind speed, pressure, precipitation, UV index
- Hourly 48-hour forecast strip with day/night detection
- 7-day daily forecast cards with max/min temps and precipitation probability
- Dynamic 3D animated weather model (Three.js) showing clouds / moon based on current conditions

### 🗺️ Interactive Maps
- **Windy.com** embedded live weather maps centered on the selected city
- Switchable overlays: **Temperature**, **Rain/Radar**, **Wind**, **Clouds**, **Pressure**
- Adjustable zoom level (3–12)
- Location marker toggle
- Global weather distribution maps (Folium heatmap, choropleth, contour gradient)

### 📊 Historical Analysis (1-Year Data)
- Hourly → Daily aggregated pipeline with feature engineering
- Monthly violin plots, calendar heatmaps, wind rose charts
- Correlation heatmap across all weather variables
- Precipitation and wind bar averages

### 🤖 ML Forecasting Engine
Runs multiple models in parallel for any chosen weather variable:
| Model | Type |
|---|---|
| **Prophet** | Additive seasonality (trend + Fourier) |
| **SARIMA** | Classical statistical auto-selection |
| **Random Forest Regressor** | Recursive lag-based ML |
| **Linear Regression** | Baseline lag-based ML |

- 95% confidence interval bands
- Side-by-side model comparison with MAE, RMSE, MAPE metrics
- Seasonal decomposition (trend / seasonal / residual)
- ACF & PACF analysis

### 🌐 Multilingual Support (6 Languages)
| Language | Code |
|---|---|
| English | `en` |
| 日本語 (Japanese) | `ja` |
| 中文 Mandarin | `zh` |
| Español | `es` |
| Français | `fr` |
| हिन्दी (Hindi) | `hi` |

### 🤖 AI Climate Insights
- Powered by **DeepSeek-V4 Pro** via NVIDIA's API endpoint
- Generates a full natural-language climate report in the selected language
- Covers historical stats, forecast trends, and model performance

### 🎥 Immersive UI
- Live **video wallpaper** background served from a local HTTP server
- Glassmorphism card design with `backdrop-filter` blur
- Smooth micro-animations and hover effects
- Full dark mode with curated color palette

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend / App** | [Streamlit](https://streamlit.io) |
| **3D Graphics** | [Three.js](https://threejs.org) (via HTML component) |
| **Maps** | [Windy.com Embed API](https://api.windy.com/embed), [Folium](https://python-visualization.github.io/folium/) |
| **Charting** | [Plotly](https://plotly.com/python/), [Matplotlib](https://matplotlib.org/) |
| **ML Models** | [Prophet](https://facebook.github.io/prophet/), [statsmodels](https://www.statsmodels.org/) SARIMA, [scikit-learn](https://scikit-learn.org/) |
| **Data Source** | [Open-Meteo API](https://open-meteo.com/) (free, no key needed) |
| **Geocoding** | [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) |
| **AI** | [DeepSeek-V4 Pro](https://www.deepseek.com/) via [NVIDIA API](https://integrate.api.nvidia.com/) |
| **Language** | Python 3.10+ |
| **Env Management** | [python-dotenv](https://pypi.org/project/python-dotenv/) |

---

---

## 📁 Project Structure

```
Weather_Data-Analysis-and-Prediction/
├── .env.example              # 🔑 API key template (safe to commit)
├── .gitignore
├── requirements.txt
└── climatrend/
    ├── app.py                # 🏠 Main Streamlit application
    ├── logo.jpg
    ├── verify.py             # ✅ Regression test script
    └── src/
        ├── ai_insights.py        # 🤖 DeepSeek AI report generation
        ├── chart_visualizations.py  # 📊 Plotly + Matplotlib charts
        ├── data_acquisition.py   # 📡 Open-Meteo API client
        ├── data_cleaning.py      # 🧹 Feature engineering pipeline
        ├── eda.py                # 📈 Seasonal decomposition, ACF/PACF
        ├── forecasting_model.py  # 🔮 Prophet, SARIMA, ML models
        ├── map_visualizations.py # 🗺️ Folium heatmap, choropleth
        ├── threejs_models.py     # 🌩️ 3D animated weather card
        └── translations.py       # 🌐 6-language i18n dictionary
```

---

## 📸 Screenshots or Demo will be at my linkdin post

> _Coming soon_

---

## ⚙️ Configuration

| Setting | Where to change |
|---|---|
| API Key (NVIDIA/DeepSeek) | `.env` → `NVIDIA_API_KEY` |
| Wallpaper video path | `app.py` → `start_background_wallpaper_server()` → `directory` |
| Default city list | `app.py` → `PREDEFINED_CITIES` dict |
| Forecast horizon | Sidebar slider in the **Trends** tab |
| Temperature unit (°C/°F) | Sidebar toggle |

---

## 🧮 Forecasting Methods

### Prophet (Additive Seasonality)
$$y(t) = g(t) + s(t) + h(t) + \epsilon_t$$
where $g(t)$ = trend, $s(t)$ = seasonality, $h(t)$ = holidays, $\epsilon_t$ = error.

### SARIMAX
$$(p, d, q) \times (P, D, Q)_m$$
Stepwise auto-selection of AR, differencing, and MA components with seasonal period $m$.

### Recursive Lag ML
Transforms forecasting into tabular regression using lag features at $1, 2, 7, 30, 365$ days plus rolling statistics — fitted with Random Forest or Linear Regression.

---

## 🤝 Contributing

Pull requests are welcome! For major changes, please open an issue first to discuss what you'd like to change.

1. Fork the repo
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📜 License

This project was built and is maintained by **Abhigyan**. Feel free to use it for learning and personal projects. Give credit if you build on top of it! 🙌

---

## 🙏 Acknowledgements

- [Open-Meteo](https://open-meteo.com/) — free, open-source weather API
- [Windy.com](https://www.windy.com/) — beautiful live weather maps
- [Three.js](https://threejs.org/) — 3D graphics in the browser
- [Facebook Prophet](https://facebook.github.io/prophet/) — time-series forecasting
- [NVIDIA NIM](https://integrate.api.nvidia.com/) — AI inference API
- [DeepSeek](https://www.deepseek.com/) — the underlying language model

---

<div align="center">
Made with ❤️ by <a href="https://github.com/abhigyanTakt">Abhigyan</a>
</div>
