# JourneyAI India

**One search. Every practical way there.**

An intelligent multimodal journey planner for India that compares *every*
practical way to get from A to B — fastest, cheapest, fewest changes,
least walking, or greenest — across walking, cycling, bus, metro, train
and taxi, using real free public APIs wherever possible and clearly
labelling anything estimated.

This is a real, runnable full-stack app (FastAPI + React), not a static
demo. See `SETUP.md` for exact commands.

---

## Features

- **Universal location search** — any Indian city, locality, street,
  address, station, airport, landmark, or tourist place, via debounced
  autocomplete. No hardcoded city list.
- **Current location** — browser geolocation → reverse geocoding, with
  friendly handling of denied/unavailable/timeout cases.
- **Real multimodal routing** — tries Transitous/MOTIS (open multimodal
  transit routing) and an optional local GTFS feed first; falls back to a
  clearly-labelled *estimated* multi-leg itinerary when there's no
  transit coverage for an area, rather than inventing "official" data.
- **Transfer-time-aware totals** — a journey's total time is
  `sum(leg durations) + sum(transfer/waiting time)`, never just the sum of
  vehicle durations.
- **Five ranking modes** — fastest, cheapest, fewest changes, least
  walking, greenest (CO₂), each explicitly labelled when the underlying
  data is estimated.
- **Filters** — max fare, max time, max transfers, max walking distance,
  and per-mode checkboxes (train/metro/bus/walk/taxi) that actually
  constrain the backend search.
- **Interactive map** — Leaflet + OpenStreetMap, origin/destination
  markers, route polylines per leg, nearby transit stops.
- **Live context** — road distance, destination weather, transit
  availability for the searched pair.
- **Real train data (optional)** — with a free `INDIANRAIL_API_KEY`
  (indianrailapi.com, third-party, not IRCTC), long-distance train legs
  show the real train number, train name, and class-wise fares instead of
  a generic estimate. Without a key, this degrades gracefully to the
  typical-schedule estimate, same as everything else.
- **Food & drink near your destination** — real nearby restaurants/cafes
  with cuisine tags, sourced live from OpenStreetMap (Overpass), shown
  alongside the Wikipedia landmark cards.
- **Explore your destination** — Wikipedia-sourced place cards with
  images, descriptions, and source links.
- **Trip details page** — full step-by-step breakdown: every leg's mode,
  operator, from/to, duration, fare, and an explicit data-source badge
  (Official / Live / Scheduled / Estimated / Unknown).
- **Graceful degradation everywhere** — a failed or missing API never
  crashes the app; it degrades to an estimate with a visible note instead.

---

## Architecture

```
journeyai-india/
  backend/                  FastAPI app
    main.py                 API endpoints
    engine.py                Multimodal journey assembly + ranking
    services.py               Orchestration + in-memory journey store
    models.py                 Pydantic schemas
    config.py                 Env-driven settings
    providers/                 One module per external data source
      geocoding.py              Open-Meteo (primary) + Photon (fallback)
      routing.py                 OSRM (walk/cycle/taxi legs) + straight-line fallback
      transit.py                  Transitous/MOTIS + GTFS feed adapter (stub) + Overpass
      weather.py                   Open-Meteo forecast
      places.py                     Wikipedia GeoSearch + PageImages
    tests/                      pytest — transfer-time math, ranking
  frontend/                 React + Vite + Leaflet
    src/components/           Header, LocationSearch, CurrentLocationButton,
                                TransportFilters, FilterPanel, JourneyCard,
                                JourneyLeg, JourneyMap, LiveContext,
                                FamousPlaces, TripDetails, ApiStatus
    src/pages/                 SearchPage, TripDetailsPage
```

The **provider abstraction** (`backend/providers/`) means every external
data source is swappable: add a new geocoder, a new transit feed, or a
different weather API without touching `engine.py` or `main.py`. GTFS
support (routes/trips/stop_times/stops/calendar/fares, plus GTFS-Realtime)
has a working adapter stub at `providers/transit.py::GTFSFeedAdapter` —
drop feed files into `backend/gtfs_feeds/` and implement the two TODOs to
plug in a real Indian transit agency's official schedule.

## API providers

| Purpose | Provider | Key required? |
|---|---|---|
| Geocoding / autocomplete | Open-Meteo Geocoding API | No |
| Geocoding fallback + reverse geocoding | Photon (Komoot) | No |
| Walking/cycling/taxi routing | OSRM public demo server | No |
| Multimodal transit routing | Transitous / MOTIS | No (optional key for higher limits) |
| Nearby transit stops | OpenStreetMap Overpass API | No |
| Weather | Open-Meteo Forecast API | No |
| Destination places/images | Wikipedia (MediaWiki Action API) | No |
| Nearby food & drink | OpenStreetMap Overpass API | No |
| Real train name/number/schedule/fare | indianrailapi.com (third-party, unofficial) | Yes — free tier, optional |
| Map tiles | OpenStreetMap | No |

Public Nominatim is deliberately **not** used for autocomplete, per its
usage policy (max ~1 req/s, not meant for live-typing search).

## Real train data (optional)

Long-distance train legs (>250 km) try a real Indian Railways lookup
before falling back to an estimate:

1. `backend/providers/railway.py` resolves your origin/destination names
   to station codes, finds real trains between them, and pulls
   class-wise fares — via **indianrailapi.com**, a free-tier third-party
   service (not IRCTC-issued, hence tagged `scheduled` not `official`).
2. Sign up at https://indianrailapi.com, put the key in
   `backend/.env` as `INDIANRAIL_API_KEY=...`, restart the backend.
3. Without a key, this section of the itinerary uses the same
   typical-schedule estimate as before — nothing breaks.

## Installation

See **`SETUP.md`** for exact Windows PowerShell commands. Short version:

```powershell
# Backend
cd backend; python -m venv venv; .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m uvicorn main:app --reload

# Frontend (separate terminal)
cd frontend; npm install; npm run dev
```

Then open http://localhost:5173.

## Environment variables

All in `backend/.env` (copy from `backend/.env.example`). The app runs
with **zero keys filled in** — every default provider above is free and
keyless. Optional keys (`TRANSITLAND_API_KEY`, `TRANSITOUS_API_KEY`,
`INDIANRAIL_API_KEY`) unlock higher-limit/official transit data and real
train info where available; `GTFS_FEED_DIR` lets you point at a local
GTFS feed for one Indian operator.

## How fallback routing works

1. The engine first asks Transitous/MOTIS (and a local GTFS feed, if
   configured) for a real multimodal itinerary between the two points.
2. If that returns real legs, they're used, tagged `scheduled`/`live`.
3. If no provider has coverage, the engine builds one clearly-labelled
   **estimated** multi-leg itinerary using OSRM-routed walking legs plus
   typical Indian urban-transport speeds/fares for the remaining legs
   (metro/bus/train), and a note is shown: *"Transit data unavailable for
   this area — estimated route shown."*
4. A direct taxi option (OSRM-routed, estimated fare) is always offered
   as a comparison point when the taxi mode is enabled.
5. In both cases, transfer/waiting time between legs is added explicitly
   as its own segment and counted in the total — see
   `backend/engine.py::_finalise_journey` and
   `backend/tests/test_engine.py` for the worked example from the spec
   (18:00→18:20 bus, 18:30→19:00 train, 19:10→19:25 metro = **85
   minutes**, not 65).

## Data-source limitations

- Fares/times without a matched GTFS feed or a Transitous itinerary are
  **estimates** based on typical Indian urban-transport speeds and fare
  formulas — always badged "Estimated", never presented as official.
- The public OSRM demo server and Overpass API are shared, rate-limited
  instances suitable for a hackathon demo, not production traffic at
  scale — see comments in `providers/routing.py` and `providers/transit.py`
  for how to point at self-hosted instances.
- Transitous/MOTIS transit coverage in India is still growing; many
  routes will use the estimated fallback today. This is intentional and
  clearly surfaced rather than hidden.

## Attribution

- Map tiles & road/transit-stop data: © OpenStreetMap contributors
- Place cards: Wikipedia (CC BY-SA / linked per-article licensing)
- Weather & geocoding: Open-Meteo
- Multimodal routing: Transitous / MOTIS

## Troubleshooting

| Symptom | Fix |
|---|---|
| `ModuleNotFoundError` on backend start | Activate the venv, re-run `pip install -r requirements.txt` |
| Frontend shows "Search is temporarily unavailable" | Backend isn't running, or your network blocks the geocoding APIs — check `/api/status` |
| Map tiles don't load | Check your network can reach `tile.openstreetmap.org` |
| "Transit data unavailable" note appears often | Expected in many parts of India today — see *Data-source limitations* above |
| `npm run build` fails on a missing package | Re-run `npm install` in `frontend/` |
| CORS errors in the browser console | Confirm `CORS_ORIGINS` in `backend/.env` includes `http://localhost:5173` |

## Testing performed during development

Because this project was built in a sandboxed environment without
outbound network access, **live API calls, `pip install`, `npm install`,
and `npm run build` could not be executed here.** Every Python file was
syntax-checked (`ast.parse`), every JS/JSX file was checked for balanced
braces/parens, and endpoint names/parameters were cross-checked between
`frontend/src/api.js` and `backend/main.py` by hand. Run the commands in
`SETUP.md` locally to install dependencies and do a full live test —
please open an issue (or just tell me) if `npm run build` or `pytest`
surfaces anything, and I'll fix it immediately.
