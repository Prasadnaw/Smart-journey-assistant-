# JourneyAI India — API Reference

Base URL (dev): `http://localhost:8000`

All responses are JSON. All endpoints are read-only except the journey
search, which is a POST because the request body carries structured
filters.

---

## `GET /health`
Liveness check.
```json
{ "status": "ok" }
```

## `GET /api/status`
Live-checks each provider (not a hardcoded claim) and reports its state.
```json
{
  "geocoding": "OK",
  "routing": "OK",
  "weather": "OK",
  "places": "OK",
  "transit": "Not configured (using public Transitous + estimated fallback)"
}
```

## `GET /api/location-search?q=Marina`
Debounced autocomplete. Returns up to 8 `Location` objects (Open-Meteo
primary, Photon fallback, merged and de-duplicated).

## `GET /api/geocode?lat=13.06&lon=80.25`
Reverse geocode — used by "Use current location". Returns a single
`Location`, or 404 if nothing could be resolved.

## `GET /api/weather?lat=13.06&lon=80.25`
Current conditions from Open-Meteo: temperature, precipitation, wind,
condition text.

## `GET /api/city-places?lat=13.06&lon=80.25&limit=6`
"Explore your destination" cards, sourced from Wikipedia GeoSearch +
PageImages. Each place includes a source URL.

## `GET /api/local-food?lat=13.06&lon=80.25&limit=9`
Real nearby restaurants/cafes/fast-food spots with cuisine tags, sourced
live from OpenStreetMap (Overpass) — genuine POI data, not a curated
"famous dishes" list.

## `GET /api/road-route?from_lat=&from_lon=&to_lat=&to_lon=&mode=taxi`
Road-network distance/time/polyline for one mode (`walk`, `cycle`, `taxi`)
via OSRM, or a labelled straight-line estimate if OSRM has no coverage.

## `GET /api/transit-stops?lat=&lon=&radius_m=800`
Nearby real bus stops / metro / rail stations from OpenStreetMap
(Overpass), or from a local GTFS feed if one is configured.

## `POST /api/journeys/search`
The core multimodal search. Body:
```json
{
  "origin": { "name": "...", "latitude": 0, "longitude": 0 },
  "destination": { "name": "...", "latitude": 0, "longitude": 0 },
  "priority": "fastest",
  "modes": ["train", "metro", "bus", "walk", "taxi"],
  "max_fare_inr": null,
  "max_duration_minutes": null,
  "max_changes": null,
  "max_walking_meters": null
}
```
`priority` is one of `fastest | cheapest | fewest_changes | least_walking | greenest`.

Returns a `JourneySearchResponse` with up to 6 ranked `Journey` objects,
each built from ordered `Segment` legs, transfer/waiting time included in
`total_duration_minutes`, and every fare/time tagged with a `DataSource`
(`official | live | scheduled | estimated | unknown`).

## `GET /api/journeys/{id}`
Fetches a previously-computed journey (used by the trip details page).
Journeys are kept in memory for 1 hour after a search; 404 after that or
if the id is unknown.

---

## Data-source badges
Every fare and every time in the API carries an explicit source:

| Value | Meaning |
|---|---|
| `official` | From an operator's official GTFS/fare data |
| `live` | Real-time data (e.g. live routing) |
| `scheduled` | From a real transit provider's timetable (not live) |
| `estimated` | Computed by JourneyAI from typical speeds/fares — **not official** |
| `unknown` | Source could not be determined |

The frontend renders these as small badges next to every fare/time so
estimates are never presented as official data.
