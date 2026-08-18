"""
Tests for the core engine rule: total elapsed time must include
transfer/waiting time, not just summed vehicle durations.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from models import DataSource, Journey, Segment, TransportMode
from engine import _finalise_journey, rank_journeys
from models import Location


def _loc(name="A", lat=13.08, lon=80.27) -> Location:
    return Location(name=name, latitude=lat, longitude=lon)


def test_finalise_journey_includes_transfer_wait_time():
    segments = [
        Segment(
            mode=TransportMode.BUS,
            from_location="Stop A",
            to_location="Stop B",
            duration_minutes=20,
            fare_inr=15,
        ),
        Segment(
            mode=TransportMode.CHANGE,
            from_location="Stop B",
            to_location="Stop B",
            duration_minutes=20,  # explicit wait, matches the README's worked example
        ),
        Segment(
            mode=TransportMode.TRAIN,
            from_location="Stop B",
            to_location="Stop C",
            duration_minutes=30,
            fare_inr=100,
        ),
        Segment(
            mode=TransportMode.METRO,
            from_location="Stop C",
            to_location="Stop D",
            duration_minutes=15,
            fare_inr=20,
        ),
    ]
    journey = _finalise_journey(_loc(), _loc("B"), segments)

    # 20 + 20 + 30 + 15 = 85, NOT 20 + 30 + 15 = 65
    assert journey.total_duration_minutes == 85
    assert journey.num_changes == 1
    assert journey.total_fare_inr == 135


def test_rank_journeys_by_fastest():
    fast = _finalise_journey(
        _loc(),
        _loc("B"),
        [Segment(mode=TransportMode.TAXI, from_location="A", to_location="B", duration_minutes=10, fare_inr=100)],
    )
    slow = _finalise_journey(
        _loc(),
        _loc("B"),
        [Segment(mode=TransportMode.BUS, from_location="A", to_location="B", duration_minutes=40, fare_inr=15)],
    )
    ranked = rank_journeys([slow, fast], "fastest")
    assert ranked[0].id == fast.id
    assert "best_match" in ranked[0].tags


def test_rank_journeys_by_cheapest():
    fast_expensive = _finalise_journey(
        _loc(),
        _loc("B"),
        [Segment(mode=TransportMode.TAXI, from_location="A", to_location="B", duration_minutes=10, fare_inr=300)],
    )
    slow_cheap = _finalise_journey(
        _loc(),
        _loc("B"),
        [Segment(mode=TransportMode.BUS, from_location="A", to_location="B", duration_minutes=40, fare_inr=15)],
    )
    ranked = rank_journeys([fast_expensive, slow_cheap], "cheapest")
    assert ranked[0].id == slow_cheap.id
