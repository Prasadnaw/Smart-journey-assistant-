"""
Road routing provider -- used for:
  * walking legs (first/last mile, transfers)
  * taxi/car legs
  * cycling legs
  * the plain "road distance" shown in Live Context

Uses the public OSRM demo server (router.project-osrm.org), which is free
and requires no API key. It is a shared demo instance with fair-use limits,
so results are cached and requests are kept modest -- see README for how to
point this at a self-hosted OSRM instance instead.
"""
from __future__ import annotations

import httpx

from config import settings
from models import DataSource
from providers.cache import routing_cache

_OSRM_PROFILE = {
    "walk": "foot",
    "cycle": "bike",
    "taxi": "car",
}


class RoutingProvider:
    async def route(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float, mode: str
    ) -> dict | None:
        raise NotImplementedError


class OSRMRoutingProvider(RoutingProvider):
    async def route(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float, mode: str
    ) -> dict | None:
        """Returns {distance_meters, duration_minutes, polyline, source} or None."""
        profile = _OSRM_PROFILE.get(mode, "foot")
        cache_key = f"{profile}:{from_lat:.5f},{from_lon:.5f}:{to_lat:.5f},{to_lon:.5f}"
        cached = routing_cache.get(cache_key)
        if cached is not None:
            return cached

        # NOTE: OSRM demo server only hosts the "car" profile publicly on
        # router.project-osrm.org; foot/bike profiles are not guaranteed to
        # exist there. We still try, and gracefully fall back to a straight
        # line + walking-speed estimate if the profile/route isn't available.
        url = f"{settings.OSRM_BASE_URL}/route/v1/{profile}/{from_lon},{from_lat};{to_lon},{to_lat}"
        params = {"overview": "full", "geometries": "geojson"}
        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        routes = data.get("routes")
        if not routes:
            return None

        route = routes[0]
        coords = route.get("geometry", {}).get("coordinates", [])
        polyline = [[c[1], c[0]] for c in coords]  # -> [lat, lon]

        result = {
            "distance_meters": route.get("distance", 0),
            "duration_minutes": route.get("duration", 0) / 60.0,
            "polyline": polyline,
            "source": DataSource.LIVE,
        }
        routing_cache.set(cache_key, result, 3600)
        return result


import math


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(min(1, math.sqrt(a)))


def straight_line_estimate(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float, mode: str
) -> dict:
    """Fallback when OSRM has no coverage/route: straight-line distance with
    a road-network fudge factor, and typical Indian urban speeds."""
    distance_m = haversine_meters(from_lat, from_lon, to_lat, to_lon) * 1.3
    speeds_kmh = {"walk": 4.5, "cycle": 14.0, "taxi": 22.0}
    speed = speeds_kmh.get(mode, 20.0)
    duration_minutes = (distance_m / 1000.0) / speed * 60.0
    return {
        "distance_meters": distance_m,
        "duration_minutes": duration_minutes,
        "polyline": [[from_lat, from_lon], [to_lat, to_lon]],
        "source": DataSource.ESTIMATED,
    }


router_provider = OSRMRoutingProvider()


async def get_leg(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float, mode: str
) -> dict:
    """Provider-independent entry point: try OSRM, fall back to a labelled
    estimate. Never raises, never crashes the app."""
    result = await router_provider.route(from_lat, from_lon, to_lat, to_lon, mode)
    if result is not None:
        return result
    return straight_line_estimate(from_lat, from_lon, to_lat, to_lon, mode)
