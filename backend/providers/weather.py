"""
Weather provider -- Open-Meteo.
No API key required.
"""

from __future__ import annotations

import httpx

from models import DataSource, WeatherInfo
from providers.cache import weather_cache


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


_WEATHER_CODES = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Rime fog",
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
    82: "Heavy rain showers",
    85: "Snow showers",
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
            timeout=20.0,
            follow_redirects=True,
            headers={
                "User-Agent": "JourneyAI-India/1.0"
            },
        ) as client:

            response = await client.get(
                OPEN_METEO_URL,
                params=params,
            )

            print(
                "OPEN-METEO STATUS:",
                response.status_code,
            )

            print(
                "OPEN-METEO URL:",
                response.url,
            )

            print(
                "OPEN-METEO RESPONSE:",
                response.text[:2000],
            )

            response.raise_for_status()

            data = response.json()

    except httpx.HTTPStatusError as exc:

        print(
            "OPEN-METEO HTTP ERROR:",
            exc.response.status_code,
            exc.response.text[:2000],
        )

        return None

    except httpx.RequestError as exc:

        print(
            "OPEN-METEO REQUEST ERROR:",
            repr(exc),
        )

        return None

    except ValueError as exc:

        print(
            "OPEN-METEO JSON ERROR:",
            repr(exc),
        )

        return None

    except Exception as exc:

        print(
            "OPEN-METEO UNEXPECTED ERROR:",
            repr(exc),
        )

        return None

    current = data.get("current")

    if not current:

        print(
            "OPEN-METEO MISSING CURRENT DATA:",
            data,
        )

        return None

    hourly = data.get("hourly") or {}

    probabilities = hourly.get(
        "precipitation_probability"
    ) or []

    rain_probability = (
        probabilities[0]
        if probabilities
        else None
    )

    weather_code = current.get(
        "weather_code"
    )

    info = WeatherInfo(

        temperature_c=current.get(
            "temperature_2m"
        ),

        apparent_temperature_c=current.get(
            "apparent_temperature"
        ),

        precipitation_mm=current.get(
            "precipitation"
        ),

        rain_probability_pct=rain_probability,

        wind_speed_kmh=current.get(
            "wind_speed_10m"
        ),

        condition=_WEATHER_CODES.get(
            weather_code,
            "Unknown",
        ),

        source=DataSource.LIVE,
    )

    weather_cache.set(
        cache_key,
        info,
        900,
    )

    return info
