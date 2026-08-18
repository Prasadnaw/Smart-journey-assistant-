"""
Service layer -- glues providers + engine together for main.py's endpoints,
and holds a small in-memory store so GET /api/journeys/{id} can return a
previously-computed journey (e.g. after the user clicks a result card).
"""
from __future__ import annotations

import time

from models import Journey, JourneySearchRequest, JourneySearchResponse
from providers.routing import get_leg
from engine import apply_filters, generate_candidate_journeys, rank_journeys

_JOURNEY_STORE: dict[str, tuple[float, Journey]] = {}
_JOURNEY_TTL_SECONDS = 3600


def _remember(journey: Journey) -> None:
    _JOURNEY_STORE[journey.id] = (time.time() + _JOURNEY_TTL_SECONDS, journey)


def get_stored_journey(journey_id: str) -> Journey | None:
    entry = _JOURNEY_STORE.get(journey_id)
    if not entry:
        return None
    expires_at, journey = entry
    if time.time() > expires_at:
        _JOURNEY_STORE.pop(journey_id, None)
        return None
    return journey


async def search_journeys(request: JourneySearchRequest) -> JourneySearchResponse:
    journeys, transit_available, notes = await generate_candidate_journeys(request)

    journeys = apply_filters(
        journeys,
        request
    )

    journeys = rank_journeys(
        journeys,
        request.priority
    )

    # General / All options intentionally exposes more alternatives.
    # The other modes stay compact and focused.
    result_limit = (
        12
        if request.priority == "general"
        else 6
    )

    journeys = journeys[:result_limit]

    for j in journeys:
        _remember(j)

    road_leg = await get_leg(
        request.origin.latitude,
        request.origin.longitude,
        request.destination.latitude,
        request.destination.longitude,
        "taxi",
    )

    road_distance_km = round(
        road_leg["distance_meters"] / 1000.0,
        1
    )

    if not journeys:
        notes.append(
            "No journeys matched your filters — try relaxing the fare, "
            "time, change, or walking limits."
        )

    return JourneySearchResponse(
        origin=request.origin,
        destination=request.destination,
        journeys=journeys,
        road_distance_km=road_distance_km,
        transit_available=transit_available,
        notes=notes,
    )