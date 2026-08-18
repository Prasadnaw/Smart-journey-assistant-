"""
Shared Pydantic models for JourneyAI India.
"""
from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class DataSource(str, Enum):
    OFFICIAL = "official"
    LIVE = "live"
    SCHEDULED = "scheduled"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class TransportMode(str, Enum):
    WALK = "walk"
    CYCLE = "cycle"
    BUS = "bus"
    METRO = "metro"
    TRAIN = "train"
    TAXI = "taxi"
    CHANGE = "change"  # transfer / wait segment, not a real vehicle leg


class LocationType(str, Enum):
    CITY = "city"
    LOCALITY = "locality"
    ADDRESS = "address"
    RAILWAY_STATION = "railway_station"
    METRO_STATION = "metro_station"
    BUS_STOP = "bus_stop"
    AIRPORT = "airport"
    LANDMARK = "landmark"
    TOURIST_PLACE = "tourist_place"
    UNKNOWN = "unknown"


class Location(BaseModel):
    name: str
    locality: Optional[str] = None
    state: Optional[str] = None
    country: str = "India"
    latitude: float
    longitude: float
    feature_type: LocationType = LocationType.UNKNOWN
    raw_label: Optional[str] = None  # full display string for UI

    def display_label(self) -> str:
        if self.raw_label:
            return self.raw_label
        parts = [self.name]
        if self.locality and self.locality != self.name:
            parts.append(self.locality)
        if self.state:
            parts.append(self.state)
        return ", ".join(parts)


class WeatherInfo(BaseModel):
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    precipitation_mm: Optional[float] = None
    rain_probability_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    condition: Optional[str] = None
    source: DataSource = DataSource.LIVE


class Place(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    source_url: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class FoodSpot(BaseModel):
    name: str
    cuisine: Optional[str] = None
    kind: Optional[str] = None  # restaurant | cafe | fast_food | street_food (from OSM tags)
    latitude: float
    longitude: float
    source: DataSource = DataSource.LIVE


class Segment(BaseModel):
    """One leg of a journey -- a single mode of travel or a change/wait."""
    mode: TransportMode
    operator: Optional[str] = None
    from_location: str
    to_location: str
    departure_time: Optional[str] = None  # ISO8601, may be relative/unknown
    arrival_time: Optional[str] = None
    duration_minutes: float = 0
    distance_meters: Optional[float] = None
    fare_inr: Optional[float] = None
    fare_source: DataSource = DataSource.UNKNOWN
    time_source: DataSource = DataSource.UNKNOWN
    line_name: Optional[str] = None
    train_number: Optional[str] = None
    notes: Optional[str] = None
    polyline: Optional[list[list[float]]] = None  # [[lat, lon], ...]


class RouteBreakdown(BaseModel):
    fare_inr: float
    walking_meters: float
    transport_minutes: float
    waiting_minutes: float
    num_changes: int
    co2_grams: float
    reliability_pct: int
    fare_source: DataSource
    time_source: DataSource


class Journey(BaseModel):
    id: str
    origin: str
    destination: str
    segments: list[Segment]
    total_duration_minutes: float
    total_fare_inr: float
    total_walking_meters: float
    num_changes: int
    co2_grams: float
    reliability_pct: int
    fare_source: DataSource
    time_source: DataSource
    tags: list[str] = Field(default_factory=list)  # e.g. ["fastest", "cheapest"]
    departure_time: Optional[str] = None
    arrival_time: Optional[str] = None


class JourneySearchRequest(BaseModel):
    origin: Location
    destination: Location
    priority: str = "general"  # general | fastest | cheapest | fewest_changes | least_walking | greenest | greenest
    modes: list[TransportMode] = Field(
        default_factory=lambda: [
            TransportMode.WALK,
            TransportMode.BUS,
            TransportMode.METRO,
            TransportMode.TRAIN,
            TransportMode.TAXI,
        ]
    )
    max_fare_inr: Optional[float] = None
    max_duration_minutes: Optional[float] = None
    max_changes: Optional[int] = None
    max_walking_meters: Optional[float] = None
    departure_time: Optional[str] = None


class JourneySearchResponse(BaseModel):
    origin: Location
    destination: Location
    journeys: list[Journey]
    road_distance_km: Optional[float] = None
    transit_available: bool = False
    notes: list[str] = Field(default_factory=list)


class ApiStatus(BaseModel):
    geocoding: str
    routing: str
    weather: str
    places: str
    transit: str
    railway: str = "Not configured"
