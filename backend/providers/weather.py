"""
Weather provider -- Open-Meteo forecast API. Free, no API key required.
"""
from __future__ import annotations

import httpx

from config import settings
from models import DataSource, WeatherInfo
from providers.cache import weather_cache

_WEATHER_CODE_DESCRIPTIONS = {
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
    71: "Slight snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
    96: "Thunderstorm with hail",
    99: "Severe thunderstorm with hail",
}


async def get_weather(lat: float, lon: float) -> WeatherInfo | None:
    cache_key = f"{lat:.3f},{lon:.3f}"
    cached = weather_cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code",
        "hourly": "precipitation_probability",
        "timezone": "Asia/Kolkata",
        "forecast_days": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.get(settings.OPEN_METEO_WEATHER_URL, params=params)
            resp.raise_for_status()
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None

    current = data.get("current", {})
    hourly = data.get("hourly", {})
    rain_prob = None
    probs = hourly.get("precipitation_probability") or []
    if probs:
        rain_prob = probs[0]

    weather_code = current.get("weather_code")
    info = WeatherInfo(
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        precipitation_mm=current.get("precipitation"),
        rain_probability_pct=rain_prob,
        wind_speed_kmh=current.get("wind_speed_10m"),
        condition=_WEATHER_CODE_DESCRIPTIONS.get(weather_code, "Unknown"),
        source=DataSource.LIVE,
    )
    weather_cache.set(cache_key, info, settings.CACHE_TTL_WEATHER)
    return info
