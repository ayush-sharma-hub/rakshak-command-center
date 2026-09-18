"""
Project Rakshak — Open-Meteo Weather Ingestion Service
Fetches live rainfall, temperature, wind speed, and humidity
for Uttarakhand cities. Free API — no key required.
Cache TTL: 15 minutes to respect rate limits.
"""

import urllib.request
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from backend.cache.ttl_cache import weather_cache
from backend.core.database import get_db

logger = logging.getLogger("rakshak.weather")

OPEN_METEO_BASE = "https://api.open-meteo.com/v1/forecast"
WEATHER_TTL = 900          # 15 minutes
REQUEST_TIMEOUT = 8        # seconds

# Uttarakhand cities with their coordinates
UK_CITIES: Dict[str, Dict[str, float]] = {
    "Dehradun":       {"lat": 30.3165, "lng": 78.0322},
    "Rishikesh":      {"lat": 30.0869, "lng": 78.2676},
    "Haridwar":       {"lat": 29.9457, "lng": 78.1642},
    "Mussoorie":      {"lat": 30.4598, "lng": 78.0644},
    "Tehri":          {"lat": 30.3804, "lng": 78.4800},
    "Uttarkashi":     {"lat": 30.7268, "lng": 78.4354},
    "Rudraprayag":    {"lat": 30.2844, "lng": 78.9811},
    "Chamoli":        {"lat": 30.4095, "lng": 79.3344},
    "Joshimath":      {"lat": 30.5506, "lng": 79.5660},
    "Badrinath":      {"lat": 30.7433, "lng": 79.4938},
    "Kedarnath":      {"lat": 30.7346, "lng": 79.0669},
    "Pauri":          {"lat": 30.1494, "lng": 78.7800},
    "Kotdwar":        {"lat": 29.7446, "lng": 78.5156},
    "Nainital":       {"lat": 29.3919, "lng": 79.4542},
    "Almora":         {"lat": 29.5971, "lng": 79.6591},
    "Pithoragarh":    {"lat": 29.5829, "lng": 80.2182},
    "Dharchula":      {"lat": 29.8519, "lng": 80.5284},
    "Bageshwar":      {"lat": 29.8384, "lng": 79.7717},
    "Ranikhet":       {"lat": 29.6408, "lng": 79.4295},
    "Haldwani":       {"lat": 29.2183, "lng": 79.5130},
    "Ramnagar":       {"lat": 29.3944, "lng": 79.1167},
    "Gauchar":        {"lat": 30.2980, "lng": 79.1620},
    "Guptkashi":      {"lat": 30.5840, "lng": 79.0520},
    "Sonprayag":      {"lat": 30.6375, "lng": 78.9950},
    "Ukhimath":       {"lat": 30.5547, "lng": 79.0733},
}


def _build_url(lat: float, lng: float) -> str:
    params = (
        f"latitude={lat}"
        f"&longitude={lng}"
        f"&hourly=precipitation,precipitation_probability,windspeed_10m,relativehumidity_2m,temperature_2m"
        f"&current_weather=true"
        f"&timezone=Asia%2FKolkata"
        f"&forecast_days=1"
    )
    return f"{OPEN_METEO_BASE}?{params}"


def fetch_weather(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Fetch live weather for a named Uttarakhand city.
    Uses in-memory cache (15 min TTL).
    Falls back to DB-cached data if API is unreachable.
    """
    cache_key = f"weather:{city_name}"
    cached = weather_cache.get(cache_key)
    if cached:
        logger.debug("Cache hit for weather: %s", city_name)
        return cached

    coords = UK_CITIES.get(city_name)
    if not coords:
        logger.warning("Unknown city: %s", city_name)
        return None

    url = _build_url(coords["lat"], coords["lng"])

    try:
        req = urllib.request.Request(url, headers={"User-Agent": "RakshakSEOC/1.0"})
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            raw = json.loads(resp.read().decode())

        current = raw.get("current_weather", {})
        hourly = raw.get("hourly", {})

        # Grab current hour index
        now_hour = datetime.now(timezone.utc).hour
        precip = _safe_list_get(hourly.get("precipitation", []), now_hour, 0.0)
        humidity = _safe_list_get(hourly.get("relativehumidity_2m", []), now_hour, 60)
        precip_prob = _safe_list_get(hourly.get("precipitation_probability", []), now_hour, 0)

        result = {
            "city": city_name,
            "lat": coords["lat"],
            "lng": coords["lng"],
            "temperature": round(current.get("temperature", 18.0), 1),
            "wind_speed": round(current.get("windspeed", 0.0), 1),
            "precipitation": round(precip, 1),
            "precipitation_probability": precip_prob,
            "humidity": humidity,
            "weather_code": current.get("weathercode", 0),
            "fetched_at": datetime.utcnow().isoformat(),
        }

        weather_cache.set(cache_key, result, ttl_seconds=WEATHER_TTL)
        _persist_to_db(city_name, coords, result, raw)
        return result

    except Exception as exc:
        logger.error("Weather API failed for %s: %s", city_name, exc)
        # Try DB fallback
        return _fetch_from_db(city_name)


def fetch_all_weather() -> Dict[str, Any]:
    """Fetch weather for high-risk Uttarakhand cities (subset to avoid rate limits)."""
    priority_cities = [
        "Rudraprayag", "Chamoli", "Joshimath", "Kedarnath",
        "Uttarkashi", "Tehri", "Badrinath", "Dehradun"
    ]
    results = {}
    for city in priority_cities:
        data = fetch_weather(city)
        if data:
            results[city] = data
    return results


def _safe_list_get(lst: list, idx: int, default):
    try:
        return lst[idx]
    except (IndexError, TypeError):
        return default


def _persist_to_db(city: str, coords: Dict, result: Dict, raw: Dict):
    try:
        conn = get_db()
        expires = (datetime.utcnow() + timedelta(seconds=WEATHER_TTL)).isoformat()
        conn.execute("""
            INSERT OR REPLACE INTO weather_cache
            (city_name, lat, lng, temperature, precipitation, wind_speed, humidity, raw_json, fetched_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            city, coords["lat"], coords["lng"],
            result["temperature"], result["precipitation"],
            result["wind_speed"], result["humidity"],
            json.dumps(raw), result["fetched_at"], expires
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error("Failed to persist weather to DB: %s", e)


def _fetch_from_db(city: str) -> Optional[Dict]:
    try:
        conn = get_db()
        row = conn.execute(
            "SELECT * FROM weather_cache WHERE city_name = ?", (city,)
        ).fetchone()
        conn.close()
        if row:
            return dict(row)
    except Exception:
        pass
    return None

