"""
JourneyAI India -- FastAPI backend entrypoint.

Run with:
    python -m uvicorn main:app --reload
"""
from __future__ import annotations

import httpx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from models import (
    ApiStatus,
    Journey,
    JourneySearchRequest,
    JourneySearchResponse,
    Location,
    WeatherInfo,
)
from providers.geocoding import geocoder
from providers.places import get_famous_places, get_local_food
from providers.routing import get_leg
from providers.transit import get_nearby_stops
from providers.weather import get_weather
import services

app = FastAPI(
    title="JourneyAI India API",
    description="One search. Every practical way there.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/status", response_model=ApiStatus)
async def api_status():
    """Lightweight live check of each provider so the frontend can show a
    real 'Geocoding: OK / Transit: Not configured' panel instead of a
    hardcoded claim."""
    geocoding_status = "OK"
    try:
        results = await geocoder.search("Chennai", limit=1)
        geocoding_status = "OK" if results else "Degraded"
    except Exception:
        geocoding_status = "Unavailable"

    routing_status = "OK"
    try:
        leg = await get_leg(13.0827, 80.2707, 13.0604, 80.2496, "walk")
        routing_status = "OK" if leg else "Degraded"
    except Exception:
        routing_status = "Unavailable"

    weather_status = "OK"
    try:
        w = await get_weather(13.0827, 80.2707)
        weather_status = "OK" if w else "Unavailable"
    except Exception:
        weather_status = "Unavailable"

    places_status = "OK"
    try:
        places = await get_famous_places(13.0827, 80.2707, limit=1)
        places_status = "OK" if places else "Degraded"
    except Exception:
        places_status = "Unavailable"

    if settings.TRANSITOUS_API_KEY or settings.TRANSITLAND_API_KEY:
        transit_status = "Connected"
    else:
        transit_status = "Not configured (using public Transitous + estimated fallback)"

    railway_status = (
        "Connected (indianrailapi.com)" if settings.INDIANRAIL_API_KEY else "Not configured (train legs estimated)"
    )

    return ApiStatus(
        geocoding=geocoding_status,
        routing=routing_status,
        weather=weather_status,
        places=places_status,
        transit=transit_status,
        railway=railway_status,
    )


@app.get("/api/location-search", response_model=list[Location])
async def location_search(q: str = Query(..., min_length=1)):
    return await geocoder.search(q, limit=8)


@app.get("/api/geocode", response_model=Location | None)
async def reverse_geocode(lat: float, lon: float):
    result = await geocoder.reverse(lat, lon)
    if result is None:
        raise HTTPException(
            status_code=404, detail="Could not determine a location for these coordinates."
        )
    return result


@app.get("/api/weather", response_model=WeatherInfo)
async def weather(lat: float, lon: float):
    result = await get_weather(lat, lon)
    if result is None:
        raise HTTPException(status_code=503, detail="Weather data temporarily unavailable.")
    return result


@app.get("/api/city-places")
async def city_places(lat: float, lon: float, limit: int = 8):
    places = await get_famous_places(lat, lon, limit)
    return {"places": places}


@app.get("/api/local-food")
async def local_food(lat: float, lon: float, limit: int = 9):
    spots = await get_local_food(lat, lon, limit)
    return {"food": spots}


@app.get("/api/road-route")
async def road_route(
    from_lat: float, from_lon: float, to_lat: float, to_lon: float, mode: str = "taxi"
):
    leg = await get_leg(from_lat, from_lon, to_lat, to_lon, mode)
    return leg


@app.get("/api/transit-stops")
async def transit_stops(lat: float, lon: float, radius_m: int = 800):
    stops = await get_nearby_stops(lat, lon, radius_m)
    return {"stops": stops}


@app.post("/api/journeys/search", response_model=JourneySearchResponse)
async def journeys_search(request: JourneySearchRequest):
    try:
        return await services.search_journeys(request)
    except httpx.HTTPError:
        raise HTTPException(
            status_code=503,
            detail="Live transit data temporarily unavailable. Showing what we could compute.",
        )


@app.get("/api/journeys/{journey_id}", response_model=Journey)
async def get_journey(journey_id: str):
    journey = services.get_stored_journey(journey_id)
    if journey is None:
        raise HTTPException(
            status_code=404,
            detail="Journey not found or expired — please search again.",
        )
    return journey
