"""
Geocoding provider.

Primary: Open-Meteo Geocoding API (free, no key, generous for autocomplete).
Fallback: Photon (free, no key, OSM-based, good for POIs/landmarks/streets
that Open-Meteo's admin-area-focused index may miss).

Public Nominatim is intentionally NOT used for autocomplete because of its
usage policy (max 1 req/s, no heavy autocomplete use) -- see README.
"""
from __future__ import annotations

import httpx

from config import settings
from models import Location, LocationType
from providers.cache import geocoding_cache

_FEATURE_TYPE_MAP = {
    "city": LocationType.CITY,
    "town": LocationType.CITY,
    "village": LocationType.LOCALITY,
    "suburb": LocationType.LOCALITY,
    "neighbourhood": LocationType.LOCALITY,
    "state": LocationType.LOCALITY,
    "railway": LocationType.RAILWAY_STATION,
    "station": LocationType.RAILWAY_STATION,
    "subway": LocationType.METRO_STATION,
    "bus_stop": LocationType.BUS_STOP,
    "aerodrome": LocationType.AIRPORT,
    "airport": LocationType.AIRPORT,
    "attraction": LocationType.TOURIST_PLACE,
    "tourism": LocationType.TOURIST_PLACE,
    "house": LocationType.ADDRESS,
    "street": LocationType.ADDRESS,
}


def _guess_feature_type(raw: str | None) -> LocationType:
    if not raw:
        return LocationType.UNKNOWN
    raw_lower = raw.lower()
    for key, val in _FEATURE_TYPE_MAP.items():
        if key in raw_lower:
            return val
    return LocationType.UNKNOWN


class GeocodingProvider:
    """Provider-independent interface. search() and reverse() are the
    contract other code depends on."""

    async def search(self, query: str, limit: int = 8) -> list[Location]:
        raise NotImplementedError

    async def reverse(self, lat: float, lon: float) -> Location | None:
        raise NotImplementedError


class OpenMeteoGeocodingProvider(GeocodingProvider):
    async def search(self, query: str, limit: int = 8) -> list[Location]:
        cache_key = f"om:{query.lower()}:{limit}"
        cached = geocoding_cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "name": query,
            "count": limit,
            "language": "en",
            "format": "json",
        }
        results: list[Location] = []
        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.get(settings.OPEN_METEO_GEOCODING_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return []

        for item in data.get("results", []) or []:
            country = item.get("country") or "India"
            if country != "India":
                # Open-Meteo's geocoder is global; keep the app India-first
                # without hardcoding *which* Indian city is searchable.
                continue
            loc = Location(
                name=item.get("name", query),
                locality=item.get("admin2") or item.get("admin1"),
                state=item.get("admin1"),
                country=country,
                latitude=item["latitude"],
                longitude=item["longitude"],
                feature_type=_guess_feature_type(item.get("feature_code")),
            )
            results.append(loc)

        geocoding_cache.set(cache_key, results, settings.CACHE_TTL_GEOCODING)
        return results

    async def reverse(self, lat: float, lon: float) -> Location | None:
        # Open-Meteo's geocoding API does not support reverse geocoding;
        # this is handled by falling back to Photon (see CompositeGeocoder).
        return None


class PhotonGeocodingProvider(GeocodingProvider):
    async def search(self, query: str, limit: int = 8) -> list[Location]:
        cache_key = f"photon:{query.lower()}:{limit}"
        cached = geocoding_cache.get(cache_key)
        if cached is not None:
            return cached

        params = {
            "q": query,
            "limit": limit,
            "lang": "en",
            # Bias results toward India's bounding box.
            "lat": 22.0,
            "lon": 79.0,
        }
        results: list[Location] = []
        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.get(settings.PHOTON_GEOCODING_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return []

        for feature in data.get("features", []) or []:
            props = feature.get("properties", {})
            country = props.get("country")
            if country and country != "India":
                continue
            coords = feature.get("geometry", {}).get("coordinates")
            if not coords or len(coords) != 2:
                continue
            lon, lat = coords
            name = props.get("name") or query
            locality = props.get("city") or props.get("district") or props.get("locality")
            state = props.get("state")
            osm_value = props.get("osm_value") or props.get("osm_key")
            loc = Location(
                name=name,
                locality=locality,
                state=state,
                country="India",
                latitude=lat,
                longitude=lon,
                feature_type=_guess_feature_type(osm_value),
                raw_label=", ".join(
                    p for p in [name, locality, state] if p and p != name
                ) or None,
            )
            results.append(loc)

        geocoding_cache.set(cache_key, results, settings.CACHE_TTL_GEOCODING)
        return results

    async def reverse(self, lat: float, lon: float) -> Location | None:
        cache_key = f"photon-rev:{lat:.5f}:{lon:.5f}"
        cached = geocoding_cache.get(cache_key)
        if cached is not None:
            return cached

        reverse_url = settings.PHOTON_GEOCODING_URL.rstrip("/") + "/reverse"
        params = {"lat": lat, "lon": lon, "lang": "en"}
        try:
            async with httpx.AsyncClient(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                resp = await client.get(reverse_url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except (httpx.HTTPError, ValueError):
            return None

        features = data.get("features") or []
        if not features:
            return None
        props = features[0].get("properties", {})
        name = props.get("name") or f"{lat:.4f}, {lon:.4f}"
        loc = Location(
            name=name,
            locality=props.get("city") or props.get("district"),
            state=props.get("state"),
            country=props.get("country") or "India",
            latitude=lat,
            longitude=lon,
            feature_type=_guess_feature_type(props.get("osm_value")),
        )
        geocoding_cache.set(cache_key, loc, settings.CACHE_TTL_GEOCODING)
        return loc


class CompositeGeocoder(GeocodingProvider):
    """Tries Open-Meteo first, falls back to Photon. This is what the rest
    of the app should import."""

    def __init__(self) -> None:
        self.primary = OpenMeteoGeocodingProvider()
        self.fallback = PhotonGeocodingProvider()

    async def search(self, query: str, limit: int = 8) -> list[Location]:
        query = query.strip()
        if len(query) < 2:
            return []
        primary_results = await self.primary.search(query, limit)
        if primary_results:
            fallback_results = await self.fallback.search(query, max(2, limit - len(primary_results)))
            merged = primary_results[:]
            seen = {(round(r.latitude, 3), round(r.longitude, 3)) for r in merged}
            for r in fallback_results:
                key = (round(r.latitude, 3), round(r.longitude, 3))
                if key not in seen:
                    merged.append(r)
                    seen.add(key)
            return merged[:limit]
        return await self.fallback.search(query, limit)

    async def reverse(self, lat: float, lon: float) -> Location | None:
        result = await self.primary.reverse(lat, lon)
        if result:
            return result
        return await self.fallback.reverse(lat, lon)


geocoder = CompositeGeocoder()
