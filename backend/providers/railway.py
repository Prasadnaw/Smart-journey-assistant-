"""
Indian Railways train data provider.

There is no free *official* IRCTC API. This module talks to
indianrailapi.com, a third-party service (not run or endorsed by IRCTC)
that offers a free-tier signup key and returns real train numbers, train
names, station-to-station schedules, and class-wise fares sourced from
Indian Railways timetable data.

Because this is a third-party aggregator rather than an IRCTC-issued feed,
results are tagged DataSource.SCHEDULED, never DataSource.OFFICIAL --
JourneyAI never claims data is more authoritative than it is.

If INDIANRAIL_API_KEY is not set in .env, or a lookup fails or has no
match, every function here returns None and the caller (engine.py) falls
back to its existing typical-schedule estimate. The app never depends on
this provider to function.

NOTE: indianrailapi.com's exact endpoint paths/response shape are a
third-party contract that can change independently of this project. The
functions below follow its commonly documented REST pattern
(apikey/.../From/.../To/...). If your key's plan uses a different path,
check https://indianrailapi.com/api-collection and adjust the URLs below
-- everything is isolated to this one file.
"""
from __future__ import annotations

import httpx

from config import settings
from models import DataSource
from providers.cache import transit_cache


def is_configured() -> bool:
    return bool(settings.INDIANRAIL_API_KEY)


async def _get(path: str) -> dict | None:
    if not is_configured():
        return None
    url = f"{settings.INDIANRAIL_API_URL}/{path}"
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return None
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return None

    if str(data.get("ResponseCode")) not in ("200", "OK") and data.get("Status") != "SUCCESS":
        return None
    return data


async def find_station_code(place_name: str) -> str | None:
    """Best-effort station-code lookup by free-text name (city or station
    name), e.g. 'Chennai' -> 'MAS'. Returns None if unresolved."""
    cache_key = f"station:{place_name.lower()}"
    cached = transit_cache.get(cache_key)
    if cached is not None:
        return cached or None

    data = await _get(f"apikey/{settings.INDIANRAIL_API_KEY}/StationCode/{place_name}/")
    code = None
    if data:
        stations = data.get("Stations") or []
        if stations:
            code = stations[0].get("StationCode")

    transit_cache.set(cache_key, code or "", settings.CACHE_TTL_TRANSIT)
    return code


async def trains_between_stations(from_code: str, to_code: str) -> list[dict] | None:
    """Real trains running between two station codes: number, name,
    departure/arrival, duration, distance. Returns None if unavailable."""
    cache_key = f"tbs:{from_code}:{to_code}"
    cached = transit_cache.get(cache_key)
    if cached is not None:
        return cached or None

    data = await _get(
        f"TrainBetweenStation/apikey/{settings.INDIANRAIL_API_KEY}/From/{from_code}/To/{to_code}/"
    )
    trains = None
    if data:
        raw = data.get("Trains") or []
        trains = [
            {
                "train_number": t.get("TrainNo"),
                "train_name": t.get("TrainName"),
                "departure_time": t.get("StartTime") or t.get("Departure"),
                "arrival_time": t.get("EndTime") or t.get("Arrival"),
                "duration": t.get("TravelTime") or t.get("Duration"),
                "distance_km": t.get("Distance"),
            }
            for t in raw
        ]

    transit_cache.set(cache_key, trains or [], settings.CACHE_TTL_TRANSIT)
    return trains or None


async def train_fare(train_number: str, from_code: str, to_code: str) -> list[dict] | None:
    """Class-wise fares (1A/2A/3A/SL/CC/GN/...) for a specific train."""
    cache_key = f"fare:{train_number}:{from_code}:{to_code}"
    cached = transit_cache.get(cache_key)
    if cached is not None:
        return cached or None

    data = await _get(
        f"TrainFare/apikey/{settings.INDIANRAIL_API_KEY}/TrainNumber/{train_number}"
        f"/Da/{from_code}/Ja/{to_code}/"
    )
    fares = None
    if data:
        raw = data.get("Fares") or []
        fares = [
            {"class_name": f.get("Name"), "class_code": f.get("Code"), "fare_inr": f.get("Fare")}
            for f in raw
        ]

    transit_cache.set(cache_key, fares or [], settings.CACHE_TTL_TRANSIT)
    return fares or None


async def get_real_train_leg(from_name: str, to_name: str) -> dict | None:
    """High-level convenience used by engine.py: resolve station codes,
    find a real train, attach fares. Returns a single best-match dict or
    None if any step fails -- always safe to call speculatively."""
    if not is_configured():
        return None

    from_code = await find_station_code(from_name)
    to_code = await find_station_code(to_name)
    if not from_code or not to_code:
        return None

    trains = await trains_between_stations(from_code, to_code)
    if not trains:
        return None

    best = trains[0]
    fares = await train_fare(best["train_number"], from_code, to_code) if best.get("train_number") else None
    sleeper_fare = None
    if fares:
        for f in fares:
            if f.get("class_code") == "SL":
                sleeper_fare = f.get("fare_inr")
                break
        if sleeper_fare is None and fares:
            sleeper_fare = fares[0].get("fare_inr")

    return {
        "train_number": best.get("train_number"),
        "train_name": best.get("train_name"),
        "from_code": from_code,
        "to_code": to_code,
        "departure_time": best.get("departure_time"),
        "arrival_time": best.get("arrival_time"),
        "fare_inr": float(sleeper_fare) if sleeper_fare not in (None, "") else None,
        "fares_by_class": fares,
        "source": DataSource.SCHEDULED,
    }
