"""
Places provider -- Explore your destination.

Uses Wikimedia's public MediaWiki API for nearby landmarks and
OpenStreetMap/Overpass for nearby food.

No API key required.
"""

from __future__ import annotations

import httpx

from config import settings
from models import Place
from providers.cache import places_cache


WIKIMEDIA_HEADERS = {
    "User-Agent": (
        "JourneyAI-India/1.0 "
        "(hackathon project; contact: dev@example.com)"
    )
}


# ============================================================
# PLACE SCORING
# ============================================================

POSITIVE_TERMS = (
    "beach",
    "fort",
    "palace",
    "temple",
    "museum",
    "park",
    "garden",
    "church",
    "mosque",
    "cathedral",
    "monument",
    "gateway",
    "market",
    "lake",
    "waterfall",
    "island",
    "hill",
    "viewpoint",
    "zoo",
    "aquarium",
    "gallery",
    "heritage",
    "landmark",
    "shrine",
    "cave",
    "theatre",
    "theater",
    "bridge",
    "maidan",
    "promenade",
    "memorial",
    "observatory",
    "palace",
    "museum",
    "tower",
    "stadium",
)


NEGATIVE_TERMS = (
    "assembly constituency",
    "constituency",
    "directorate",
    "election",
    "political",
    "district",
    "village",
    "municipal corporation",
    "legislative",
    "ward",
    "government office",
    "riots",
    "census",
    "politician",
    "political party",
)


def _score_place(
    title: str,
    description: str | None,
    distance_km: float | None = None,
) -> float:

    text = f"{title} {description or ''}".lower()

    score = 0.0

    for term in POSITIVE_TERMS:
        if term in text:
            score += 3

    for term in NEGATIVE_TERMS:
        if term in text:
            score -= 8

    # Prefer nearby places.
    if distance_km is not None:

        if distance_km <= 2:
            score += 4

        elif distance_km <= 5:
            score += 2

        elif distance_km <= 10:
            score += 1

        elif distance_km > 15:
            score -= 2

    return score


# ============================================================
# FAMOUS PLACES
# ============================================================

async def get_famous_places(
    lat: float,
    lon: float,
    limit: int = 8,
) -> list[Place]:

    cache_key = f"{lat:.3f},{lon:.3f}:{limit}"

    cached = places_cache.get(cache_key)

    if cached is not None:
        return cached

    # Ask for more results than we need because we filter them.
    search_limit = min(
        max(limit * 5, 25),
        50,
    )

    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",

        # Wikimedia-supported nearby-page generator.
        "generator": "geosearch",

        "ggscoord": f"{lat}|{lon}",

        # 20 km gives better city coverage.
        "ggsradius": 10000,

        "ggslimit": min(search_limit,50),

        # Get everything needed in one request.
        "prop": "coordinates|pageimages|extracts|info",

        "piprop": "thumbnail|original",

        "pithumbsize": 700,

        "pilimit": search_limit,

        "exintro": "1",

        "explaintext": "1",

        "exsentences": 2,

        "inprop": "url",
    }

    try:

        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers=WIKIMEDIA_HEADERS,
            follow_redirects=True,
        ) as client:

            response = await client.get(
                settings.WIKIPEDIA_API_URL,
                params=params,
            )

            response.raise_for_status()

            data = response.json()

    except (
        httpx.HTTPError,
        ValueError,
        KeyError,
        TypeError,
    ):

        return []

    pages = (
        data
        .get("query", {})
        .get("pages", [])
    )

    # formatversion=2 normally gives a list.
    # Keep support for the old dictionary format too.
    if isinstance(pages, dict):
        pages = list(pages.values())

    candidates = []

    for index, page in enumerate(pages):

        if not isinstance(page, dict):
            continue

        title = (
            page.get("title")
            or "Unknown place"
        )

        # Ignore pages that aren't actual articles.
        if page.get("missing"):
            continue

        description = (
            page.get("extract")
            or ""
        ).strip()

        # ----------------------------------------------------
        # IMAGE
        # ----------------------------------------------------

        thumbnail = (
            page
            .get("thumbnail", {})
            .get("source")
        )

        original_image = (
            page
            .get("original", {})
            .get("source")
        )

        image_url = (
            thumbnail
            or original_image
        )

        # ----------------------------------------------------
        # COORDINATES / DISTANCE
        # ----------------------------------------------------

        coordinates = page.get("coordinates") or []

        distance_km = None

        if coordinates:

            distance_m = coordinates[0].get("dist")

            if distance_m is not None:

                try:
                    distance_km = float(distance_m) / 1000
                except (TypeError, ValueError):
                    distance_km = None

        # ----------------------------------------------------
        # SCORE
        # ----------------------------------------------------

        score = _score_place(
            title,
            description,
            distance_km,
        )

        # Results without an image are allowed into the
        # candidate list, but are ranked lower.
        if not image_url:
            score -= 6

        # Wikipedia's generator ordering is already useful.
        score -= index * 0.03

        candidates.append(
            {
                "score": score,
                "title": title,
                "description": description or None,
                "image_url": image_url,
                "source_url": page.get("fullurl"),
                "distance_km": distance_km,
            }
        )

    # Best attractions first.
    candidates.sort(
        key=lambda x: x["score"],
        reverse=True,
    )

    places: list[Place] = []

    for candidate in candidates:

        # Prefer image-backed cards.
        if not candidate["image_url"]:
            continue

        try:

            places.append(
                Place(
                    name=candidate["title"],

                    description=candidate["description"],

                    image_url=candidate["image_url"],

                    source_url=candidate["source_url"],
                )
            )

        except (TypeError, ValueError):

            continue

        if len(places) >= limit:
            break

    # --------------------------------------------------------
    # SECOND PASS
    #
    # If we couldn't get enough image-backed places, return
    # additional valid Wikipedia places instead of returning
    # an almost-empty Explore section.
    # --------------------------------------------------------

    if len(places) < limit:

        used_names = {
            p.name
            for p in places
        }

        for candidate in candidates:

            if candidate["title"] in used_names:
                continue

            try:

                places.append(
                    Place(
                        name=candidate["title"],

                        description=candidate["description"],

                        image_url=candidate["image_url"],

                        source_url=candidate["source_url"],
                    )
                )

                used_names.add(
                    candidate["title"]
                )

            except (TypeError, ValueError):

                continue

            if len(places) >= limit:
                break

    places_cache.set(
        cache_key,
        places,
        settings.CACHE_TTL_PLACES,
    )

    return places


# ============================================================
# LOCAL FOOD
# ============================================================

async def get_local_food(
    lat: float,
    lon: float,
    limit: int = 9,
) -> list["FoodSpot"]:

    """
    Real nearby restaurants, cafes and fast-food locations
    using OpenStreetMap Overpass.

    No API key required.
    """

    from models import (
        DataSource,
        FoodSpot,
    )

    cache_key = (
        f"food:{lat:.3f},{lon:.3f}:{limit}"
    )

    cached = places_cache.get(cache_key)

    if cached is not None:
        return cached

    query = f"""
    [out:json][timeout:15];

    (
      node["amenity"="restaurant"]
        (around:3000,{lat},{lon});

      way["amenity"="restaurant"]
        (around:3000,{lat},{lon});

      node["amenity"="cafe"]
        (around:2500,{lat},{lon});

      way["amenity"="cafe"]
        (around:2500,{lat},{lon});

      node["amenity"="fast_food"]
        (around:2500,{lat},{lon});

      way["amenity"="fast_food"]
        (around:2500,{lat},{lon});
    );

    out center {max(limit * 3, 30)};
    """

    try:

        async with httpx.AsyncClient(
            timeout=settings.HTTP_TIMEOUT_SECONDS,
            headers=WIKIMEDIA_HEADERS,
            follow_redirects=True,
        ) as client:

            response = await client.post(
                "https://overpass-api.de/api/interpreter",
                data={
                    "data": query,
                },
            )

            response.raise_for_status()

            data = response.json()

    except (
        httpx.HTTPError,
        ValueError,
    ):

        return []

    spots: list[FoodSpot] = []

    seen_names: set[str] = set()

    for element in data.get("elements", []):

        tags = element.get("tags", {})

        name = (
            tags.get("name")
            or tags.get("brand")
        )

        if not name:
            continue

        name_key = name.strip().lower()

        if name_key in seen_names:
            continue

        seen_names.add(name_key)

        # Nodes have lat/lon directly.
        latitude = element.get("lat")
        longitude = element.get("lon")

        # Ways normally use a center.
        center = element.get("center") or {}

        if latitude is None:
            latitude = center.get("lat")

        if longitude is None:
            longitude = center.get("lon")

        cuisine = (
            tags.get("cuisine")
            or ""
        ).replace("_", " ")

        try:

            spots.append(
                FoodSpot(
                    name=name,

                    cuisine=cuisine or None,

                    kind=tags.get("amenity"),

                    latitude=latitude,

                    longitude=longitude,

                    source=DataSource.LIVE,
                )
            )

        except (TypeError, ValueError):

            continue

        if len(spots) >= limit:
            break

    places_cache.set(
        cache_key,
        spots,
        settings.CACHE_TTL_PLACES,
    )

    return spots