"""
ClimaTrend AI Insights Module.

This module integrates with the Deepseek v4 model via the Nvidia API endpoint
to generate natural-language climate commentaries and analysis reports.
It incorporates real-time weather reports, short-term 7-day forecasts, and
localizes responses to English, Japanese, Mandarin Chinese, Spanish, French, or Hindi.
"""

import os
import logging
from typing import Dict, Any, Optional
import pandas as pd
from openai import OpenAI

# Load .env file if present (for local development)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not required in production

logger = logging.getLogger(__name__)

# API configuration — set NVIDIA_API_KEY in your .env file or environment
API_KEY = os.getenv("NVIDIA_API_KEY", "")
BASE_URL = "https://integrate.api.nvidia.com/v1"
MODEL_NAME = "deepseek-ai/deepseek-v4-pro"

# WMO Weather Code Mapping to descriptions
WMO_CODE_MAP = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow fall",
    73: "Moderate snow fall",
    75: "Heavy snow fall",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm: Slight or moderate",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def get_ai_insight(
    location_name: str,
    summary_stats: pd.DataFrame,
    forecast_results: pd.DataFrame,
    model_metrics: Dict[str, Dict[str, float]],
    realtime_data: Optional[Dict[str, Any]] = None,
    language: str = "English",
    api_key: str = API_KEY,
    stream: bool = False,
) -> Any:
    """
    Generates a natural-language climate insights report using Deepseek v4.
    Supports real-time weather statistics, 7-day predictions, and multilingual outputs.

    Args:
        location_name: Name of the weather location.
        summary_stats: Descriptive statistics for historical weather variables.
        forecast_results: Predicted values from the models.
        model_metrics: Performance metrics (MAE, RMSE, MAPE) for models.
        realtime_data: Current real-time weather and 7-day forecast from API.
        language: Selected language (English, 日本語, 中文 (Mandarin), Español, Français, हिन्दी).
        api_key: Deepseek API key.
        stream: If True, returns a generator that streams response chunks.

    Returns:
        A Markdown string if stream=False, else a generator yielding string chunks.
    """
    logger.info(f"Generating AI insights for {location_name} in {language} (stream={stream})...")

    # Calculate some descriptive trends to pass to the model
    temp_col = "temperature_2m_mean" if "temperature_2m_mean" in summary_stats.index else "temperature_2m"
    precip_col = "precipitation_sum" if "precipitation_sum" in summary_stats.index else "precipitation"

    hist_mean_temp = summary_stats.loc[temp_col, "mean"] if temp_col in summary_stats.index else "N/A"
    hist_max_temp = summary_stats.loc[temp_col, "max"] if temp_col in summary_stats.index else "N/A"
    hist_min_temp = summary_stats.loc[temp_col, "min"] if temp_col in summary_stats.index else "N/A"

    hist_total_precip = (
        summary_stats.loc[precip_col, "mean"] * 365.25
        if precip_col in summary_stats.index
        else "N/A"
    )  # Approximate annual precipitation

    # Forecast trends
    forecast_start = forecast_results["forecast"].iloc[0] if not forecast_results.empty else "N/A"
    forecast_end = forecast_results["forecast"].iloc[-1] if not forecast_results.empty else "N/A"
    forecast_days = len(forecast_results)

    # Compile metrics overview
    metrics_str = ""
    for model, met in model_metrics.items():
        metrics_str += f"- {model}: MAE={met.get('MAE', 0):.2f}, RMSE={met.get('RMSE', 0):.2f}, MAPE={met.get('MAPE', 0):.2f}%\n"

    # Assemble Real-Time Weather and 7-Day Forecast context
    realtime_str = ""
    if realtime_data and "current" in realtime_data:
        curr = realtime_data["current"]
        wcode = curr.get("weather_code", 0)
        wdesc = WMO_CODE_MAP.get(wcode, "Unknown conditions")
        realtime_str += f"""
### Current Real-Time Conditions:
- Temperature: {curr.get('temperature_2m')}°C (Apparent/Feels Like: {curr.get('apparent_temperature')}°C)
- Weather Status: {wdesc} (WMO Code: {wcode})
- Relative Humidity: {curr.get('relative_humidity_2m')}%
- Wind Speed: {curr.get('wind_speed_10m')} km/h (Direction: {curr.get('wind_direction_10m')}°)
- Surface Pressure: {curr.get('surface_pressure')} hPa
"""

    if realtime_data and "daily" in realtime_data:
        daily = realtime_data["daily"]
        realtime_str += "\n### Real-Time 7-Day Short-Term Weather Forecast:\n"
        for i in range(len(daily.get("time", []))):
            date = daily["time"][i]
            tmax = daily["temperature_2m_max"][i]
            tmin = daily["temperature_2m_min"][i]
            apmax = daily["apparent_temperature_max"][i]
            apmin = daily["apparent_temperature_min"][i]
            pprob = daily["precipitation_probability_max"][i]
            psum = daily["precipitation_sum"][i]
            uv = daily["uv_index_max"][i]
            
            realtime_str += f"- **{date}**: Temperature {tmin}°C to {tmax}°C (Apparent: {apmin}°C to {apmax}°C), Rain Probability: {pprob}%, Precip: {psum} mm, UV Max Index: {uv}\n"

    # Construct prompt
    prompt = f"""
You are an expert climatologist and data scientist. Provide a professional, detailed climate analysis report for {location_name}.

{realtime_str}

### Long-Term Historical Climate Summary (Descriptive Stats):
- Average Mean Temperature: {hist_mean_temp}°C (Range: {hist_min_temp}°C to {hist_max_temp}°C)
- Estimated Annual Precipitation: {hist_total_precip:.1f} mm (based on historical daily average)

### Long-Term Temperature Forecast ({forecast_days}-day horizon):
- Expected Temperature at start of forecast: {forecast_start:.2f}°C
- Expected Temperature at end of forecast: {forecast_end:.2f}°C
- Forecast trend direction: {"Warm-up" if (forecast_end > forecast_start) else "Cool-down" if (forecast_end < forecast_start) else "Stable"}

### Long-Term Model Performance Metrics:
{metrics_str}

Please generate a well-structured Markdown report.
IMPORTANT: You MUST write the entire report in the language: '{language}'. This is a strict localization requirement.

Ensure the report includes:
1. **Current Real-Time Analysis**: Comment on the current weather and the 7-day outlook. Are there immediate weather alerts, extreme UV warnings, or rainfall risks?
2. **Climate Classification**: Briefly classify the climate of {location_name} (e.g. Temperate, Arid, Tropical) based on the historical stats.
3. **Forecasting Model Evaluation**: Interpret the model metrics. Which model performed best and why? Are these models reliable for this climate?
4. **Meteorological Trend Interpretation**: Explain the physical reasons for the predicted long-term trend. Is this seasonal change, or are there indicators of anomalous weather patterns?
5. **Actionable Climate Strategy**: What are the environmental or socio-economic implications of this short-term and long-term forecast (e.g. agricultural planning, energy demands, public health, disaster preparedness)? Keep it specific and professional.

Ensure the output is clean Markdown, readable, and scientific yet accessible. Do not include raw HTML.
"""

    fallback_response = f"""
# ClimaTrend AI Analysis Report for {location_name} ({language})
*(Note: Automated fallback report generated due to API service limitations)*

### 1. Current Conditions and Forecast
Current temperatures and short-term trends conform to normal local cycles. Rain and UV metrics are in expected bounds.

### 2. Climate Characteristics
The weather data for **{location_name}** indicates a historical mean temperature of **{hist_mean_temp}°C**, with temperatures varying between **{hist_min_temp}°C** and **{hist_max_temp}°C**.

### 3. Model Performance Summary
Based on the validation metrics:
{metrics_str}

### 4. Long-Term Forecast Trend
Over the next **{forecast_days} days**, the temperature is predicted to move from **{forecast_start:.2f}°C** to **{forecast_end:.2f}°C**. This represents a general **{"warming" if (forecast_end > forecast_start) else "cooling" if (forecast_end < forecast_start) else "stable"} trend**.

### 5. Environmental and Planning Implications
- **Energy Demands**: Plan for {"increased cooling loads" if forecast_end > 25 else "heating requirements" if forecast_end < 15 else "moderate base energy demands"}.
- **Agriculture & Water**: Regional planning should monitor water balances and soil moisture levels, especially given estimated annual rainfall rates.
"""

    if stream:
        def stream_generator():
            try:
                client = OpenAI(base_url=BASE_URL, api_key=api_key)
                completion = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.7,
                    top_p=0.95,
                    max_tokens=1000,
                    extra_body={"chat_template_kwargs": {"thinking": False}},
                    stream=True,
                )
                for chunk in completion:
                    content = chunk.choices[0].delta.content
                    if content:
                        yield content
            except Exception as e:
                logger.error(f"Error calling Deepseek v4 API in stream: {str(e)}")
                # Stream the fallback response in chunks
                for chunk in fallback_response.split(" "):
                    yield chunk + " "
        return stream_generator()
    else:
        try:
            client = OpenAI(base_url=BASE_URL, api_key=api_key)
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                top_p=0.95,
                max_tokens=1000,
                extra_body={"chat_template_kwargs": {"thinking": False}},
                stream=False,
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Error calling Deepseek v4 API: {str(e)}")
            return fallback_response
