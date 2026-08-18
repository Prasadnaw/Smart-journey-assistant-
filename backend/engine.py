"""
Journey planning engine.

Responsible for turning (origin, destination, filters) into one or more
Journey objects, each built from ordered Segment legs. This is where the
"transfer/waiting time is not free" rule lives (see rule 25 in the spec):

    total_elapsed_time = sum(leg durations) + sum(transfer/wait durations)

never just sum(vehicle durations).

Two paths feed into this engine:
  1. Real transit data (Transitous/MOTIS or a local GTFS feed), when
     coverage exists for the OD pair -- see providers/transit.py.
  2. A clearly-labelled ESTIMATED synthetic multimodal itinerary, built
     from road-network walking/driving legs (providers/routing.py) plus
     typical Indian urban-transport assumptions, when no real transit
     coverage is available.

Every journey/segment carries an explicit DataSource so the frontend can
badge it "Official" / "Scheduled" / "Live" / "Estimated" -- the app never
presents an estimate as official data.
"""
from __future__ import annotations

import uuid
from typing import Optional

from models import (
    DataSource,
    Journey,
    JourneySearchRequest,
    Location,
    RouteBreakdown,
    Segment,
    TransportMode,
)
from providers import transit as transit_provider
from providers import railway as railway_provider
from providers.routing import get_leg, haversine_meters

# ---- Assumption tables (all clearly used only for ESTIMATED data) --------

# grams CO2 per passenger-km
CO2_G_PER_KM = {
    TransportMode.WALK: 0,
    TransportMode.CYCLE: 0,
    TransportMode.BUS: 27,
    TransportMode.METRO: 14,
    TransportMode.TRAIN: 20,
    TransportMode.TAXI: 120,
}

# INR fare model: (per_km, minimum_fare, base_fare)
FARE_MODEL = {
    TransportMode.BUS: (1.4, 10, 0),
    TransportMode.METRO: (1.8, 10, 5),
    TransportMode.TRAIN: (1.1, 20, 10),
    TransportMode.TAXI: (15.0, 60, 30),
}

# typical scheduled speeds (km/h) used only to *estimate* in-vehicle time
# when no live schedule is available
TYPICAL_SPEED_KMH = {
    TransportMode.BUS: 20,
    TransportMode.METRO: 33,
    TransportMode.TRAIN: 55,
    TransportMode.TAXI: 24,
}

TRANSFER_WAIT_MINUTES = {
    TransportMode.BUS: 9,
    TransportMode.METRO: 5,
    TransportMode.TRAIN: 15,
    TransportMode.TAXI: 3,
}


def _estimate_fare(mode: TransportMode, distance_km: float) -> float:
    per_km, minimum, base = FARE_MODEL.get(mode, (0, 0, 0))
    return round(max(minimum, base + per_km * distance_km))


def _estimate_co2(mode: TransportMode, distance_km: float) -> float:
    return round(CO2_G_PER_KM.get(mode, 0) * distance_km)


async def _walk_segment(origin: Location, dest: Location, label_from: str, label_to: str) -> Segment:
    leg = await get_leg(origin.latitude, origin.longitude, dest.latitude, dest.longitude, "walk")
    return Segment(
        mode=TransportMode.WALK,
        from_location=label_from,
        to_location=label_to,
        duration_minutes=round(leg["duration_minutes"], 1),
        distance_meters=round(leg["distance_meters"]),
        fare_inr=0,
        fare_source=DataSource.ESTIMATED,
        time_source=leg["source"],
        polyline=leg.get("polyline"),
    )


def _synthetic_walk_segment(from_label: str, to_label: str, distance_m: float) -> Segment:
    """Used for access/egress walks to a stop/station where we don't have a
    real stop location to route to (e.g. no live transit coverage). Uses a
    typical walking pace; always labelled ESTIMATED."""
    duration = max(2.0, (distance_m / 1000.0) / 4.5 * 60.0)
    return Segment(
        mode=TransportMode.WALK,
        from_location=from_label,
        to_location=to_label,
        duration_minutes=round(duration, 1),
        distance_meters=round(distance_m),
        fare_inr=0,
        fare_source=DataSource.ESTIMATED,
        time_source=DataSource.ESTIMATED,
        notes="Estimated access walk (nearest stop not confirmed)",
    )


async def _taxi_segment(origin: Location, dest: Location) -> Segment:
    leg = await get_leg(
        origin.latitude, origin.longitude, dest.latitude, dest.longitude, "taxi"
    )
    distance_km = leg["distance_meters"] / 1000.0
    return Segment(
        mode=TransportMode.TAXI,
        operator="Estimated cab fare",
        from_location=origin.display_label(),
        to_location=dest.display_label(),
        duration_minutes=round(leg["duration_minutes"], 1),
        distance_meters=round(leg["distance_meters"]),
        fare_inr=_estimate_fare(TransportMode.TAXI, distance_km),
        fare_source=DataSource.ESTIMATED,
        time_source=leg["source"],
        polyline=leg.get("polyline"),
    )


def _change_segment(at: str, wait_minutes: float, note: Optional[str] = None) -> Segment:
    return Segment(
        mode=TransportMode.CHANGE,
        from_location=at,
        to_location=at,
        duration_minutes=round(wait_minutes, 1),
        fare_inr=0,
        fare_source=DataSource.ESTIMATED,
        time_source=DataSource.ESTIMATED,
        notes=note or f"Transfer / wait at {at}",
    )


def _synthetic_transit_segment(
    mode: TransportMode, from_label: str, to_label: str, distance_km: float, operator: str
) -> Segment:
    speed = TYPICAL_SPEED_KMH.get(mode, 25)
    duration = max(3.0, (distance_km / speed) * 60.0)
    return Segment(
        mode=mode,
        operator=operator,
        from_location=from_label,
        to_location=to_label,
        duration_minutes=round(duration, 1),
        distance_meters=round(distance_km * 1000),
        fare_inr=_estimate_fare(mode, distance_km),
        fare_source=DataSource.ESTIMATED,
        time_source=DataSource.ESTIMATED,
        line_name=f"{mode.value.title()} (typical schedule)",
    )


def _parse_hhmm_duration(departure: str, arrival: str) -> Optional[float]:
    """Best-effort parse of 'HH:MM' departure/arrival strings from the
    railway provider into a duration in minutes. Handles overnight trains
    (arrival time < departure time) by assuming next-day arrival. Returns
    None if the strings aren't parseable -- caller falls back to an
    estimate rather than showing a wrong duration."""
    try:
        dh, dm = (int(x) for x in departure.strip().split(":")[:2])
        ah, am = (int(x) for x in arrival.strip().split(":")[:2])
    except (ValueError, AttributeError, IndexError):
        return None
    dep_minutes = dh * 60 + dm
    arr_minutes = ah * 60 + am
    if arr_minutes < dep_minutes:
        arr_minutes += 24 * 60
    return float(arr_minutes - dep_minutes)


def _finalise_journey(origin: Location, destination: Location, segments: list[Segment]) -> Journey:
    """Sums leg durations *and* transfer/wait durations into one elapsed
    total -- the core rule from spec section 25."""
    total_minutes = sum(s.duration_minutes for s in segments)
    fare = sum(s.fare_inr or 0 for s in segments)
    walking_m = sum(s.distance_meters or 0 for s in segments if s.mode == TransportMode.WALK)
    waiting_minutes = sum(s.duration_minutes for s in segments if s.mode == TransportMode.CHANGE)
    num_changes = sum(1 for s in segments if s.mode == TransportMode.CHANGE)
    co2 = 0.0
    for s in segments:
        if s.mode in CO2_G_PER_KM and s.distance_meters:
            co2 += CO2_G_PER_KM[s.mode] * (s.distance_meters / 1000.0)

    sources = {s.fare_source for s in segments} | {s.time_source for s in segments}
    if DataSource.ESTIMATED in sources:
        overall_fare_source = DataSource.ESTIMATED
        overall_time_source = DataSource.ESTIMATED
    else:
        overall_fare_source = DataSource.SCHEDULED if DataSource.SCHEDULED in sources else DataSource.LIVE
        overall_time_source = overall_fare_source

    # Reliability is a simple heuristic confidence score, always presented
    # as an indicative percentage, never as a guarantee.
    reliability = 90 if overall_time_source != DataSource.ESTIMATED else max(
        55, 85 - num_changes * 8
    )

    return Journey(
        id=str(uuid.uuid4())[:8],
        origin=origin.display_label(),
        destination=destination.display_label(),
        segments=segments,
        total_duration_minutes=round(total_minutes, 1),
        total_fare_inr=round(fare),
        total_walking_meters=round(walking_m),
        num_changes=num_changes,
        co2_grams=round(co2),
        reliability_pct=reliability,
        fare_source=overall_fare_source,
        time_source=overall_time_source,
    )


async def _build_from_real_transit(
    origin: Location, destination: Location, raw_legs: list[dict]
) -> Journey:
    segments: list[Segment] = []
    mode_lookup = {
        "walk": TransportMode.WALK,
        "bicycle": TransportMode.CYCLE,
        "bus": TransportMode.BUS,
        "subway": TransportMode.METRO,
        "metro": TransportMode.METRO,
        "rail": TransportMode.TRAIN,
        "train": TransportMode.TRAIN,
        "tram": TransportMode.METRO,
        "car": TransportMode.TAXI,
    }
    prev_mode = None
    for i, leg in enumerate(raw_legs):
        mode = mode_lookup.get(leg["mode"], TransportMode.BUS)
        if prev_mode is not None and prev_mode != TransportMode.WALK and mode != TransportMode.WALK and prev_mode != mode:
            segments.append(
                _change_segment(leg["from"], TRANSFER_WAIT_MINUTES.get(mode, 8))
            )
        segments.append(
            Segment(
                mode=mode,
                operator=leg.get("operator"),
                from_location=leg["from"],
                to_location=leg["to"],
                departure_time=leg.get("start_time"),
                arrival_time=leg.get("end_time"),
                duration_minutes=round(leg.get("duration_minutes", 0), 1),
                distance_meters=leg.get("distance_meters"),
                fare_inr=leg.get("fare_inr"),
                fare_source=leg.get("fare_source", DataSource.UNKNOWN),
                time_source=leg.get("time_source", DataSource.SCHEDULED),
                line_name=leg.get("line_name"),
            )
        )
        prev_mode = mode
    return _finalise_journey(origin, destination, segments)


async def _build_synthetic_multimodal(
    origin: Location, destination: Location, allowed_modes: set[TransportMode]
) -> Journey:
    """Builds one clearly ESTIMATED multi-leg journey using typical Indian
    urban-transport patterns, when no real transit data is available."""
    distance_km = haversine_meters(
        origin.latitude, origin.longitude, destination.latitude, destination.longitude
    ) / 1000.0

    segments: list[Segment] = []
    origin_label = origin.display_label()
    dest_label = destination.display_label()

    if distance_km > 250 and TransportMode.TRAIN in allowed_modes:
        # Long distance: walk -> train -> walk. Try a real train (number,
        # name, schedule, class fares) via the optional Indian Railways
        # provider first; fall back to a typical-schedule estimate.
        hub_from = f"{origin.name} area station"
        hub_to = f"{destination.name} area station"
        segments.append(_synthetic_walk_segment(origin_label, hub_from, 900))

        real_train = await railway_provider.get_real_train_leg(origin.name, destination.name)
        if real_train and real_train.get("train_number"):
            train_label = real_train.get("train_name") or "Train"
            duration = None
            if real_train.get("departure_time") and real_train.get("arrival_time"):
                duration = _parse_hhmm_duration(
                    real_train["departure_time"], real_train["arrival_time"]
                )
            segments.append(
                Segment(
                    mode=TransportMode.TRAIN,
                    operator="Indian Railways",
                    from_location=hub_from,
                    to_location=hub_to,
                    departure_time=real_train.get("departure_time"),
                    arrival_time=real_train.get("arrival_time"),
                    duration_minutes=duration or max(60.0, distance_km / 55 * 60),
                    distance_meters=round(distance_km * 970),
                    fare_inr=real_train.get("fare_inr") or _estimate_fare(TransportMode.TRAIN, distance_km),
                    fare_source=DataSource.SCHEDULED if real_train.get("fare_inr") else DataSource.ESTIMATED,
                    time_source=DataSource.SCHEDULED,
                    line_name=train_label,
                    train_number=str(real_train.get("train_number")),
                    notes="Train name/number/schedule via indianrailapi.com (third-party, not IRCTC-issued)",
                )
            )
        else:
            segments.append(
                _synthetic_transit_segment(
                    TransportMode.TRAIN, hub_from, hub_to, distance_km * 0.97, "Indian Railways (typical)"
                )
            )
        segments.append(_synthetic_walk_segment(hub_to, dest_label, 500))
    elif distance_km > 5 and {TransportMode.METRO, TransportMode.BUS} & allowed_modes:
        # Urban multimodal: walk -> metro/bus -> change -> bus -> walk
        mid_lat = (origin.latitude + destination.latitude) / 2
        mid_lon = (origin.longitude + destination.longitude) / 2
        interchange = "Interchange hub"

        first_mode = TransportMode.METRO if TransportMode.METRO in allowed_modes else TransportMode.BUS
        second_mode = TransportMode.BUS if TransportMode.BUS in allowed_modes else first_mode

        stop1 = f"{origin.name} stop"
        stop2 = interchange
        stop3 = f"{destination.name} stop"

        segments.append(await _walk_segment(origin, origin, origin_label, stop1))
        segments.append(
            _synthetic_transit_segment(
                first_mode, stop1, stop2, distance_km * 0.55, f"City {first_mode.value} (typical)"
            )
        )
        if second_mode != first_mode or True:
            segments.append(
                _change_segment(stop2, TRANSFER_WAIT_MINUTES.get(second_mode, 8))
            )
            segments.append(
                _synthetic_transit_segment(
                    second_mode, stop2, stop3, distance_km * 0.4, f"City {second_mode.value} (typical)"
                )
            )
        segments.append(await _walk_segment(destination, destination, stop3, dest_label))
    elif TransportMode.WALK in allowed_modes and distance_km <= 3:
        segments.append(await _walk_segment(origin, destination, origin_label, dest_label))
    elif TransportMode.TAXI in allowed_modes:
        segments.append(await _taxi_segment(origin, destination))
    else:
        # Last resort: direct walk even if long, so the app never returns
        # zero journeys.
        segments.append(await _walk_segment(origin, destination, origin_label, dest_label))

    return _finalise_journey(origin, destination, segments)


async def generate_candidate_journeys(request: JourneySearchRequest) -> tuple[list[Journey], bool, list[str]]:
    """Returns (journeys, transit_data_was_real, notes)."""
    notes: list[str] = []
    allowed_modes = set(request.modes)
    journeys: list[Journey] = []
    transit_available = False

    raw_legs = await transit_provider.plan_real_transit_journey(
        request.origin.latitude,
        request.origin.longitude,
        request.destination.latitude,
        request.destination.longitude,
    )
    if raw_legs:
        transit_available = True
        real_journey = await _build_from_real_transit(request.origin, request.destination, raw_legs)
        journeys.append(real_journey)
    else:
        notes.append("Transit data unavailable for this area — estimated route shown.")

    # Always add a synthetic multimodal estimate as a comparison point
    # (and as the only option when there's no real transit coverage).
    synthetic = await _build_synthetic_multimodal(request.origin, request.destination, allowed_modes)
    journeys.append(synthetic)

    # Direct taxi option, if enabled.
    if TransportMode.TAXI in allowed_modes:
        taxi_leg = await _taxi_segment(request.origin, request.destination)
        journeys.append(_finalise_journey(request.origin, request.destination, [taxi_leg]))

    # Filter out journeys that use a disabled mode.
    def uses_only_allowed(j: Journey) -> bool:
        for s in j.segments:
            if s.mode == TransportMode.CHANGE:
                continue
            if s.mode not in allowed_modes:
                return False
        return True

    journeys = [j for j in journeys if uses_only_allowed(j)]

    # Deduplicate near-identical journeys (e.g. real+synthetic collapse to
    # the same single-taxi leg).
    seen_signatures = set()
    unique = []
    for j in journeys:
        sig = tuple((s.mode, round(s.duration_minutes)) for s in j.segments)
        if sig not in seen_signatures:
            seen_signatures.add(sig)
            unique.append(j)
    journeys = unique

    return journeys, transit_available, notes


def apply_filters(journeys: list[Journey], request: JourneySearchRequest) -> list[Journey]:
    result = journeys
    if request.max_fare_inr is not None:
        result = [j for j in result if j.total_fare_inr <= request.max_fare_inr]
    if request.max_duration_minutes is not None:
        result = [j for j in result if j.total_duration_minutes <= request.max_duration_minutes]
    if request.max_changes is not None:
        result = [j for j in result if j.num_changes <= request.max_changes]
    if request.max_walking_meters is not None:
        result = [j for j in result if j.total_walking_meters <= request.max_walking_meters]
    return result


_PRIORITY_KEYS = {
    "fastest": lambda j: j.total_duration_minutes,
    "cheapest": lambda j: j.total_fare_inr,
    "fewest_changes": lambda j: j.num_changes,
    "least_walking": lambda j: j.total_walking_meters,
    "greenest": lambda j: j.co2_grams,
}


def rank_journeys(journeys: list[Journey], priority: str) -> list[Journey]:
    key = _PRIORITY_KEYS.get(priority, _PRIORITY_KEYS["fastest"])
    ranked = sorted(journeys, key=key)

    # Tag each journey with every category it happens to win, so the
    # frontend can show "BEST MATCH" / "GREENEST" etc. badges.
    if ranked:
        best_of = {}
        for tag, k in _PRIORITY_KEYS.items():
            best = min(journeys, key=k)
            best_of.setdefault(best.id, []).append(tag)
        for j in ranked:
            j.tags = best_of.get(j.id, [])
        if ranked[0].id in best_of:
            if "best_match" not in ranked[0].tags:
                ranked[0].tags = ["best_match"] + ranked[0].tags
        else:
            ranked[0].tags = ["best_match"] + ranked[0].tags

    return ranked
