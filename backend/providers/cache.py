"""
Minimal in-process TTL cache. Good enough for a hackathon demo backend
running as a single process. Avoids hammering free public APIs while the
user types in the autocomplete box, and avoids refetching weather/city
images repeatedly.
"""
import time
from typing import Any, Optional


class TTLCache:
    def __init__(self) -> None:
        self._store: dict[str, tuple[float, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.time() > expires_at:
            self._store.pop(key, None)
            return None
        return value

    def set(self, key: str, value: Any, ttl_seconds: float) -> None:
        self._store[key] = (time.time() + ttl_seconds, value)

    def clear(self) -> None:
        self._store.clear()


# Shared caches per data domain, used across providers.
geocoding_cache = TTLCache()
weather_cache = TTLCache()
places_cache = TTLCache()
transit_cache = TTLCache()
routing_cache = TTLCache()
