"""
Central configuration for JourneyAI India backend.
Reads all secrets/config from environment variables (.env). Never hardcode keys.
"""
import os
from dotenv import load_dotenv

load_dotenv()


def _get_bool(name: str, default: bool = False) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    # ---- Server ----
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")

    # ---- Geocoding ----
    OPEN_METEO_GEOCODING_URL: str = os.getenv(
        "OPEN_METEO_GEOCODING_URL", "https://geocoding-api.open-meteo.com/v1/search"
    )
    PHOTON_GEOCODING_URL: str = os.getenv(
        "PHOTON_GEOCODING_URL", "https://photon.komoot.io/api/"
    )

    # ---- Weather ----
    OPEN_METEO_WEATHER_URL: str = os.getenv(
        "OPEN_METEO_WEATHER_URL", "https://api.open-meteo.com/v1/forecast"
    )

    # ---- Road routing (walking / driving / cycling legs) ----
    # Public OSRM demo server. No key required. Rate-limited & "not for heavy
    # production use" per project policy -- fine for a hackathon demo.
    OSRM_BASE_URL: str = os.getenv("OSRM_BASE_URL", "https://router.project-osrm.org")

    # ---- Transit (multimodal public transport routing) ----
    TRANSITOUS_API_URL: str = os.getenv(
        "TRANSITOUS_API_URL", "https://api.transitous.org/api/v1"
    )
    TRANSITOUS_API_KEY: str = os.getenv("TRANSITOUS_API_KEY", "")
    TRANSITLAND_API_URL: str = os.getenv(
        "TRANSITLAND_API_URL", "https://transit.land/api/v2/rest"
    )
    TRANSITLAND_API_KEY: str = os.getenv("TRANSITLAND_API_KEY", "")
    OTHER_API_KEY: str = os.getenv("OTHER_API_KEY", "")

    # ---- Indian Railways train name/number/schedule/fare (optional) ----
    # indianrailapi.com is an unofficial third-party service (not run by
    # IRCTC) offering a free-tier API key. When configured, real train
    # numbers/names/schedules/class fares are used for long-distance train
    # legs instead of a generic "typical schedule" estimate. Data is tagged
    # DataSource.SCHEDULED (not "official"), since it is a third-party
    # aggregator, not an IRCTC-endorsed feed. Sign up at
    # https://indianrailapi.com to get a key.
    INDIANRAIL_API_URL: str = os.getenv(
        "INDIANRAIL_API_URL", "https://indianrailapi.com/api/v2"
    )
    INDIANRAIL_API_KEY: str = os.getenv("INDIANRAIL_API_KEY", "")

    # ---- Places / images ----
    WIKIPEDIA_API_URL: str = os.getenv(
        "WIKIPEDIA_API_URL", "https://en.wikipedia.org/w/api.php"
    )
    WIKIMEDIA_COMMONS_URL: str = os.getenv(
        "WIKIMEDIA_COMMONS_URL", "https://commons.wikimedia.org/w/api.php"
    )

    # ---- Behaviour ----
    HTTP_TIMEOUT_SECONDS: float = float(os.getenv("HTTP_TIMEOUT_SECONDS", "8.0"))
    ENABLE_FALLBACK_ROUTES: bool = _get_bool("ENABLE_FALLBACK_ROUTES", True)
    CACHE_TTL_GEOCODING: int = int(os.getenv("CACHE_TTL_GEOCODING", "3600"))
    CACHE_TTL_WEATHER: int = int(os.getenv("CACHE_TTL_WEATHER", "600"))
    CACHE_TTL_PLACES: int = int(os.getenv("CACHE_TTL_PLACES", "86400"))
    CACHE_TTL_TRANSIT: int = int(os.getenv("CACHE_TTL_TRANSIT", "300"))

    # ---- GTFS (optional local feeds -- see providers/transit.py) ----
    GTFS_FEED_DIR: str = os.getenv("GTFS_FEED_DIR", "./gtfs_feeds")


settings = Settings()
