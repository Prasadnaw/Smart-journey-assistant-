"""
Transit provider.

Primary: Transitous / MOTIS public multimodal routing API
         (https://transitous.org) -- an open, community-run multimodal
         router built on public GTFS feeds. Coverage in India is still
         growing, so this call is always wrapped and allowed to fail
         gracefully.

Secondary: a local GTFS feed adapter (GTFSFeedAdapter) -- a stub that shows
         exactly where to plug in an Indian city's GTFS static feed
         (routes.txt / trips.txt / stop_times.txt / stops.txt / calendar.txt
         / calendar_dates.txt / fare_attributes.txt / fare_rules.txt) and,
         later, GTFS-Realtime (vehicle positions / trip updates / service
         alerts) once a feed is dropped into GTFS_FEED_DIR.

Nearby stops: uses the public Overpass API (OpenStreetMap) to find real
         bus/metro/rail stops/stations near a point -- free, no key.

If neither Transitous nor a local GTFS feed has coverage for a given
origin/destination pair, transit.py returns None and the journey engine
(engine.py) builds a clearly-labelled ESTIMATED multimodal itinerary
instead. JourneyAI never invents "official" transit data.
"""
from __future__ import annotations

import os
from pathlib import Path

import httpx

from config import settings
from models import DataSource
from providers.cache import transit_cache


class TransitProvider:
    async def plan_journey(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> list[dict] | None:
        """Returns a list of raw leg dicts (mode, from, to, times, fare) if
        real transit coverage exists for this OD pair, else None."""
        raise NotImplementedError

    async def nearby_stops(self, lat: float, lon: float, radius_m: int = 800) -> list[dict]:
        raise NotImplementedError


class TransitousProvider(TransitProvider):
    async def plan_journey(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> list[dict] | None:
        cache_key = f"tt:{from_lat:.4f},{from_lon:.4f}:{to_lat:.4f},{to_lon:.4f}"
        cached = transit_cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "fromPlace": f"{from_lat},{from_lon}",
            "toPlace": f"{to_lat},{to_lon}",
            "numItineraries": 3,
        }
        headers = {}
        if settings.TRANSITOUS_API_KEY:
            headers["Authorization"] = f"Bearer {settings.TRANSITOUS_API_KEY}"

        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.get(
                    f"{settings.TRANSITOUS_API_URL}/plan", params=params, headers=headers
                )
                if resp.status_code != 200:
                    return None
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        itineraries = (data.get("plan") or {}).get("itineraries") or []
        if not itineraries:
            return None

        # Normalise the first itinerary into our internal leg format.
        legs = []
        for leg in itineraries[0].get("legs", []):
            mode = (leg.get("mode") or "").lower()
            legs.append(
                {
                    "mode": mode,
                    "from": leg.get("from", {}).get("name", "Stop"),
                    "to": leg.get("to", {}).get("name", "Stop"),
                    "start_time": leg.get("startTime"),
                    "end_time": leg.get("endTime"),
                    "duration_minutes": (leg.get("duration") or 0) / 60.0,
                    "distance_meters": leg.get("distance"),
                    "line_name": (leg.get("route") or {}).get("shortName"),
                    "operator": (leg.get("agency") or {}).get("name"),
                    "fare_inr": None,  # Transitous rarely exposes fares for India
                    "fare_source": DataSource.UNKNOWN,
                    "time_source": DataSource.SCHEDULED,
                }
            )

        if legs:
            transit_cache.set(cache_key, legs, settings.CACHE_TTL_TRANSIT)
        return legs or None

    async def nearby_stops(self, lat: float, lon: float, radius_m: int = 800) -> list[dict]:
        # Transitous does not currently expose a simple "nearby stops"
        # REST endpoint publicly, so this falls through to Overpass.
        return []


class GTFSFeedAdapter(TransitProvider):
    """
    Adapter for a locally-loaded static GTFS feed for one Indian transit
    agency (e.g. a city metro or state bus corporation).

    This is intentionally a stub: dropping GTFS text files into
    GTFS_FEED_DIR (see config.py) and implementing the TODOs below is how
    you add real official schedules/fares for a specific operator without
    touching the rest of the app. Until a feed is present, plan_journey()
    simply returns None so the engine falls back to an estimated route.
    """

    def __init__(self, feed_dir: str | None = None) -> None:
        self.feed_dir = Path(feed_dir or settings.GTFS_FEED_DIR)

    def _has_feed(self) -> bool:
        required = ["stops.txt", "routes.txt", "trips.txt", "stop_times.txt"]
        return self.feed_dir.exists() and all(
            (self.feed_dir / f).exists() for f in required
        )

    async def plan_journey(
        self, from_lat: float, from_lon: float, to_lat: float, to_lon: float
    ) -> list[dict] | None:
        if not self._has_feed():
            return None
        # TODO: load stops.txt / stop_times.txt / trips.txt / routes.txt /
        # calendar.txt / calendar_dates.txt with a library such as
        # `gtfs-kit` or `partridge`, build a lightweight RAPTOR/CSA journey
        # planner, and (optionally) enrich with GTFS-Realtime
        # TripUpdate/VehiclePosition/ServiceAlert feeds for live delays.
        return None

    async def nearby_stops(self, lat: float, lon: float, radius_m: int = 800) -> list[dict]:
        if not self._has_feed():
            return []
        # TODO: spatial lookup against stops.txt (lat/lon + stop_name).
        return []


async def overpass_nearby_stops(lat: float, lon: float, radius_m: int = 800) -> list[dict]:
    """Free OSM Overpass lookup for real bus/metro/rail stops near a point."""
    cache_key = f"overpass:{lat:.4f},{lon:.4f}:{radius_m}"
    cached = transit_cache.get(cache_key)
    if cached is not None:
        return cached

    query = f"""
    [out:json][timeout:10];
    (
      node["highway"="bus_stop"](around:{radius_m},{lat},{lon});
      node["railway"="station"](around:{radius_m},{lat},{lon});
      node["railway"="halt"](around:{radius_m},{lat},{lon});
      node["station"="subway"](around:{radius_m},{lat},{lon});
      node["public_transport"="station"](around:{radius_m},{lat},{lon});
    );
    out center 20;
    """
    try:
        async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
            resp = await client.post(
                "https://overpass-api.de/api/interpreter", data={"data": query}
            )
            if resp.status_code != 200:
                return []
            data = resp.json()
    except (httpx.HTTPError, ValueError):
        return []

    stops = []
    for el in data.get("elements", [])[:20]:
        tags = el.get("tags", {})
        kind = "metro" if tags.get("station") == "subway" else (
            "rail" if tags.get("railway") in ("station", "halt") else "bus"
        )
        stops.append(
            {
                "name": tags.get("name", "Unnamed stop"),
                "kind": kind,
                "latitude": el.get("lat"),
                "longitude": el.get("lon"),
            }
        )
    transit_cache.set(cache_key, stops, settings.CACHE_TTL_TRANSIT)
    return stops


transitous = TransitousProvider()
gtfs_adapter = GTFSFeedAdapter()


async def plan_real_transit_journey(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float
) -> list[dict] | None:
    """Tries all configured real-data transit providers in order. Returns
    None if none of them have coverage -- the engine then builds a clearly
    labelled estimated itinerary."""
    legs = await gtfs_adapter.plan_journey(from_lat, from_lon, to_lat, to_lon)
    if legs:
        return legs
    legs = await transitous.plan_journey(from_lat, from_lon, to_lat, to_lon)
    if legs:
        return legs
    return None


async def get_nearby_stops(lat: float, lon: float, radius_m: int = 800) -> list[dict]:
    stops = await gtfs_adapter.nearby_stops(lat, lon, radius_m)
    if stops:
        return stops
    return await overpass_nearby_stops(lat, lon, radius_m)
