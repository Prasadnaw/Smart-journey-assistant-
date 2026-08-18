"""
Weather provider -- Open-Meteo forecast API.
Free and does not require an API key.
"""

from __future__ import annotations

import httpx

from models import DataSource, WeatherInfo
from providers.cache import weather_cache


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


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
    56: "Freezing drizzle",
    57: "Freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
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
        "current": (
            "temperature_2m,"
            "apparent_temperature,"
            "precipitation,"
            "wind_speed_10m,"
            "weather_code"
        ),
        "hourly": "precipitation_probability",
        "timezone": "Asia/Kolkata",
        "forecast_days": 1,
    }

    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            headers={
                "User-Agent": "JourneyAI-India/1.0"
            },
        ) as client:

            response = await client.get(
                OPEN_METEO_URL,
                params=params,
            )

            # This will make Render logs much more useful if Open-Meteo
            # returns an error.
            response.raise_for_status()

            data = response.json()

    except httpx.HTTPStatusError as exc:
        print(
            "Open-Meteo HTTP error:",
            exc.response.status_code,
            exc.response.text,
        )
        return None

    except (httpx.HTTPError, ValueError) as exc:
        print("Open-Meteo request error:", repr(exc))
        return None

    current = data.get("current")

    if not current:
        print("Open-Meteo returned no current weather data:", data)
        return None

    hourly = data.get("hourly") or {}

    probabilities = hourly.get("precipitation_probability") or []

    rain_probability = None

    if probabilities:
        rain_probability = probabilities[0]

    weather_code = current.get("weather_code")

    info = WeatherInfo(
        temperature_c=current.get("temperature_2m"),
        apparent_temperature_c=current.get("apparent_temperature"),
        precipitation_mm=current.get("precipitation"),
        rain_probability_pct=rain_probability,
        wind_speed_kmh=current.get("wind_speed_10m"),
        condition=_WEATHER_CODE_DESCRIPTIONS.get(
            weather_code,
            "Unknown",
        ),
        source=DataSource.LIVE,
    )

    weather_cache.set(
        cache_key,
        info,
        900,  # 15 minutes
    )

    return info
