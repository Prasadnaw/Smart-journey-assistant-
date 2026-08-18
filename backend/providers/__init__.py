"""
Provider abstraction layer.

Every external data source (geocoding, routing, transit, weather, places)
is wrapped behind a small class with a stable interface, so a new provider
(e.g. a GTFS feed for a specific city, or a paid transit API) can be added
later without touching engine.py or main.py.
"""
